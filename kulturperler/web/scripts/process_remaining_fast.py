#!/usr/bin/env python3
"""Fast parallel processing of remaining plays using OpenAI with ThreadPoolExecutor."""

import yaml
import json
import os
import requests
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path('data')
PLAYS_DIR = DATA_DIR / 'plays'
PERSONS_DIR = DATA_DIR / 'persons'
OUTPUT_DIR = Path('output')
PROGRESS_FILE = OUTPUT_DIR / 'synopsis_refresh_progress.json'

OPENAI_KEY = os.getenv('OPENAI_KEY')
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

MAX_WORKERS = 10  # 10 concurrent requests

def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)

def save_yaml(path, data):
    field_order = ['id', 'title', 'original_title', 'playwright_id', 'composer_id',
                   'choreographer_id', 'year_written', 'work_type', 'category',
                   'synopsis', 'wikidata_id', 'wikipedia_url', 'sceneweb_id',
                   'sceneweb_url', 'external_links']
    ordered = {}
    for field in field_order:
        if field in data:
            ordered[field] = data[field]
    for key, value in data.items():
        if key not in ordered:
            ordered[key] = value
    with open(path, 'w') as f:
        yaml.dump(ordered, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

def clean_json_response(text):
    text = text.strip()
    text = re.sub(r'^```json?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return text

def build_prompt(play, creator_name, is_classical):
    if is_classical:
        return f"""Søk etter informasjon om dette verket av {creator_name}:
- "{play['title']}" (ID: {play['id']})

Gi:
1. Kanonisk norsk tittel (f.eks. "Symfoni nr. 5 i c-moll", "Fiolinkonsert i D-dur, op. 35")
2. Kort beskrivelse (4-5 setninger på norsk)

Svar i JSON-format:
{{
  "id": {play['id']},
  "canonical_title": "...",
  "synopsis": "...",
  "confidence": "high" | "medium" | "low"
}}

VIKTIG: Hvis du ikke finner spesifikk info, sett confidence til "low" og synopsis til null."""
    else:
        return f"""Søk etter informasjon om dette verket av {creator_name}:
- "{play['title']}" (ID: {play['id']})

Gi en nøyaktig beskrivelse av handlingen (4-5 setninger på norsk).

Svar i JSON-format:
{{
  "id": {play['id']},
  "synopsis": "...",
  "confidence": "high" | "medium" | "low"
}}

VIKTIG: Hvis du ikke finner spesifikk info, sett confidence til "low" og synopsis til null."""

def call_openai(prompt, play_id):
    headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "Du er en ekspert på teater, opera og klassisk musikk. Svar alltid på norsk i JSON-format."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
    try:
        response = requests.post(OPENAI_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        if 'error' in result:
            return None
        text = result['choices'][0]['message']['content']
        cleaned = clean_json_response(text)
        try:
            return json.loads(cleaned)
        except:
            return {'raw_text': text}
    except Exception as e:
        print(f"  [{play_id}] Error: {e}")
        return None

def process_play(play, persons):
    """Process a single play and return result."""
    creator_id = play.get('playwright_id') or play.get('composer_id')
    creator_name = persons.get(creator_id, "Unknown") if creator_id else "Unknown"
    is_classical = play.get('category') in {'konsert', 'opera'} or play.get('composer_id')

    prompt = build_prompt(play, creator_name, is_classical)
    result = call_openai(prompt, play['id'])

    return {
        'play': play,
        'result': result,
        'is_classical': is_classical
    }

def main():
    # Load progress
    progress = json.load(open(PROGRESS_FILE))
    processed_ids = set(progress['processed_ids'])

    # Load persons
    print("Loading persons...")
    persons = {}
    for f in PERSONS_DIR.glob('*.yaml'):
        p = load_yaml(f)
        persons[p['id']] = p['name']

    # Find unprocessed plays
    print("Finding unprocessed plays...")
    unprocessed = []
    for f in PLAYS_DIR.glob('*.yaml'):
        play = load_yaml(f)
        if play['id'] not in processed_ids:
            unprocessed.append(play)

    print(f"Found {len(unprocessed)} unprocessed plays")
    print(f"Processing with {MAX_WORKERS} concurrent workers...")

    stats = {'updated': 0, 'unverified': 0, 'errors': 0}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        futures = {executor.submit(process_play, play, persons): play for play in unprocessed}

        completed = 0
        for future in as_completed(futures):
            completed += 1
            try:
                data = future.result()
                play = data['play']
                result = data['result']
                is_classical = data['is_classical']

                if not result or 'raw_text' in result:
                    stats['errors'] += 1
                    progress['stats']['errors'] += 1
                    print(f"[{completed}/{len(unprocessed)}] {play['id']}: ERROR")
                else:
                    confidence = result.get('confidence', 'low')
                    synopsis = result.get('synopsis')
                    canonical_title = result.get('canonical_title')

                    if confidence == 'low' or not synopsis:
                        stats['unverified'] += 1
                        progress['stats']['unverified'] += 1
                        print(f"[{completed}/{len(unprocessed)}] {play['id']}: Unverified")
                    else:
                        # Update the play file
                        play_file = PLAYS_DIR / f"{play['id']}.yaml"
                        play_data = load_yaml(play_file)
                        play_data['synopsis'] = synopsis
                        if canonical_title and is_classical:
                            play_data['title'] = canonical_title
                        save_yaml(play_file, play_data)
                        stats['updated'] += 1
                        progress['stats']['updated'] += 1
                        print(f"[{completed}/{len(unprocessed)}] {play['id']}: Updated ({confidence})")

                progress['processed_ids'].append(play['id'])

            except Exception as e:
                print(f"[{completed}/{len(unprocessed)}] Exception: {e}")
                stats['errors'] += 1

            # Save progress every 20 completions
            if completed % 20 == 0:
                with open(PROGRESS_FILE, 'w') as f:
                    json.dump(progress, f, indent=2, ensure_ascii=False)
                print(f"  [Progress saved: {completed}/{len(unprocessed)}]")

    # Final save
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Processed: {len(unprocessed)}")
    print(f"Updated: {stats['updated']}")
    print(f"Unverified: {stats['unverified']}")
    print(f"Errors: {stats['errors']}")
    print(f"\nTotal in database:")
    print(f"  Processed: {len(progress['processed_ids'])}/2027")
    print(f"  Updated: {progress['stats']['updated']}")
    print(f"  Unverified: {progress['stats']['unverified']}")

if __name__ == '__main__':
    main()
