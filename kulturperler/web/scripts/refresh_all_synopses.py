#!/usr/bin/env python3
"""
Refresh all play synopses using Gemini 3 Flash with Google Search grounding.

Strategy:
1. Load all plays and group by creator (playwright_id or composer_id)
2. Batch requests by author/composer for better context
3. For classical works: also update titles to canonical Norwegian forms
4. Track progress for restartability
5. Create list of unverified plays for manual review

Usage:
    python3 scripts/refresh_all_synopses.py --live           # Actually modify files
    python3 scripts/refresh_all_synopses.py --live --limit 10  # Process first 10 batches
    python3 scripts/refresh_all_synopses.py --resume         # Resume from last progress
"""

import yaml
import json
import re
import os
import requests
import time
import argparse
from pathlib import Path
from typing import Optional, Dict, List, Any
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path('data')
PLAYS_DIR = DATA_DIR / 'plays'
PERSONS_DIR = DATA_DIR / 'persons'
OUTPUT_DIR = Path('output')

PROGRESS_FILE = OUTPUT_DIR / 'synopsis_refresh_progress.json'
UNVERIFIED_FILE = OUTPUT_DIR / 'unverified_plays.json'

GEMINI_KEY = os.getenv('GEMINI_KEY')
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={GEMINI_KEY}"

OPENAI_KEY = os.getenv('OPENAI_KEY')
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

# Categories that are theater/drama works (vs classical music)
THEATER_CATEGORIES = {'teater', 'dramaserie', 'hørespill'}
CLASSICAL_CATEGORIES = {'konsert', 'opera'}


def load_yaml(path: Path) -> Dict:
    """Load a YAML file."""
    with open(path) as f:
        return yaml.safe_load(f)


def save_yaml(path: Path, data: Dict):
    """Save data to a YAML file, preserving field order."""
    # Define preferred field order
    field_order = ['id', 'title', 'original_title', 'playwright_id', 'composer_id',
                   'choreographer_id', 'year_written', 'work_type', 'category',
                   'synopsis', 'wikidata_id', 'wikipedia_url', 'sceneweb_id',
                   'sceneweb_url', 'external_links']

    # Build ordered dict
    ordered = {}
    for field in field_order:
        if field in data:
            ordered[field] = data[field]
    # Add any remaining fields
    for key, value in data.items():
        if key not in ordered:
            ordered[key] = value

    with open(path, 'w') as f:
        yaml.dump(ordered, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def load_progress() -> Dict:
    """Load progress from file or create new."""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {
        'processed_ids': [],
        'last_batch': 0,
        'stats': {
            'total': 0,
            'updated': 0,
            'skipped': 0,
            'unverified': 0,
            'errors': 0
        }
    }


def save_progress(progress: Dict):
    """Save progress to file."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


def load_unverified() -> List[Dict]:
    """Load unverified list from file."""
    if UNVERIFIED_FILE.exists():
        with open(UNVERIFIED_FILE) as f:
            return json.load(f)
    return []


def save_unverified(unverified: List[Dict]):
    """Save unverified list to file."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    with open(UNVERIFIED_FILE, 'w') as f:
        json.dump(unverified, f, indent=2, ensure_ascii=False)


def clean_json_response(text: str) -> str:
    """Clean markdown code blocks from JSON response."""
    text = text.strip()
    text = re.sub(r'^```json?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return text


def call_gemini(prompt: str, use_search: bool = True) -> Optional[Dict]:
    """Call Gemini API with optional Google Search grounding."""
    if not GEMINI_KEY:
        print("ERROR: GEMINI_KEY not set")
        return None

    try:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1}
        }

        if use_search:
            payload["tools"] = [{"google_search": {}}]

        response = requests.post(GEMINI_URL, json=payload, timeout=60)
        response.raise_for_status()

        result = response.json()
        text = result['candidates'][0]['content']['parts'][0]['text']

        # Try to parse as JSON
        cleaned = clean_json_response(text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Return raw text if not JSON
            return {'raw_text': text}

    except requests.exceptions.Timeout:
        print("  ERROR: Gemini API timeout")
        return None
    except Exception as e:
        print(f"  ERROR: Gemini API error: {e}")
        return None


def call_openai(prompt: str) -> Optional[Dict]:
    """Call OpenAI GPT-5.2 API as fallback."""
    if not OPENAI_KEY:
        print("  ERROR: OPENAI_KEY not set")
        return None

    try:
        headers = {
            "Authorization": f"Bearer {OPENAI_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-5.2",
            "messages": [
                {"role": "system", "content": "Du er en ekspert på teater, opera og klassisk musikk. Svar alltid på norsk."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1
        }

        response = requests.post(OPENAI_URL, headers=headers, json=payload, timeout=90)
        response.raise_for_status()

        result = response.json()
        text = result['choices'][0]['message']['content']

        # Try to parse as JSON
        cleaned = clean_json_response(text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {'raw_text': text}

    except requests.exceptions.Timeout:
        print("  ERROR: OpenAI API timeout")
        return None
    except Exception as e:
        print(f"  ERROR: OpenAI API error: {e}")
        return None


def call_ai(prompt: str, use_search: bool = True) -> Optional[Dict]:
    """Call AI API - try Gemini first, fall back to OpenAI if it fails."""
    result = call_gemini(prompt, use_search)
    if result is not None:
        return result

    print("  Falling back to OpenAI GPT-5.2...")
    return call_openai(prompt)


def build_theater_prompt(author_name: str, plays: List[Dict]) -> str:
    """Build prompt for theater plays by a single author."""
    plays_list = []
    for play in plays:
        play_info = f'- "{play["title"]}" (ID: {play["id"]})'
        if play.get('year_written'):
            play_info += f' ({play["year_written"]})'
        if play.get('original_title') and play['original_title'] != play['title']:
            play_info += f' [originaltittel: {play["original_title"]}]'
        plays_list.append(play_info)

    plays_text = '\n'.join(plays_list)

    return f"""Søk etter informasjon om disse skuespillene/verkene av {author_name}:

{plays_text}

For hvert verk, gi:
1. En nøyaktig beskrivelse av handlingen/innholdet (4-5 setninger på norsk)
2. Bekreft at dette er riktig verk av denne forfatteren (ikke et annet verk med samme navn)

Svar i JSON-format (en liste):
[
  {{
    "id": <play_id>,
    "synopsis": "Beskrivelse på norsk...",
    "confidence": "high" | "medium" | "low"
  }}
]

VIKTIG:
- Hvis du ikke finner spesifikk info om et verk, sett confidence til "low" og synopsis til null
- Synopsis skal være på norsk
- Hver synopsis skal være 4-5 setninger som beskriver handlingen
- Ikke ta med generisk info - kun om det spesifikke verket"""


def build_classical_prompt(composer_name: str, works: List[Dict]) -> str:
    """Build prompt for classical works by a single composer."""
    works_list = []
    for work in works:
        work_info = f'- "{work["title"]}" (ID: {work["id"]}, type: {work.get("work_type", "ukjent")})'
        if work.get('wikidata_id'):
            work_info += f' [Wikidata: {work["wikidata_id"]}]'
        works_list.append(work_info)

    works_text = '\n'.join(works_list)

    return f"""Søk etter informasjon om disse musikalske verkene av {composer_name}:

{works_text}

For hvert verk, gi:
1. Kanonisk norsk tittel (f.eks. "Symfoni nr. 5 i c-moll, op. 67", "Fiolinkonsert i D-dur, op. 35", "Peer Gynt-suiten nr. 1, op. 46")
2. Kort beskrivelse (3-4 setninger på norsk) om verket - når det ble komponert, hvilken type verk det er, eventuelle kjente satser eller temaer
3. Bekreft at dette er riktig verk

Svar i JSON-format (en liste):
[
  {{
    "id": <work_id>,
    "canonical_title": "Kanonisk norsk tittel",
    "synopsis": "Beskrivelse på norsk...",
    "confidence": "high" | "medium" | "low"
  }}
]

VIKTIG:
- Hvis du ikke finner spesifikk info om et verk, sett confidence til "low" og synopsis/canonical_title til null
- Tittelen skal være på norsk der det finnes en etablert norsk form (f.eks. "Symfoni" ikke "Symphony")
- Inkluder toneart og opus-nummer i tittelen der det er relevant
- Bruk formater som "nr." (ikke "No."), "i c-moll" (ikke "in C minor")"""


def build_orphan_prompt(play: Dict) -> str:
    """Build prompt for a single play without known author."""
    info_parts = [f'Tittel: "{play["title"]}"']
    if play.get('original_title') and play['original_title'] != play['title']:
        info_parts.append(f'Originaltittel: "{play["original_title"]}"')
    if play.get('year_written'):
        info_parts.append(f'År: {play["year_written"]}')
    if play.get('work_type'):
        info_parts.append(f'Type: {play["work_type"]}')
    if play.get('category'):
        info_parts.append(f'Kategori: {play["category"]}')
    if play.get('wikidata_id'):
        info_parts.append(f'Wikidata: {play["wikidata_id"]}')

    info_text = '\n'.join(info_parts)

    is_classical = play.get('category') in CLASSICAL_CATEGORIES

    if is_classical:
        return f"""Søk etter informasjon om dette musikalske verket:

{info_text}

Gi:
1. Kanonisk norsk tittel (hvis dette er et klassisk verk med en etablert tittel)
2. Kort beskrivelse (3-4 setninger på norsk)
3. Hvem komponerte dette verket (hvis kjent)

Svar i JSON-format:
{{
  "id": {play["id"]},
  "canonical_title": "Tittel" eller null,
  "synopsis": "Beskrivelse..." eller null,
  "composer": "Komponistnavn" eller null,
  "confidence": "high" | "medium" | "low"
}}

VIKTIG: Sett confidence til "low" hvis du er usikker på om du har funnet riktig verk."""
    else:
        return f"""Søk etter informasjon om dette teaterstykket/dramaet:

{info_text}

Gi:
1. Beskrivelse av handlingen (4-5 setninger på norsk)
2. Hvem skrev dette verket (hvis kjent)

Svar i JSON-format:
{{
  "id": {play["id"]},
  "synopsis": "Beskrivelse..." eller null,
  "playwright": "Forfatternavn" eller null,
  "confidence": "high" | "medium" | "low"
}}

VIKTIG:
- Sett confidence til "low" hvis du er usikker på om du har funnet riktig verk
- NRK-interne produksjoner uten ekstern opprinnelse vil trolig ikke ha info tilgjengelig"""


MAX_BATCH_SIZE = 15  # Max works per Gemini request to avoid timeouts


class SynopsisRefresher:
    def __init__(self, dry_run: bool = True, resume: bool = False):
        self.dry_run = dry_run
        self.resume = resume
        self.plays = {}  # id -> play data
        self.persons = {}  # id -> person data
        self.progress = load_progress() if resume else {
            'processed_ids': [],
            'last_batch': 0,
            'stats': {'total': 0, 'updated': 0, 'skipped': 0, 'unverified': 0, 'errors': 0}
        }
        self.unverified = load_unverified() if resume else []

    def load_data(self):
        """Load all plays and persons from YAML files."""
        print("Loading plays...")
        for play_file in PLAYS_DIR.glob('*.yaml'):
            play = load_yaml(play_file)
            self.plays[play['id']] = play
        print(f"  Loaded {len(self.plays)} plays")

        print("Loading persons...")
        for person_file in PERSONS_DIR.glob('*.yaml'):
            person = load_yaml(person_file)
            self.persons[person['id']] = person
        print(f"  Loaded {len(self.persons)} persons")

    def get_creator_name(self, play: Dict) -> Optional[str]:
        """Get the creator name for a play (playwright or composer)."""
        creator_id = play.get('playwright_id') or play.get('composer_id')
        if creator_id and creator_id in self.persons:
            return self.persons[creator_id]['name']
        return None

    def group_plays_by_creator(self) -> Dict[int, List[Dict]]:
        """Group plays by their creator (playwright_id or composer_id)."""
        groups = defaultdict(list)

        for play in self.plays.values():
            creator_id = play.get('playwright_id') or play.get('composer_id')
            if creator_id:
                groups[creator_id].append(play)

        return groups

    def get_orphan_plays(self) -> List[Dict]:
        """Get plays without a known creator."""
        orphans = []
        for play in self.plays.values():
            if not play.get('playwright_id') and not play.get('composer_id'):
                orphans.append(play)
        return orphans

    def is_classical(self, play: Dict) -> bool:
        """Check if a play is a classical music work."""
        return play.get('category') in CLASSICAL_CATEGORIES or play.get('composer_id') is not None

    def update_play_yaml(self, play_id: int, synopsis: Optional[str], canonical_title: Optional[str] = None):
        """Update a play's YAML file with new synopsis and optionally title."""
        play_file = PLAYS_DIR / f"{play_id}.yaml"

        if not play_file.exists():
            print(f"    ERROR: Play file not found: {play_file}")
            return False

        play_data = load_yaml(play_file)

        updated = False
        if synopsis:
            play_data['synopsis'] = synopsis
            updated = True

        if canonical_title and canonical_title != play_data.get('title'):
            # Keep original title if different
            if play_data.get('title') and play_data['title'] != canonical_title:
                if not play_data.get('original_title'):
                    play_data['original_title'] = play_data['title']
            play_data['title'] = canonical_title
            updated = True

        if updated and not self.dry_run:
            save_yaml(play_file, play_data)

        return updated

    def process_batch(self, creator_id: int, plays: List[Dict]) -> int:
        """Process a batch of plays by the same creator."""
        # Skip already processed
        plays_to_process = [p for p in plays if p['id'] not in self.progress['processed_ids']]
        if not plays_to_process:
            return 0

        creator_name = self.get_creator_name(plays_to_process[0])
        if not creator_name:
            creator_name = "Ukjent"

        is_classical = self.is_classical(plays_to_process[0])

        print(f"\n{'='*60}")
        print(f"Processing {len(plays_to_process)} works by {creator_name}")
        print(f"Type: {'Classical' if is_classical else 'Theater'}")
        print(f"{'='*60}")

        total_updated = 0

        # Split into sub-batches if too large
        for i in range(0, len(plays_to_process), MAX_BATCH_SIZE):
            sub_batch = plays_to_process[i:i + MAX_BATCH_SIZE]

            if len(plays_to_process) > MAX_BATCH_SIZE:
                print(f"\n  Sub-batch {i // MAX_BATCH_SIZE + 1}: {len(sub_batch)} works")

            # Build appropriate prompt
            if is_classical:
                prompt = build_classical_prompt(creator_name, sub_batch)
            else:
                prompt = build_theater_prompt(creator_name, sub_batch)

            # Call AI (Gemini with OpenAI fallback)
            result = call_ai(prompt)

            updated_count = self._process_gemini_result(result, sub_batch, creator_name)
            total_updated += updated_count

            # Rate limiting between sub-batches
            if i + MAX_BATCH_SIZE < len(plays_to_process):
                time.sleep(1)

        return total_updated

    def _process_gemini_result(self, result: Optional[Dict], plays: List[Dict], creator_name: str) -> int:
        """Process Gemini API result and update plays."""

        if not result:
            print("  ERROR: No response from Gemini")
            self.progress['stats']['errors'] += len(plays)
            return 0

        # Handle non-list response
        if isinstance(result, dict) and 'raw_text' in result:
            print(f"  WARNING: Non-JSON response: {result['raw_text'][:200]}...")
            self.progress['stats']['errors'] += len(plays)
            return 0

        if not isinstance(result, list):
            result = [result]

        # Process results
        updated_count = 0
        for item in result:
            play_id = item.get('id')
            if not play_id:
                continue

            confidence = item.get('confidence', 'low')
            synopsis = item.get('synopsis')
            canonical_title = item.get('canonical_title')

            play = self.plays.get(play_id)
            if not play:
                continue

            print(f"\n  [{play_id}] {play['title']}")

            if confidence == 'low' or not synopsis:
                print(f"    -> Unverified (confidence: {confidence})")
                self.unverified.append({
                    'id': play_id,
                    'title': play['title'],
                    'creator': creator_name,
                    'reason': f'Low confidence or no synopsis found',
                    'gemini_response': item
                })
                self.progress['stats']['unverified'] += 1
            else:
                # Update the play
                if canonical_title:
                    print(f"    Title: {canonical_title}")
                print(f"    Synopsis: {synopsis[:100]}...")
                print(f"    Confidence: {confidence}")

                if self.update_play_yaml(play_id, synopsis, canonical_title):
                    if self.dry_run:
                        print(f"    [DRY RUN] Would update")
                    else:
                        print(f"    Updated!")
                    self.progress['stats']['updated'] += 1
                    updated_count += 1

            # Mark as processed
            self.progress['processed_ids'].append(play_id)

        return updated_count

    def process_orphan(self, play: Dict) -> bool:
        """Process a single orphan play (no known creator)."""
        if play['id'] in self.progress['processed_ids']:
            return False

        print(f"\n  [{play['id']}] {play['title']} (orphan)")

        prompt = build_orphan_prompt(play)
        result = call_ai(prompt)

        if not result or isinstance(result, dict) and 'raw_text' in result:
            print(f"    ERROR: Invalid response")
            self.progress['stats']['errors'] += 1
            self.progress['processed_ids'].append(play['id'])
            return False

        confidence = result.get('confidence', 'low')
        synopsis = result.get('synopsis')
        canonical_title = result.get('canonical_title')

        if confidence == 'low' or not synopsis:
            print(f"    -> Unverified (confidence: {confidence})")
            self.unverified.append({
                'id': play['id'],
                'title': play['title'],
                'creator': result.get('playwright') or result.get('composer') or 'Unknown',
                'reason': 'Orphan play - low confidence or no info',
                'gemini_response': result
            })
            self.progress['stats']['unverified'] += 1
        else:
            print(f"    Synopsis: {synopsis[:100]}...")
            if self.update_play_yaml(play['id'], synopsis, canonical_title):
                if self.dry_run:
                    print(f"    [DRY RUN] Would update")
                else:
                    print(f"    Updated!")
                self.progress['stats']['updated'] += 1

        self.progress['processed_ids'].append(play['id'])
        return True

    def run(self, limit: Optional[int] = None):
        """Run the synopsis refresh process."""
        self.load_data()

        # Group plays by creator
        creator_groups = self.group_plays_by_creator()
        orphans = self.get_orphan_plays()

        self.progress['stats']['total'] = len(self.plays)

        print(f"\n{'='*60}")
        print(f"SYNOPSIS REFRESH")
        print(f"{'='*60}")
        print(f"Total plays: {len(self.plays)}")
        print(f"Plays with creators: {sum(len(g) for g in creator_groups.values())}")
        print(f"Orphan plays: {len(orphans)}")
        print(f"Unique creators: {len(creator_groups)}")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        if self.resume:
            print(f"Resuming from batch {self.progress['last_batch']}")
            print(f"Already processed: {len(self.progress['processed_ids'])} plays")
        print(f"{'='*60}")

        # Sort creators by number of plays (most first for better batching)
        sorted_creators = sorted(creator_groups.items(), key=lambda x: -len(x[1]))

        batch_count = 0

        # Process plays by creator
        for creator_id, plays in sorted_creators:
            if limit and batch_count >= limit:
                break

            if self.resume and batch_count < self.progress['last_batch']:
                batch_count += 1
                continue

            self.process_batch(creator_id, plays)
            batch_count += 1
            self.progress['last_batch'] = batch_count

            # Save progress periodically
            if batch_count % 10 == 0:
                save_progress(self.progress)
                save_unverified(self.unverified)
                print(f"\n  [Progress saved at batch {batch_count}]")

            time.sleep(1)  # Rate limiting

        # Process orphan plays
        if not limit or batch_count < limit:
            print(f"\n{'='*60}")
            print(f"Processing {len(orphans)} orphan plays")
            print(f"{'='*60}")

            for i, play in enumerate(orphans):
                if limit and batch_count + i >= limit:
                    break

                self.process_orphan(play)

                if i % 10 == 0:
                    save_progress(self.progress)
                    save_unverified(self.unverified)

                time.sleep(1)

        # Final save
        save_progress(self.progress)
        save_unverified(self.unverified)

        # Print summary
        print(f"\n{'='*60}")
        print(f"SUMMARY")
        print(f"{'='*60}")
        print(f"Total plays: {self.progress['stats']['total']}")
        print(f"Processed: {len(self.progress['processed_ids'])}")
        print(f"Updated: {self.progress['stats']['updated']}")
        print(f"Unverified: {self.progress['stats']['unverified']}")
        print(f"Errors: {self.progress['stats']['errors']}")
        print(f"\nProgress saved to: {PROGRESS_FILE}")
        print(f"Unverified list saved to: {UNVERIFIED_FILE}")


def main():
    parser = argparse.ArgumentParser(description='Refresh all play synopses using Gemini')
    parser.add_argument('--live', action='store_true', help='Actually modify files (default is dry run)')
    parser.add_argument('--limit', type=int, help='Process only first N batches')
    parser.add_argument('--resume', action='store_true', help='Resume from last progress')
    parser.add_argument('--reset', action='store_true', help='Reset progress and start fresh')

    args = parser.parse_args()

    if args.reset and PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()
        print(f"Reset progress file: {PROGRESS_FILE}")
        if UNVERIFIED_FILE.exists():
            UNVERIFIED_FILE.unlink()
            print(f"Reset unverified file: {UNVERIFIED_FILE}")

    refresher = SynopsisRefresher(dry_run=not args.live, resume=args.resume)
    refresher.run(limit=args.limit)


if __name__ == '__main__':
    main()
