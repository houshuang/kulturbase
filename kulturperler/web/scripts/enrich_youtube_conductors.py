#!/usr/bin/env python3
"""
Enrich YouTube performances with conductor data using Gemini 3 Flash with Google Search,
with fallback to OpenAI GPT-5.2.

This script:
1. Loads YouTube performances that are orchestral types without conductors
2. Uses Gemini with Google Search to find conductor information
3. Falls back to OpenAI GPT-5.2 if Gemini fails
4. Looks up or creates person entries in data/persons/
5. Updates performance YAML files with conductor credits
"""

import os
import sys
import yaml
import requests
import time
import re
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()
GEMINI_KEY = os.getenv('GEMINI_KEY')
OPENAI_KEY = os.getenv('OPENAI_KEY')

if not GEMINI_KEY and not OPENAI_KEY:
    print("Error: Neither GEMINI_KEY nor OPENAI_KEY found in .env")
    sys.exit(1)

# Track which API to use (start with Gemini, switch to OpenAI after failures)
gemini_failures = 0
use_openai = False

DATA_DIR = Path('data')
PERFORMANCES_DIR = DATA_DIR / 'performances'
PERSONS_DIR = DATA_DIR / 'persons'
WORKS_DIR = DATA_DIR / 'plays'
EPISODES_DIR = DATA_DIR / 'episodes'

# Work types that typically have conductors
ORCHESTRAL_TYPES = ['symphony', 'concerto', 'orchestral', 'opera', 'ballet', 'choral', 'oratorio']

def load_yaml(path):
    """Load YAML file."""
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f)

def save_yaml(path, data):
    """Save YAML file, excluding internal fields."""
    clean_data = {k: v for k, v in data.items() if not k.startswith('_')}
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(clean_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

def build_conductor_prompt(title, work_title, year, youtube_url=None):
    """Build the prompt for conductor search."""
    search_terms = []
    if youtube_url:
        search_terms.append(f"YouTube URL: {youtube_url}")
    search_terms.append(f"Title: {title}")
    if work_title and work_title != title:
        search_terms.append(f"Work: {work_title}")
    search_terms.append(f"Year: {year}")

    context = "\n".join(search_terms)

    return f"""Find the conductor (dirigent) for this orchestral concert recording:
{context}

Search for the conductor who led this performance. Look for orchestra conductor credits.
Note: Some performances may be chamber music or solo recordings without a conductor.

Respond with ONLY ONE of these formats:
- The conductor's full name (e.g., "Edward Gardner")
- "NO_CONDUCTOR" if this is chamber music, solo, or small ensemble without conductor
- "NOT_FOUND" if you cannot determine the conductor

Just the name or status, nothing else."""


def search_with_gemini(prompt):
    """Use Gemini with Google Search."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={GEMINI_KEY}"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.1}
    }

    try:
        r = requests.post(url, json=payload, timeout=60)
        r.raise_for_status()
        result = r.json()

        if 'candidates' in result and len(result['candidates']) > 0:
            candidate = result['candidates'][0]
            if 'content' in candidate and 'parts' in candidate['content']:
                parts = candidate['content']['parts']
                text_parts = [p['text'] for p in parts if 'text' in p]
                return '\n'.join(text_parts).strip() if text_parts else None
        return None
    except Exception as e:
        print(f"  Gemini error: {e}")
        return None


def search_with_openai(prompt):
    """Use OpenAI GPT-4o as fallback."""
    url = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENAI_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that finds conductor information for classical music performances. Use your knowledge to identify conductors. Always respond with just the conductor's name, NO_CONDUCTOR (for chamber/solo music), or NOT_FOUND."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        result = r.json()

        if 'choices' in result and len(result['choices']) > 0:
            return result['choices'][0]['message']['content'].strip()
        return None
    except Exception as e:
        print(f"  OpenAI error: {e}")
        return None


def search_conductor(title, work_title, year, youtube_url=None):
    """Search for conductor using Gemini, with OpenAI fallback."""
    global gemini_failures, use_openai

    prompt = build_conductor_prompt(title, work_title, year, youtube_url)

    # Try Gemini first (unless we've switched to OpenAI)
    if not use_openai and GEMINI_KEY:
        result = search_with_gemini(prompt)
        if result:
            gemini_failures = 0  # Reset on success
            return result
        else:
            gemini_failures += 1
            if gemini_failures >= 3 and OPENAI_KEY:
                print("  -> Switching to OpenAI after repeated Gemini failures")
                use_openai = True

    # Try OpenAI
    if OPENAI_KEY:
        print("  Using OpenAI GPT-4o...")
        return search_with_openai(prompt)

    return None

def get_works():
    """Load all works into a lookup dictionary."""
    works = {}
    for work_file in WORKS_DIR.glob('*.yaml'):
        work = load_yaml(work_file)
        works[work['id']] = work
    return works

def get_youtube_performances(works):
    """Get YouTube performances that are orchestral types without conductors."""
    performances = []

    for perf_file in sorted(PERFORMANCES_DIR.glob('*.yaml')):
        perf = load_yaml(perf_file)

        if perf.get('source') != 'youtube':
            continue

        work_id = perf.get('work_id')
        if work_id and work_id in works:
            work = works[work_id]
            work_type = work.get('work_type')
            if work_type not in ORCHESTRAL_TYPES:
                continue
            perf['_work'] = work
        else:
            continue

        credits = perf.get('credits', [])
        has_conductor = any(c.get('role') == 'conductor' for c in credits)
        if has_conductor:
            continue

        perf['_file'] = perf_file
        performances.append(perf)

    return performances

def get_youtube_url(perf_id):
    """Get YouTube URL for a performance from its episodes."""
    for ep_file in EPISODES_DIR.glob('*.yaml'):
        ep = load_yaml(ep_file)
        if ep.get('performance_id') == perf_id:
            return ep.get('youtube_url')
    return None

def get_all_persons():
    """Load all persons into a lookup dictionary."""
    persons = {}
    for person_file in PERSONS_DIR.glob('*.yaml'):
        person = load_yaml(person_file)
        persons[person['id']] = person
        person['_file'] = person_file
    return persons

def find_person_by_name(name, persons):
    """Find a person by name (case-insensitive)."""
    name_lower = name.lower().strip()
    for person in persons.values():
        person_name = person.get('name', '').lower().strip()
        normalized_name = person.get('normalized_name', '').lower().strip()
        if person_name == name_lower or normalized_name == name_lower:
            return person
    return None

def get_next_person_id(persons):
    """Get next available person ID."""
    if not persons:
        return 1
    return max(persons.keys()) + 1

def create_person(name, persons):
    """Create a new person entry."""
    person_id = get_next_person_id(persons)
    person = {
        'id': person_id,
        'name': name,
        'normalized_name': name.lower()
    }
    person_file = PERSONS_DIR / f"{person_id}.yaml"
    save_yaml(person_file, person)
    persons[person_id] = person
    person['_file'] = person_file
    print(f"  Created new person: {name} (ID: {person_id})")
    return person

def extract_conductor_name(response):
    """Extract conductor name from Gemini response."""
    if not response:
        return None

    response = response.strip()
    response_upper = response.upper()

    if 'NO_CONDUCTOR' in response_upper or 'NOT_FOUND' in response_upper:
        return None
    if 'CHAMBER' in response_upper or 'SOLO' in response_upper:
        return None

    lines = response.split('\n')
    name = lines[0].strip().strip('"\'')

    if len(name.split()) < 2:
        return None
    if any(c in name for c in [':', '(', ')', '[', ']', '{', '}', '|', '/']):
        return None
    if len(name) > 50:
        return None

    return name

def main():
    print("Enriching YouTube performances with conductor data...")
    print("=" * 70)
    print()

    print("Loading data...")
    works = get_works()
    performances = get_youtube_performances(works)
    persons = get_all_persons()

    print(f"Found {len(performances)} YouTube orchestral performances without conductors")
    print(f"Found {len(persons)} persons in database")
    print()

    if not performances:
        print("No performances to process!")
        return

    enriched = 0
    skipped_no_conductor = 0
    skipped_not_found = 0
    errors = 0

    for i, perf in enumerate(performances, 1):
        perf_id = perf['id']
        title = perf.get('title', '')
        year = perf.get('year', '')
        work = perf.get('_work', {})
        work_title = work.get('title', '')
        work_type = work.get('work_type', '')

        print(f"[{i}/{len(performances)}]")
        print(f"Processing: {title} ({year}) [{work_type}]")

        youtube_url = get_youtube_url(perf_id)
        if youtube_url:
            print(f"  YouTube: {youtube_url}")

        print(f"  Searching for conductor...")
        response = search_conductor(title, work_title, year, youtube_url)

        if not response:
            print(f"  No response from API")
            errors += 1
            time.sleep(2)
            continue

        print(f"  Response: {response[:100]}...")

        conductor_name = extract_conductor_name(response)

        if not conductor_name:
            if 'NO_CONDUCTOR' in response.upper() or 'CHAMBER' in response.upper():
                print(f"  -> No conductor (chamber/solo music)")
                skipped_no_conductor += 1
            else:
                print(f"  -> Could not find conductor")
                skipped_not_found += 1
            time.sleep(1)
            continue

        print(f"  Found conductor: {conductor_name}")

        person = find_person_by_name(conductor_name, persons)
        if person:
            print(f"  Found existing person: {person['name']} (ID: {person['id']})")
        else:
            person = create_person(conductor_name, persons)

        credits = perf.get('credits', [])
        credits.append({
            'person_id': person['id'],
            'role': 'conductor'
        })
        perf['credits'] = credits

        save_yaml(perf['_file'], perf)
        print(f"  ✓ Updated performance with conductor")
        enriched += 1

        time.sleep(1.5)
        print()

    print()
    print("=" * 70)
    print(f"Summary:")
    print(f"  Enriched with conductor: {enriched}")
    print(f"  No conductor (chamber/solo): {skipped_no_conductor}")
    print(f"  Conductor not found: {skipped_not_found}")
    print(f"  Errors: {errors}")
    print()
    print("Run 'python3 scripts/build_database.py' to rebuild the database.")

if __name__ == '__main__':
    main()
