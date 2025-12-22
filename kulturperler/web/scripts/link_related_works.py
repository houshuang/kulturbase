#!/usr/bin/env python3
"""
Link classical works (operas, ballets, orchestral) to their literary sources.

Examples:
- Grieg: Peer Gynt Suite → Ibsen: Peer Gynt (play)
- Bibalo: Gjengangere (opera) → Ibsen: Gengangere (play)
- Prokofiev: Romeo og Julie (ballet) → Shakespeare: Romeo and Juliet

Uses Gemini to identify literary sources for works.
"""

import json
import yaml
import os
import re
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data"
CACHE_FILE = Path(__file__).parent.parent / "output" / "literary_source_cache.json"

GEMINI_KEY = os.getenv('GEMINI_KEY')
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"


def load_yaml(path: Path) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def save_yaml(path: Path, data: dict):
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def load_cache() -> dict:
    if CACHE_FILE.exists():
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_cache(cache: dict):
    CACHE_FILE.parent.mkdir(exist_ok=True)
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def load_all_works() -> dict:
    """Load all works into a dict by id."""
    works = {}
    for f in (DATA_DIR / "plays").glob("*.yaml"):
        data = load_yaml(f)
        if data:
            works[data.get('id')] = data
            works[f'path:{data.get("id")}'] = f
    return works


def load_all_persons() -> dict:
    """Load all persons into a dict by id."""
    persons = {}
    for f in (DATA_DIR / "persons").glob("*.yaml"):
        data = load_yaml(f)
        if data:
            persons[data.get('id')] = data
    return persons


def find_play_by_title(works: dict, title: str) -> int | None:
    """Find a theater work by title."""
    title_lower = title.lower().strip()

    for work_id, work in works.items():
        if isinstance(work_id, str) and work_id.startswith('path:'):
            continue

        work_type = work.get('work_type', '')
        if work_type not in ('teaterstykke', 'nrk_teaterstykke'):
            continue

        work_title = work.get('title', '').lower()
        orig_title = work.get('original_title', '').lower() if work.get('original_title') else ''

        # Exact match
        if title_lower == work_title or title_lower == orig_title:
            return work_id

        # Partial match
        if title_lower in work_title or work_title in title_lower:
            return work_id
        if orig_title and (title_lower in orig_title or orig_title in title_lower):
            return work_id

    return None


def ask_gemini_for_source(work_title: str, composer: str, work_type: str, cache: dict) -> dict | None:
    """Ask Gemini if this work is based on a literary source."""
    cache_key = f"{work_title}|{composer}|{work_type}"
    if cache_key in cache:
        return cache[cache_key]

    prompt = f"""Is this musical work based on a literary source (play, novel, poem)?

Work: {work_title}
Composer: {composer or 'Unknown'}
Type: {work_type}

Return ONLY valid JSON (no markdown):
{{
  "is_based_on_literary_work": true/false,
  "source_title": "Title of the play/novel or null",
  "source_author": "Author name or null",
  "source_type": "play|novel|poem|myth|other|null",
  "confidence": 0.0-1.0,
  "notes": "Brief explanation"
}}

Use web search to verify. Focus on famous adaptations like:
- Peer Gynt (Grieg) → Ibsen
- Romeo and Juliet ballets → Shakespeare
- Operas based on plays (Verdi, Puccini, etc.)"""

    try:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}],
            "generationConfig": {"temperature": 0.1}
        }

        resp = requests.post(GEMINI_URL, json=payload, timeout=30)
        if not resp.ok:
            return None

        result = resp.json()
        text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')

        # Clean response
        text = re.sub(r'^```json\s*', '', text.strip())
        text = re.sub(r'\s*```$', '', text)

        data = json.loads(text)
        if isinstance(data, list):
            data = data[0] if data else {}

        cache[cache_key] = data
        save_cache(cache)
        return data

    except Exception as e:
        print(f"    Gemini error: {e}")
        return None


def main():
    print("=" * 60)
    print("Link Classical Works to Literary Sources")
    print("=" * 60)

    if not GEMINI_KEY:
        print("ERROR: GEMINI_KEY not found")
        return

    works = load_all_works()
    persons = load_all_persons()
    cache = load_cache()

    # Filter to classical works that might have literary sources
    classical_types = ('opera', 'ballet', 'operetta', 'orchestral', 'symphony', 'choral')

    candidates = []
    for work_id, work in works.items():
        if isinstance(work_id, str) and work_id.startswith('path:'):
            continue
        if work.get('work_type') in classical_types:
            # Skip if already has a based_on_work_id
            if work.get('based_on_work_id'):
                continue
            candidates.append(work)

    print(f"\nFound {len(candidates)} classical works to check")
    print(f"Loaded {len(cache)} cached results")

    linked = 0
    checked = 0

    for i, work in enumerate(candidates):
        work_id = work.get('id')
        title = work.get('title', '')
        work_type = work.get('work_type', '')
        composer_id = work.get('composer_id')

        composer_name = ''
        if composer_id and composer_id in persons:
            composer_name = persons[composer_id].get('name', '')

        print(f"\n[{i+1}/{len(candidates)}] {title} ({work_type})")
        print(f"    Composer: {composer_name}")

        # First try simple title matching for well-known works
        simple_matches = {
            'peer gynt': 'Peer Gynt',
            'gengangere': 'Gengangere',
            'gjengangere': 'Gengangere',
            'hedda gabler': 'Hedda Gabler',
            'et dukkehjem': 'Et dukkehjem',
            'brand': 'Brand',
            'romeo': 'Romeo og Julie',
            'hamlet': 'Hamlet',
            'macbeth': 'Macbeth',
            'othello': 'Othello',
            'stormen': 'Stormen',
            'en midtsommernatts drøm': 'En midtsommernattsdrøm',
        }

        title_lower = title.lower()
        matched_play_id = None

        for keyword, play_title in simple_matches.items():
            if keyword in title_lower:
                matched_play_id = find_play_by_title(works, play_title)
                if matched_play_id:
                    print(f"    Quick match: '{keyword}' → {play_title} (id={matched_play_id})")
                    break

        # If no quick match, ask Gemini
        if not matched_play_id:
            result = ask_gemini_for_source(title, composer_name, work_type, cache)
            time.sleep(0.3)
            checked += 1

            if result and result.get('is_based_on_literary_work') and result.get('confidence', 0) > 0.7:
                source_title = result.get('source_title')
                source_author = result.get('source_author')
                print(f"    Gemini: Based on '{source_title}' by {source_author}")

                # Try to find the play
                if source_title:
                    matched_play_id = find_play_by_title(works, source_title)
                    if matched_play_id:
                        print(f"    Found play: id={matched_play_id}")

        # Update the work if we found a match
        if matched_play_id and matched_play_id != work_id:
            work_path = works.get(f'path:{work_id}')
            if work_path:
                work['based_on_work_id'] = matched_play_id
                save_yaml(work_path, work)
                linked += 1
                print(f"    ✓ Linked to play {matched_play_id}")

    print("\n" + "=" * 60)
    print("LINKING COMPLETE")
    print("=" * 60)
    print(f"Checked with Gemini: {checked}")
    print(f"Linked to plays: {linked}")

    print("\nNext steps:")
    print("1. Run: python3 scripts/validate_data.py")
    print("2. Run: python3 scripts/build_database.py")


if __name__ == "__main__":
    main()
