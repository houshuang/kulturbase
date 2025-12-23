#!/usr/bin/env python3
"""
Enrich conductors with images and Wikipedia URLs using Gemini 3 Flash with Google Search.

This script:
1. Finds all conductors without images
2. Uses Gemini with Google Search to find Wikipedia/Wikidata info
3. Updates person YAML files with image_url and wikipedia_url
"""

import os
import sys
import yaml
import requests
import time
import re
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()
GEMINI_KEY = os.getenv('GEMINI_KEY')

if not GEMINI_KEY:
    print("Error: GEMINI_KEY not found in .env")
    sys.exit(1)

DATA_DIR = Path('data')
PERSONS_DIR = DATA_DIR / 'persons'

def load_yaml(path):
    """Load YAML file."""
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f)

def save_yaml(path, data):
    """Save YAML file, excluding internal fields."""
    clean_data = {k: v for k, v in data.items() if not k.startswith('_')}
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(clean_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

def is_valid_conductor_name(name):
    """Check if name looks like a real conductor name."""
    # Skip names that contain instrument indicators or are clearly not person names
    invalid_patterns = [
        r',\s*(violin|viola|cello|piano|flute|oboe|clarinet|bassoon|horn|trumpet|trombone|tuba)',
        r'concerto',
        r'symphony',
        r'orchestra',
        r'quartet',
        r'trio',
        r'&.*&',  # Multiple ampersands suggest group name
    ]
    name_lower = name.lower()
    for pattern in invalid_patterns:
        if re.search(pattern, name_lower):
            return False

    # Should have at least 2 words (first and last name)
    words = name.split()
    if len(words) < 2:
        return False

    return True

def search_conductor_info(name):
    """Use Gemini with Google Search to find conductor Wikipedia/image info."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"

    prompt = f"""Find Wikipedia information for the conductor "{name}".

Search for their Wikipedia page (prefer Norwegian no.wikipedia.org, then English en.wikipedia.org).

Return a JSON object with these fields:
- wikipedia_url: The Wikipedia URL (Norwegian preferred, English acceptable) or null
- wikidata_id: The Wikidata Q-ID (e.g., "Q12345") if found, or null
- image_url: A direct URL to a portrait image (from Wikipedia/Wikimedia Commons) or null
- birth_year: Birth year as integer or null
- death_year: Death year as integer or null (only if deceased)
- nationality: Nationality as string or null
- bio: A 1-2 sentence biography in Norwegian or null

IMPORTANT: Only return the JSON object, nothing else. If you cannot find information, return {{"wikipedia_url": null, "image_url": null}}"""

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
                response_text = '\n'.join(text_parts).strip() if text_parts else None
                return response_text
        return None
    except Exception as e:
        print(f"  Gemini error: {e}")
        return None

def parse_json_response(response):
    """Parse JSON from Gemini response."""
    if not response:
        return None

    # Try to extract JSON from response
    # Sometimes Gemini wraps it in markdown code blocks
    json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # Try to find JSON object directly
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_str = response

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None

def get_conductors_without_images():
    """Get all conductors without images from YAML files."""
    # First get all conductor person IDs
    conductor_ids = set()
    for perf_file in PERSONS_DIR.parent.glob('performances/*.yaml'):
        perf = load_yaml(perf_file)
        for credit in perf.get('credits', []):
            if credit.get('role') == 'conductor':
                conductor_ids.add(credit.get('person_id'))

    # Now get persons without images
    conductors = []
    for person_file in PERSONS_DIR.glob('*.yaml'):
        person = load_yaml(person_file)
        person_id = person.get('id')

        if person_id not in conductor_ids:
            continue

        # Skip if already has image
        if person.get('image_url'):
            continue

        name = person.get('name', '')
        if not is_valid_conductor_name(name):
            continue

        person['_file'] = person_file
        conductors.append(person)

    return conductors

def main():
    print("Enriching conductors with images and Wikipedia info...")
    print("=" * 70)
    print()

    conductors = get_conductors_without_images()
    print(f"Found {len(conductors)} conductors without images")
    print()

    if not conductors:
        print("No conductors to process!")
        return

    enriched = 0
    skipped = 0

    for i, person in enumerate(conductors, 1):
        name = person.get('name', '')
        person_id = person.get('id')
        person_file = person['_file']

        print(f"[{i}/{len(conductors)}] {name} (ID: {person_id})")

        # Search for info
        response = search_conductor_info(name)

        if not response:
            print("  No response from Gemini")
            skipped += 1
            time.sleep(1)
            continue

        # Parse response
        info = parse_json_response(response)

        if not info:
            print(f"  Could not parse response: {response[:100]}...")
            skipped += 1
            time.sleep(1)
            continue

        # Check if we got useful info
        has_update = False

        if info.get('wikipedia_url') and not person.get('wikipedia_url'):
            person['wikipedia_url'] = info['wikipedia_url']
            print(f"  Wikipedia: {info['wikipedia_url']}")
            has_update = True

        if info.get('wikidata_id') and not person.get('wikidata_id'):
            person['wikidata_id'] = info['wikidata_id']
            print(f"  Wikidata: {info['wikidata_id']}")
            has_update = True

        if info.get('image_url') and not person.get('image_url'):
            person['image_url'] = info['image_url']
            print(f"  Image: {info['image_url']}")
            has_update = True

        if info.get('birth_year') and not person.get('birth_year'):
            person['birth_year'] = info['birth_year']
            has_update = True

        if info.get('death_year') and not person.get('death_year'):
            person['death_year'] = info['death_year']
            has_update = True

        if info.get('nationality') and not person.get('nationality'):
            person['nationality'] = info['nationality']
            has_update = True

        if info.get('bio') and not person.get('bio'):
            person['bio'] = info['bio']
            has_update = True

        if has_update:
            save_yaml(person_file, person)
            print(f"  ✓ Updated")
            enriched += 1
        else:
            print(f"  No new info found")
            skipped += 1

        # Rate limiting
        time.sleep(1.5)
        print()

    print()
    print("=" * 70)
    print(f"Summary:")
    print(f"  Enriched: {enriched} conductors")
    print(f"  Skipped: {skipped} conductors (no info found)")
    print()
    print("Run 'python3 scripts/build_database.py' to rebuild the database.")

if __name__ == '__main__':
    main()
