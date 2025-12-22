#!/usr/bin/env python3
"""
Fix duplicate person_id assignments in conductor credits from the enrichment script.
The first enrichment run had a bug where all new conductors got ID 4063.
This script identifies which performances have which conductors based on the titles,
creates proper person files, and updates the performance credits.
"""

import yaml
from pathlib import Path
import sqlite3
import re

DATA_DIR = Path('data')
DB_PATH = Path('static/kulturperler.db')

def load_yaml(path: Path):
    with open(path) as f:
        return yaml.safe_load(f)

def save_yaml(path: Path, data):
    with open(path, 'w') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

def extract_conductor_from_title(title: str) -> str:
    """Extract conductor name from title (same logic as main script)."""
    parts = [p.strip() for p in title.split('/')]
    if len(parts) < 3:
        return None

    orchestra_keywords = ['Orchestra', 'Philharmonic', 'Symphony', 'Ensemble', 'Choir', 'Phil.', 'Phil']
    orchestra_idx = None
    for i in range(len(parts) - 1, 0, -1):
        if any(kw in parts[i] for kw in orchestra_keywords):
            orchestra_idx = i
            break

    if orchestra_idx is None:
        if len(parts) >= 3:
            return parts[-1]
        return None

    if orchestra_idx > 1:
        conductor_candidate = parts[orchestra_idx - 1]
        common_composers = [
            'Mozart', 'Beethoven', 'Bach', 'Brahms', 'Wagner', 'Verdi',
            'Tchaikovsky', 'Mahler', 'Strauss', 'Debussy', 'Ravel',
            'Sibelius', 'Dvořák', 'Dvorak', 'Rachmaninoff',
            'Shostakovich', 'Stravinsky', 'Prokofiev', 'Bartók', 'Bartok',
            'Mendelssohn', 'Schumann', 'Chopin', 'Liszt', 'Vivaldi',
            'Handel', 'Haydn', 'Schubert', 'Berlioz', 'Saint-Saëns',
            'Britten', 'Copland',
            'Svendsen', 'Halvorsen', 'Valen', 'Nordheim', 'Sinding',
            'Lully', 'Berio', 'Glass', 'Mussorgsky',
            'Korngold', 'Purcell', 'Orff', 'Dessner', 'Chin', 'Zinovjev',
            'Henriette'
        ]

        if len(conductor_candidate) < 50:
            is_composer = any(comp in conductor_candidate.split() for comp in common_composers)
            if not is_composer:
                name_parts = conductor_candidate.split()
                if 1 <= len(name_parts) <= 3:
                    return conductor_candidate

    return None

def get_next_person_id() -> int:
    """Get next available person ID from filesystem."""
    person_files = list((DATA_DIR / 'persons').glob('*.yaml'))
    if not person_files:
        return 1
    max_id = max([int(f.stem) for f in person_files])
    return max_id + 1

def find_person_by_name(name: str) -> int:
    """Find person by name in persons directory."""
    normalized_search = name.lower().strip()

    for person_file in (DATA_DIR / 'persons').glob('*.yaml'):
        person = load_yaml(person_file)
        person_name = person.get('name', '').lower()
        normalized_name = person.get('normalized_name', '').lower()

        if person_name == normalized_search or normalized_name == normalized_search:
            return person['id']

    return None

# Map of conductor names to person IDs (will be populated)
conductor_map = {}

print("Finding all performances with person_id 4063...")
perf_files = sorted((DATA_DIR / 'performances').glob('*.yaml'))

performances_to_fix = []
for perf_file in perf_files:
    perf = load_yaml(perf_file)
    credits = perf.get('credits', [])

    has_4063_conductor = False
    for credit in credits:
        if credit.get('person_id') == 4063 and credit.get('role') == 'conductor':
            has_4063_conductor = True
            break

    if has_4063_conductor:
        # Extract conductor from title
        title = perf.get('title', '')
        conductor_name = extract_conductor_from_title(title)

        if conductor_name:
            performances_to_fix.append((perf_file, perf['id'], title, conductor_name))

print(f"Found {len(performances_to_fix)} performances to fix")
print()

# Group by conductor name
conductors_needed = {}
for _, perf_id, title, conductor_name in performances_to_fix:
    if conductor_name not in conductors_needed:
        conductors_needed[conductor_name] = []
    conductors_needed[conductor_name].append(perf_id)

print("Conductors that need to be created/mapped:")
for conductor_name, perf_ids in sorted(conductors_needed.items(), key=lambda x: -len(x[1])):
    print(f"  {conductor_name}: {len(perf_ids)} performances")

print()
print("Creating/finding person IDs for conductors...")

for conductor_name in conductors_needed.keys():
    # Check if conductor already exists
    person_id = find_person_by_name(conductor_name)

    if person_id:
        print(f"  Found existing: {conductor_name} -> {person_id}")
        conductor_map[conductor_name] = person_id
    else:
        # Create new person
        person_id = get_next_person_id()
        person_data = {
            'id': person_id,
            'name': conductor_name,
            'normalized_name': conductor_name.lower()
        }

        person_file = DATA_DIR / 'persons' / f'{person_id}.yaml'
        save_yaml(person_file, person_data)

        print(f"  Created new: {conductor_name} -> {person_id}")
        conductor_map[conductor_name] = person_id

print()
print("Updating performance credits...")

for perf_file, perf_id, title, conductor_name in performances_to_fix:
    perf = load_yaml(perf_file)

    # Update credits: replace person_id 4063 with correct conductor ID
    for credit in perf['credits']:
        if credit.get('person_id') == 4063 and credit.get('role') == 'conductor':
            credit['person_id'] = conductor_map[conductor_name]

    save_yaml(perf_file, perf)
    print(f"  Updated performance {perf_id}: {conductor_name} -> {conductor_map[conductor_name]}")

print()
print("Done! Run 'python3 scripts/validate_data.py' to verify.")
print("Then run 'python3 scripts/build_database.py' to rebuild the database.")
