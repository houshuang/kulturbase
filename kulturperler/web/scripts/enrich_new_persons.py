#!/usr/bin/env python3
"""
Enrich new persons (ID >= 4547) with Wikipedia data using curl to avoid SSL issues.
"""

import json
import os
import re
import subprocess
import yaml
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
PERSONS_DIR = BASE_DIR / "data" / "persons"
START_ID = 4547


def fetch_wikipedia_data(name):
    """Fetch person data from Norwegian Wikipedia using curl."""
    encoded_name = name.replace(' ', '_')
    url = f"https://no.wikipedia.org/api/rest_v1/page/summary/{encoded_name}"

    try:
        result = subprocess.run(
            ['curl', '-s', '-H', 'User-Agent: Kulturperler/1.0', url],
            capture_output=True, text=True, timeout=15
        )

        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)

        if data.get('type') == 'disambiguation' or 'not found' in data.get('title', '').lower():
            return None

        result_data = {
            'bio': data.get('extract', ''),
            'wikipedia_url': data.get('content_urls', {}).get('desktop', {}).get('page'),
            'image_url': None,
            'birth_year': None,
            'death_year': None
        }

        # Get image
        if data.get('thumbnail', {}).get('source'):
            result_data['image_url'] = data['thumbnail']['source']

        # Extract birth/death years
        desc = data.get('description', '') + ' ' + data.get('extract', '')

        # Pattern: (1920-1990) or (1920–1990)
        year_match = re.search(r'\((\d{4})\s*[-–]\s*(\d{4})?\)', desc)
        if year_match:
            result_data['birth_year'] = int(year_match.group(1))
            if year_match.group(2):
                result_data['death_year'] = int(year_match.group(2))
        else:
            # Try "født X" pattern
            birth_match = re.search(r'født\s+(\d{4})', desc, re.IGNORECASE)
            if birth_match:
                result_data['birth_year'] = int(birth_match.group(1))

            death_match = re.search(r'død\s+(\d{4})', desc, re.IGNORECASE)
            if death_match:
                result_data['death_year'] = int(death_match.group(1))

        return result_data
    except Exception as e:
        print(f"    Error fetching {name}: {e}")
        return None


def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_yaml(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def main():
    print("=" * 60)
    print("Enriching new persons with Wikipedia data")
    print("=" * 60)

    # Find all person files with ID >= START_ID
    person_files = []
    for f in PERSONS_DIR.glob('*.yaml'):
        try:
            person_id = int(f.stem)
            if person_id >= START_ID:
                person_files.append(f)
        except ValueError:
            continue

    person_files.sort(key=lambda f: int(f.stem))
    print(f"Found {len(person_files)} new persons to enrich\n")

    enriched = 0
    failed = 0

    for person_file in person_files:
        person = load_yaml(person_file)
        name = person.get('name')

        # Skip if already has bio
        if person.get('bio'):
            continue

        print(f"  {person['id']}: {name}...", end=" ", flush=True)

        wiki_data = fetch_wikipedia_data(name)

        if wiki_data and wiki_data.get('bio'):
            # Truncate bio to 2-3 sentences
            bio = wiki_data['bio']
            sentences = re.split(r'(?<=[.!?])\s+', bio)
            person['bio'] = ' '.join(sentences[:3])

            if wiki_data.get('birth_year'):
                person['birth_year'] = wiki_data['birth_year']
            if wiki_data.get('death_year'):
                person['death_year'] = wiki_data['death_year']
            if wiki_data.get('wikipedia_url'):
                person['wikipedia_url'] = wiki_data['wikipedia_url']

            save_yaml(person_file, person)
            print("OK")
            enriched += 1
        else:
            print("not found")
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"Enriched: {enriched}")
    print(f"Not found: {failed}")


if __name__ == "__main__":
    main()
