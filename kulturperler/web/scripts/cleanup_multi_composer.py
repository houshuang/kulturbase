#!/usr/bin/env python3
"""
Clean up multi-composer entries.

For entries like "Mozart and Beethoven", "Gluck, Wagner, Verdi":
1. Extract individual composer names
2. Create person entries for composers who don't exist
3. Add composer credits to performances (multi-composer concerts)
4. Delete the combined person entries
"""

import yaml
import re
import os
import requests
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / 'data'
GEMINI_KEY = os.getenv('GEMINI_KEY')
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={GEMINI_KEY}"


def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_yaml(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def call_gemini(prompt):
    """Call Gemini 3 Flash API."""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1}
    }
    try:
        r = requests.post(GEMINI_URL, json=payload, timeout=30)
        if r.status_code == 200:
            data = r.json()
            return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"  Gemini error: {e}")
    return None


def get_next_person_id():
    """Find the next available person ID."""
    max_id = 0
    for f in (DATA_DIR / 'persons').glob('*.yaml'):
        p = load_yaml(f)
        if p and p.get('id'):
            max_id = max(max_id, p['id'])
    return max_id + 1


def find_combined_entries():
    """Find all combined composer entries."""
    multi_patterns = [
        r'^[A-Z][a-zæøåÆØÅ]+ (and|og|&) [A-Z]',
        r'^[A-Z][a-zæøåÆØÅ]+/[A-Z]',
        r'^[A-Z][a-zæøåÆØÅ]+, [A-Z][a-zæøåÆØÅ]+, [A-Z]',
        r'^[A-Z][a-zæøåÆØÅ]+, [A-Z][a-zæøåÆØÅ]+ (and|og|&)',
    ]

    combined = []
    for f in (DATA_DIR / 'persons').glob('*.yaml'):
        p = load_yaml(f)
        if not p:
            continue
        name = p.get('name', '')
        for pattern in multi_patterns:
            if re.search(pattern, name):
                combined.append({
                    'id': p['id'],
                    'name': name,
                    'file': f,
                })
                break
    return combined


def extract_composer_names(combined_name):
    """Extract individual composer names from a combined entry."""
    # Use Gemini to parse the names
    prompt = f"""Extract the individual composer/artist names from this combined entry:
"{combined_name}"

Return ONLY a JSON array of full names, like: ["Wolfgang Amadeus Mozart", "Ludwig van Beethoven"]
If a name is partial (like just a last name), provide the most likely full name for a classical composer.
"""
    response = call_gemini(prompt)
    if response:
        try:
            # Extract JSON array from response
            match = re.search(r'\[.*\]', response, re.DOTALL)
            if match:
                return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return []


def find_or_create_composer(name, next_id_holder):
    """Find existing composer or create new one."""
    # Search for existing person
    name_lower = name.lower()
    for f in (DATA_DIR / 'persons').glob('*.yaml'):
        p = load_yaml(f)
        if not p:
            continue
        existing_name = p.get('name', '').lower()
        # Check for exact match or partial match
        if existing_name == name_lower:
            return p['id'], False
        # Check if all parts of the search name are in existing name
        name_parts = name_lower.split()
        if len(name_parts) >= 2 and all(part in existing_name for part in name_parts[-2:]):
            # Make sure it's not a combined entry
            if ' and ' not in existing_name and ' og ' not in existing_name and '/' not in existing_name and ', ' not in p.get('name', ''):
                return p['id'], False

    # Create new person
    new_id = next_id_holder[0]
    next_id_holder[0] += 1

    person = {
        'id': new_id,
        'name': name,
        'normalized_name': name.lower(),
    }
    filepath = DATA_DIR / 'persons' / f'{new_id}.yaml'
    save_yaml(filepath, person)
    print(f"  Created composer: [{new_id}] {name}")
    return new_id, True


def get_works_using_composer(composer_id):
    """Get all works that reference a composer."""
    works = []
    for f in (DATA_DIR / 'plays').glob('*.yaml'):
        w = load_yaml(f)
        if w and w.get('composer_id') == composer_id:
            works.append({
                'id': w['id'],
                'title': w.get('title', ''),
                'file': f,
            })
    return works


def get_performances_for_work(work_id):
    """Get performances linked to a work."""
    performances = []
    for f in (DATA_DIR / 'performances').glob('*.yaml'):
        p = load_yaml(f)
        if p and p.get('work_id') == work_id:
            performances.append({
                'id': p['id'],
                'file': f,
                'data': p,
            })
    return performances


def add_composer_credits_to_performance(perf_file, composer_ids):
    """Add composer credits to a performance."""
    perf = load_yaml(perf_file)
    credits = perf.get('credits', [])

    # Add composer credits if not already present
    for cid in composer_ids:
        if not any(c.get('person_id') == cid and c.get('role') == 'composer' for c in credits):
            credits.append({'person_id': cid, 'role': 'composer'})

    perf['credits'] = credits
    save_yaml(perf_file, perf)


def main():
    print("Cleaning up multi-composer entries...")

    if not GEMINI_KEY:
        print("Error: GEMINI_KEY not found in .env")
        return

    # Find combined entries
    combined = find_combined_entries()
    print(f"Found {len(combined)} combined entries")

    # Skip certain entries that are actual collaborators (not concerts)
    skip_names = [
        'Bing & Bringsværd',  # Writing duo
        'Gudrun og Annema Isaksen Gardsjord',  # Sisters/duo
    ]

    next_id = [get_next_person_id()]  # Use list for mutability
    processed = 0
    skipped = 0

    for entry in combined:
        print(f"\n[{entry['id']}] {entry['name']}")

        if entry['name'] in skip_names:
            print("  Skipping (legitimate duo/collaboration)")
            skipped += 1
            continue

        # Extract individual composer names
        composers = extract_composer_names(entry['name'])
        if not composers:
            print("  Failed to extract composer names")
            skipped += 1
            continue

        print(f"  Extracted composers: {composers}")

        # Find or create person entries for each composer
        composer_ids = []
        for comp_name in composers:
            cid, created = find_or_create_composer(comp_name, next_id)
            composer_ids.append(cid)
            if not created:
                print(f"  Found existing: [{cid}] {comp_name}")

        # Get works using this combined entry
        works = get_works_using_composer(entry['id'])
        print(f"  Works using this entry: {len(works)}")

        for work in works:
            print(f"    Work [{work['id']}] '{work['title']}'")

            # Get performances for this work
            performances = get_performances_for_work(work['id'])

            # Add composer credits to performances
            for perf in performances:
                add_composer_credits_to_performance(perf['file'], composer_ids)
                print(f"      Added composer credits to performance [{perf['id']}]")

            # Update work to use first composer (primary)
            # For multi-composer concerts, the "work" represents the concert, not individual pieces
            work_data = load_yaml(work['file'])
            if len(composer_ids) == 1:
                work_data['composer_id'] = composer_ids[0]
            else:
                # Use first composer as primary, rest via performance credits
                work_data['composer_id'] = composer_ids[0]
            save_yaml(work['file'], work_data)

        # Delete the combined entry
        entry['file'].unlink()
        print(f"  Deleted combined entry {entry['file'].name}")
        processed += 1

    print(f"\n\nResults:")
    print(f"  Processed: {processed}")
    print(f"  Skipped: {skipped}")


if __name__ == '__main__':
    main()
