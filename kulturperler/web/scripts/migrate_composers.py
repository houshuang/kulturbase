#!/usr/bin/env python3
"""
Migration script to convert combined composer entries to multi-composer format.

This script:
1. Finds plays with combined composer names (e.g., "Mozart, Prokofjev")
2. Identifies/creates individual person entries for each composer
3. Updates play YAML files to use the new composers array format
4. Reports which combined person entries can be deleted after migration
"""

import yaml
import re
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path('data')
PLAYS_DIR = DATA_DIR / 'plays'
PERSONS_DIR = DATA_DIR / 'persons'

# Custom YAML handling to preserve formatting
class CustomDumper(yaml.SafeDumper):
    pass

def str_representer(dumper, data):
    if '\n' in data:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

CustomDumper.add_representer(str, str_representer)

def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)

def save_yaml(path, data):
    with open(path, 'w') as f:
        yaml.dump(data, f, Dumper=CustomDumper, allow_unicode=True, default_flow_style=False, sort_keys=False)

def normalize_name(name):
    """Normalize a name for matching."""
    return name.lower().strip()

def parse_combined_name(name):
    """Parse a combined name into individual composer names."""
    # Skip entries that don't need splitting
    skip_patterns = [
        r'^Various',
        r'^Diverse',
        r'^N/A',
        r'\(attributed',
        r'traditional\)',
    ]
    for pattern in skip_patterns:
        if re.search(pattern, name, re.IGNORECASE):
            return None

    # Split on common separators: ", ", " and ", " og ", "; ", "/"
    # But be careful with names like "Johann Sebastian Bach" - comma followed by space is ok
    parts = re.split(r'\s*(?:,\s+|\s+and\s+|\s+og\s+|;\s*|/)\s*', name)

    # Clean up parts
    cleaned = []
    for part in parts:
        part = part.strip()
        # Skip very short parts (probably artifacts)
        if len(part) < 3:
            continue
        # Skip parts that look like parenthetical notes
        if part.startswith('(') or part.endswith(')'):
            continue
        cleaned.append(part)

    # Only return if we have multiple composers
    if len(cleaned) >= 2:
        return cleaned
    return None

def find_person_by_name(name, persons_index):
    """Find an existing person by name (fuzzy match)."""
    normalized = normalize_name(name)

    # Direct match
    if normalized in persons_index:
        return persons_index[normalized]

    # Manual mapping for known spelling variations (normalized name -> existing normalized name)
    name_mappings = {
        'beethoven': 'ludwig van beethoven',
        'brahms': 'johannes brahms',
        'wagner': 'richard wagner',
        'schubert': 'franz schubert',
        'schumann': 'robert schumann',
        'haydn': 'joseph haydn',
        'dvořák': 'antonín dvořák',
        'dvorak': 'antonín dvořák',
        'halvorsen': 'johan halvorsen',
        'prokofjev': 'sergej prokofjev',
        'pjotr tsjajkovskij': 'pyotr ilyich tchaikovsky',  # Use English spelling that exists
        'tsjajkovskij': 'pyotr ilyich tchaikovsky',
        'dohnanyi': 'ernst von dohnányi',
        'rameau': 'jean-philippe rameau',
        'handel': 'george frideric handel',
        'händel': 'george frideric handel',
        'georg friedrich händel': 'george frideric handel',
        'j.s. bach': 'johann sebastian bach',
        'carl philipp emanuel bach': 'carl philipp emanuel bach',
        'c.p.e. bach': 'carl philipp emanuel bach',
        'george antheil': 'george antheil',
        'georges enescu': 'george enescu',
        'karl johan ankarblom': 'karl-johan ankarblom',
        'dmitrij sjostakovitsj': 'dmitri shostakovich',  # Variant spelling
    }

    # Try mapped name
    if normalized in name_mappings:
        mapped = name_mappings[normalized]
        if mapped in persons_index:
            return persons_index[mapped]

    # Try partial match (last name only, for short names like "Wagner")
    last_name = normalized.split()[-1] if normalized.split() else normalized
    if len(normalized.split()) == 1:  # Single word name (just last name)
        candidates = []
        for norm_name, person_id in persons_index.items():
            parts = norm_name.split()
            # Match if the last part matches
            if parts and parts[-1] == last_name:
                candidates.append((norm_name, person_id))

        # If we have exactly one candidate, use it
        if len(candidates) == 1:
            return candidates[0][1]

    return None

def build_persons_index():
    """Build an index of normalized name -> person_id."""
    index = {}
    for pfile in PERSONS_DIR.glob('*.yaml'):
        person = load_yaml(pfile)
        if person:
            name = person.get('name', '')
            norm_name = normalize_name(name)
            index[norm_name] = person['id']
            # Also index by normalized_name if different
            if person.get('normalized_name'):
                index[person['normalized_name']] = person['id']
    return index

def get_next_person_id():
    """Get the next available person ID."""
    max_id = 0
    for pfile in PERSONS_DIR.glob('*.yaml'):
        try:
            pid = int(pfile.stem)
            if pid > max_id:
                max_id = pid
        except ValueError:
            pass
    return max_id + 1

def main():
    print("Composer Migration Script")
    print("=" * 60)

    # Build persons index
    print("\nBuilding persons index...")
    persons_index = build_persons_index()
    print(f"Found {len(persons_index)} persons")

    # Find plays with combined composer names
    print("\nFinding plays with combined composer names...")
    combined_plays = []

    for play_file in sorted(PLAYS_DIR.glob('*.yaml')):
        play = load_yaml(play_file)
        if not play or not play.get('composer_id'):
            continue

        composer_id = play['composer_id']
        person_file = PERSONS_DIR / f"{composer_id}.yaml"
        if not person_file.exists():
            continue

        person = load_yaml(person_file)
        if not person:
            continue

        name = person.get('name', '')
        parsed = parse_combined_name(name)
        if parsed:
            combined_plays.append({
                'play_file': play_file,
                'play': play,
                'original_composer_id': composer_id,
                'original_name': name,
                'parsed_composers': parsed
            })

    print(f"Found {len(combined_plays)} plays with combined composer names")

    if not combined_plays:
        print("No plays to migrate!")
        return

    # Show what we found
    print("\n" + "-" * 60)
    print("Plays to migrate:")
    print("-" * 60)

    # Group by original composer
    by_composer = defaultdict(list)
    for entry in combined_plays:
        by_composer[entry['original_composer_id']].append(entry)

    # Track what needs to be created vs found
    to_create = set()  # (name,) tuples
    to_find = {}  # name -> person_id (resolved)
    unresolved = set()  # names we couldn't resolve

    for composer_id, entries in sorted(by_composer.items()):
        original_name = entries[0]['original_name']
        parsed = entries[0]['parsed_composers']
        print(f"\n[{composer_id}] {original_name}")
        print(f"  Split into: {parsed}")
        print(f"  Affects {len(entries)} play(s):")
        for e in entries:
            print(f"    - {e['play']['title']}")

        # Try to find existing persons for each composer
        print(f"  Resolving composers:")
        for comp_name in parsed:
            existing_id = find_person_by_name(comp_name, persons_index)
            if existing_id:
                to_find[comp_name] = existing_id
                print(f"    ✓ {comp_name} -> person {existing_id}")
            else:
                unresolved.add(comp_name)
                print(f"    ? {comp_name} -> NOT FOUND")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total plays to update: {len(combined_plays)}")
    print(f"Combined composer entries: {len(by_composer)}")
    print(f"Composers found: {len(to_find)}")
    print(f"Composers NOT found: {len(unresolved)}")

    if unresolved:
        print(f"\nUnresolved composers need manual creation:")
        for name in sorted(unresolved):
            print(f"  - {name}")

    # Ask for confirmation
    print("\n" + "-" * 60)
    response = input("Proceed with migration? (y/N): ")
    if response.lower() != 'y':
        print("Migration cancelled.")
        return

    # Perform migration
    print("\nMigrating...")

    # Create missing persons
    next_id = get_next_person_id()
    created_persons = {}
    for name in sorted(unresolved):
        person_data = {
            'id': next_id,
            'name': name,
            'normalized_name': normalize_name(name)
        }
        person_file = PERSONS_DIR / f"{next_id}.yaml"
        save_yaml(person_file, person_data)
        created_persons[name] = next_id
        persons_index[normalize_name(name)] = next_id
        print(f"  Created person {next_id}: {name}")
        next_id += 1

    # Combine found and created
    all_composers = {**to_find, **created_persons}

    # Update plays
    updated_plays = 0
    for entry in combined_plays:
        play = entry['play']
        play_file = entry['play_file']
        parsed = entry['parsed_composers']

        # Build composers array
        composers = []
        for i, comp_name in enumerate(parsed):
            person_id = all_composers.get(comp_name) or find_person_by_name(comp_name, persons_index)
            if person_id:
                composers.append({
                    'person_id': person_id,
                    'role': 'composer'
                })

        if composers:
            # Update play with composers array
            # Keep composer_id for backward compat (first composer)
            play['composer_id'] = composers[0]['person_id']
            play['composers'] = composers
            save_yaml(play_file, play)
            updated_plays += 1
            print(f"  Updated: {play['title']}")

    print(f"\n✓ Migration complete!")
    print(f"  - {updated_plays} plays updated")
    print(f"  - {len(created_persons)} new persons created")
    print(f"\nCombined person entries that can be deleted:")
    for composer_id in by_composer.keys():
        print(f"  - data/persons/{composer_id}.yaml")

if __name__ == '__main__':
    main()
