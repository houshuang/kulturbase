#!/usr/bin/env python3
"""
Enrich bergenphilive performances with conductor data.

This script:
1. Loads all bergenphilive performances from data/performances/
2. Looks up the concert URL from external_resources.yaml
3. Uses Gemini with Google Search to find conductor information from the URL
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
API_KEY = os.getenv('GEMINI_KEY')
if not API_KEY:
    print("Error: GEMINI_KEY not found in .env")
    sys.exit(1)

DATA_DIR = Path('data')
PERFORMANCES_DIR = DATA_DIR / 'performances'
PERSONS_DIR = DATA_DIR / 'persons'
EXTERNAL_RESOURCES_FILE = DATA_DIR / 'external_resources.yaml'

def load_yaml(path):
    """Load YAML file."""
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f)

def save_yaml(path, data):
    """Save YAML file."""
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

def get_external_resources():
    """Load external resources and create a lookup by title."""
    resources = load_yaml(EXTERNAL_RESOURCES_FILE)
    bergenphil_resources = {}

    for resource in resources:
        if resource.get('type') == 'bergenphilive':
            title = resource.get('title', '')
            # Store by title for easy lookup
            bergenphil_resources[title] = resource

    return bergenphil_resources

def search_conductor_with_gemini(concert_url, title, year):
    """Use Gemini with Google Search to find conductor information."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={API_KEY}"

    query = f"""Find the conductor (dirigent) for this Bergen Philharmonic concert:
URL: {concert_url}
Title: {title}
Year: {year}

Search the URL or search for "Bergen Filharmoniske {title} {year} dirigent".
Provide ONLY the conductor's full name, or "NOT_FOUND" if you cannot find it.
Format: Just the name like "Edward Gardner" or "NOT_FOUND"
"""

    payload = {
        "contents": [{"parts": [{"text": query}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.1}
    }

    try:
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        result = r.json()

        # Extract text from response
        if 'candidates' in result and len(result['candidates']) > 0:
            candidate = result['candidates'][0]
            if 'content' in candidate and 'parts' in candidate['content']:
                parts = candidate['content']['parts']
                text_parts = [p['text'] for p in parts if 'text' in p]
                return '\n'.join(text_parts) if text_parts else None
        return None
    except Exception as e:
        print(f"  Error calling Gemini: {e}")
        return None

def get_all_bergenphilive_performances():
    """Get all bergenphilive performance files."""
    performances = []
    for perf_file in sorted(PERFORMANCES_DIR.glob('*.yaml')):
        perf = load_yaml(perf_file)
        if perf.get('source') == 'bergenphilive':
            perf['_file'] = perf_file
            performances.append(perf)
    return performances

def get_all_persons():
    """Load all persons into a lookup dictionary."""
    persons = {}
    for person_file in PERSONS_DIR.glob('*.yaml'):
        person = load_yaml(person_file)
        person['_file'] = person_file
        persons[person['id']] = person
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

def extract_conductor_from_response(response_text):
    """Extract conductor name from Gemini response."""
    if not response_text:
        return None

    response_text = response_text.strip()

    # Check for explicit NOT_FOUND
    if 'NOT_FOUND' in response_text.upper():
        return None

    # Common indicators that there's no conductor info
    response_lower = response_text.lower()
    if any(phrase in response_lower for phrase in [
        'could not find', 'no information', 'unable to find',
        'not available', 'no conductor', 'not specified', 'cannot find'
    ]):
        return None

    # If response is short and looks like a name, return it
    if len(response_text) < 50 and not '\n' in response_text:
        # Clean up the name
        name = response_text.strip()
        name = re.sub(r'^(Conductor|Dirigent):\s*', '', name, flags=re.IGNORECASE)
        name = name.split('(')[0].strip()  # Remove parenthetical
        name = name.split(',')[0].strip()  # Take first part if comma-separated
        if name and len(name) > 2 and not name.lower().startswith('http'):
            return name

    # Look for conductor mentions in multi-line response
    lines = response_text.split('\n')
    for line in lines:
        line_lower = line.lower()
        if 'dirigent' in line_lower or 'conductor' in line_lower:
            # Try to extract the name
            # Common patterns: "Dirigent: Name" or "Conductor: Name"
            for sep in [':', '-', '–']:
                if sep in line:
                    parts = line.split(sep, 1)
                    if len(parts) == 2:
                        name = parts[1].strip()
                        # Clean up the name
                        name = name.split('(')[0].strip()  # Remove parenthetical
                        name = name.split(',')[0].strip()  # Take first part if comma-separated
                        if name and len(name) > 2 and not name.lower().startswith('http'):
                            return name

    return None

def enrich_performance_with_conductor(performance, persons, external_resources):
    """Try to find and add conductor information for a performance."""
    title = performance.get('title', '')
    year = performance.get('year', '')
    description = performance.get('description', '')

    print(f"\nProcessing: {title} ({year})")

    # Check if already has conductor
    credits = performance.get('credits', [])
    if any(c.get('role') == 'conductor' for c in credits):
        print("  Already has conductor, skipping")
        return False

    # Find the concert URL from external resources
    concert_url = None
    if title in external_resources:
        concert_url = external_resources[title].get('url')
        print(f"  URL: {concert_url}")
    else:
        print(f"  Warning: No URL found in external_resources for this performance")
        # Try without URL
        concert_url = ""

    # Search for conductor
    print("  Searching for conductor...")
    response = search_conductor_with_gemini(concert_url, title, year)

    if response:
        print(f"  Gemini response: {response[:150]}...")
        conductor_name = extract_conductor_from_response(response)

        if conductor_name:
            print(f"  Found conductor: {conductor_name}")

            # Find or create person
            person = find_person_by_name(conductor_name, persons)
            if not person:
                person = create_person(conductor_name, persons)
            else:
                print(f"  Found existing person: {person['name']} (ID: {person['id']})")

            # Add conductor credit
            if 'credits' not in performance:
                performance['credits'] = []

            performance['credits'].append({
                'person_id': person['id'],
                'role': 'conductor'
            })

            # Save updated performance
            save_yaml(performance['_file'], performance)
            print(f"  ✓ Updated performance with conductor")
            return True
        else:
            print("  Could not extract conductor name from response")
    else:
        print("  No response from Gemini")

    return False

def main():
    print("Enriching bergenphilive performances with conductor data...")
    print("=" * 70)

    # Load all data
    print("\nLoading data...")
    performances = get_all_bergenphilive_performances()
    persons = get_all_persons()
    external_resources = get_external_resources()

    print(f"Found {len(performances)} bergenphilive performances")
    print(f"Found {len(persons)} persons in database")
    print(f"Found {len(external_resources)} bergenphilive external resources")

    # Process each performance
    updated_count = 0
    skipped_count = 0

    for i, performance in enumerate(performances, 1):
        print(f"\n[{i}/{len(performances)}]", end=" ")

        try:
            if enrich_performance_with_conductor(performance, persons, external_resources):
                updated_count += 1
            else:
                skipped_count += 1

            # Rate limiting - wait between API calls
            if i < len(performances):
                time.sleep(2)  # 2 seconds between requests

        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
            break
        except Exception as e:
            print(f"  Error processing performance: {e}")
            import traceback
            traceback.print_exc()
            continue

    print("\n" + "=" * 70)
    print(f"Summary:")
    print(f"  Updated: {updated_count} performances with conductor information")
    print(f"  Skipped: {skipped_count} performances (already had conductor or not found)")
    print("\nNext steps:")
    print("1. Review the changes: git diff data/")
    print("2. Validate: python3 scripts/validate_data.py")
    print("3. Rebuild database: python3 scripts/build_database.py")

if __name__ == '__main__':
    main()
