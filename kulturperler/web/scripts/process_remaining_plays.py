#!/usr/bin/env python3
"""Process remaining unprocessed plays."""

import yaml
import json
import os
import requests
import time
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path('data')
PLAYS_DIR = DATA_DIR / 'plays'
PERSONS_DIR = DATA_DIR / 'persons'
OUTPUT_DIR = Path('output')
PROGRESS_FILE = OUTPUT_DIR / 'synopsis_refresh_progress.json'

GEMINI_KEY = os.getenv('GEMINI_KEY')
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={GEMINI_KEY}"
OPENAI_KEY = os.getenv('OPENAI_KEY')
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

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

def call_gemini(prompt):
    try:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}],
            "generationConfig": {"temperature": 0.1}
        }
        response = requests.post(GEMINI_URL, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        text = result['candidates'][0]['content']['parts'][0]['text']
        cleaned = clean_json_response(text)
        try:
            return json.loads(cleaned)
        except:
            return {'raw_text': text}
    except Exception as e:
        print(f"  Gemini error: {e}")
        return None

def call_openai(prompt):
    try:
        headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
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
        cleaned = clean_json_response(text)
        try:
            return json.loads(cleaned)
        except:
            return {'raw_text': text}
    except Exception as e:
        print(f"  OpenAI error: {e}")
        return None

def call_ai(prompt):
    result = call_gemini(prompt)
    if result:
        return result
    print("  Falling back to OpenAI...")
    return call_openai(prompt)

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
}}"""
    else:
        return f"""Søk etter informasjon om dette verket av {creator_name}:
- "{play['title']}" (ID: {play['id']})

Gi en nøyaktig beskrivelse av handlingen (4-5 setninger på norsk).

Svar i JSON-format:
{{
  "id": {play['id']},
  "synopsis": "...",
  "confidence": "high" | "medium" | "low"
}}"""

def main():
    # Load progress
    progress = json.load(open(PROGRESS_FILE))
    processed_ids = set(progress['processed_ids'])

    # Load persons
    persons = {}
    for f in PERSONS_DIR.glob('*.yaml'):
        p = load_yaml(f)
        persons[p['id']] = p['name']

    # Find unprocessed plays
    unprocessed = []
    for f in PLAYS_DIR.glob('*.yaml'):
        play = load_yaml(f)
        if play['id'] not in processed_ids:
            unprocessed.append(play)

    print(f"Found {len(unprocessed)} unprocessed plays")

    updated = 0
    unverified = 0
    errors = 0

    for i, play in enumerate(unprocessed):
        creator_id = play.get('playwright_id') or play.get('composer_id')
        creator_name = persons.get(creator_id, "Unknown") if creator_id else "Unknown"
        is_classical = play.get('category') in {'konsert', 'opera'} or play.get('composer_id')

        print(f"\n[{i+1}/{len(unprocessed)}] {play['id']}: {play['title'][:50]}... (by {creator_name})")

        prompt = build_prompt(play, creator_name, is_classical)
        result = call_ai(prompt)

        if not result or 'raw_text' in result:
            print("  ERROR: Invalid response")
            errors += 1
            progress['processed_ids'].append(play['id'])
            progress['stats']['errors'] += 1
            continue

        confidence = result.get('confidence', 'low')
        synopsis = result.get('synopsis')
        canonical_title = result.get('canonical_title')

        if confidence == 'low' or not synopsis:
            print(f"  -> Unverified (confidence: {confidence})")
            unverified += 1
            progress['stats']['unverified'] += 1
        else:
            # Update the play file
            play_file = PLAYS_DIR / f"{play['id']}.yaml"
            play_data = load_yaml(play_file)
            play_data['synopsis'] = synopsis
            if canonical_title and is_classical:
                play_data['title'] = canonical_title
            save_yaml(play_file, play_data)
            print(f"  Updated! ({confidence})")
            updated += 1
            progress['stats']['updated'] += 1

        progress['processed_ids'].append(play['id'])

        # Save progress every 10 plays
        if (i + 1) % 10 == 0:
            with open(PROGRESS_FILE, 'w') as f:
                json.dump(progress, f, indent=2, ensure_ascii=False)
            print(f"  [Progress saved]")

        time.sleep(1)  # Rate limiting

    # Final save
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Processed: {len(unprocessed)}")
    print(f"Updated: {updated}")
    print(f"Unverified: {unverified}")
    print(f"Errors: {errors}")

if __name__ == '__main__':
    main()
