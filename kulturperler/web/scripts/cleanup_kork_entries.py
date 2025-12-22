#!/usr/bin/env python3
"""
Clean up KORK-related person entries:
1. Replace garbage person references with institution links
2. Extract conductor names and create person entries
3. Add conductor credits to performances
"""

import yaml
import re
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / 'data'

# KORK institution ID
KORK_ID = 1

# Garbage entries to clean up
GARBAGE_ENTRIES = {
    3327: "Kringkastingsorkestret; KORK",  # Orchestra - just reference institution
    3404: "KORK uten strykere i musikk av Stravinskij: Symfonier for blåsere og Konsert for piano og blåsere med Gunilla Süssmann.",
    3409: "KORK, Nils Eirik Måseidvåg.",  # Extract conductor
    3411: "KORK. Nils Erik Måseidvåg, dirigent - Kyung Jun Lee, cello",  # Extract conductor and soloist
}

# Known conductors to extract (name -> person_id if exists, else None)
CONDUCTORS_TO_CREATE = {
    "Nils Eirik Måseidvåg": None,  # Will create new person
    "Gunilla Süssmann": None,  # Pianist/soloist
    "Kyung Jun Lee": None,  # Cellist/soloist
}


def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_yaml(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def get_next_person_id():
    """Find the next available person ID."""
    persons_dir = DATA_DIR / 'persons'
    max_id = 0
    for f in persons_dir.glob('*.yaml'):
        p = load_yaml(f)
        if p and p.get('id'):
            max_id = max(max_id, p['id'])
    return max_id + 1


def create_conductor(name, next_id):
    """Create a new person entry for a conductor."""
    person = {
        'id': next_id,
        'name': name,
        'normalized_name': name.lower(),
    }
    filepath = DATA_DIR / 'persons' / f'{next_id}.yaml'
    save_yaml(filepath, person)
    print(f"  Created conductor: [{next_id}] {name}")
    return next_id


def update_performance(perf_id, kork_person_id, conductor_id=None, soloist_credits=None):
    """Update a performance to use institution instead of person for KORK."""
    filepath = DATA_DIR / 'performances' / f'{perf_id}.yaml'
    if not filepath.exists():
        print(f"  Warning: Performance {perf_id} not found")
        return

    perf = load_yaml(filepath)

    # Remove the garbage person credit
    new_credits = [c for c in perf.get('credits', []) if c.get('person_id') != kork_person_id]

    # Add conductor if provided
    if conductor_id:
        new_credits.append({'person_id': conductor_id, 'role': 'conductor'})

    # Add any soloist credits
    if soloist_credits:
        new_credits.extend(soloist_credits)

    perf['credits'] = new_credits

    # Add institution link
    if 'institutions' not in perf:
        perf['institutions'] = []

    # Check if KORK already linked
    if not any(i.get('institution_id') == KORK_ID for i in perf['institutions']):
        perf['institutions'].append({'institution_id': KORK_ID, 'role': 'orchestra'})

    save_yaml(filepath, perf)
    print(f"  Updated performance {perf_id}")


def main():
    print("Cleaning up KORK entries...")

    # Find performances referencing garbage entries
    perfs_dir = DATA_DIR / 'performances'

    # Track which performances need updating
    updates_needed = {}  # perf_id -> garbage_person_id

    for f in perfs_dir.glob('*.yaml'):
        perf = load_yaml(f)
        if not perf:
            continue
        for credit in perf.get('credits', []):
            if credit.get('person_id') in GARBAGE_ENTRIES:
                updates_needed[perf['id']] = credit['person_id']

    print(f"Found {len(updates_needed)} performances to update")

    # Create conductor person entries
    next_id = get_next_person_id()
    conductor_ids = {}

    # Create Nils Eirik Måseidvåg
    conductor_ids['Nils Eirik Måseidvåg'] = create_conductor('Nils Eirik Måseidvåg', next_id)
    next_id += 1

    # Create Gunilla Süssmann (pianist)
    conductor_ids['Gunilla Süssmann'] = create_conductor('Gunilla Süssmann', next_id)
    next_id += 1

    # Create Kyung Jun Lee (cellist)
    conductor_ids['Kyung Jun Lee'] = create_conductor('Kyung Jun Lee', next_id)
    next_id += 1

    # Update each performance
    for perf_id, garbage_id in updates_needed.items():
        if garbage_id == 3327:
            # Just replace with institution, no conductor
            update_performance(perf_id, garbage_id)
        elif garbage_id == 3409:
            # KORK, Nils Eirik Måseidvåg - add conductor
            update_performance(perf_id, garbage_id, conductor_ids['Nils Eirik Måseidvåg'])
        elif garbage_id == 3404:
            # KORK with Gunilla Süssmann as soloist
            update_performance(perf_id, garbage_id, soloist_credits=[
                {'person_id': conductor_ids['Gunilla Süssmann'], 'role': 'soloist'}
            ])
        elif garbage_id == 3411:
            # KORK with conductor and cellist
            update_performance(perf_id, garbage_id,
                             conductor_ids['Nils Eirik Måseidvåg'],
                             [{'person_id': conductor_ids['Kyung Jun Lee'], 'role': 'soloist'}])

    # Delete garbage person entries
    print("\nDeleting garbage person entries...")
    for pid in GARBAGE_ENTRIES:
        filepath = DATA_DIR / 'persons' / f'{pid}.yaml'
        if filepath.exists():
            filepath.unlink()
            print(f"  Deleted {pid}.yaml")

    print("\nDone!")


if __name__ == '__main__':
    main()
