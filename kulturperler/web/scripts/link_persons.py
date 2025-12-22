#!/usr/bin/env python3
"""
Find and merge duplicate person records.

Identifies duplicates by:
- Similar normalized names (fuzzy matching)
- Same person with different name spellings (e.g., "Grieg" vs "Edvard Grieg")

Reports duplicates for review and can merge them.
"""

import yaml
import re
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).parent.parent / "data"


def load_yaml(path: Path) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def save_yaml(path: Path, data: dict):
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def normalize_name(name: str) -> str:
    """Normalize a name for matching."""
    if not name:
        return ""
    name = name.lower().strip()
    # Remove common titles and prefixes
    name = re.sub(r'^(sir|dame|dr\.?|prof\.?|mr\.?|mrs\.?|ms\.?)\s+', '', name)
    # Remove birth/death years in parentheses
    name = re.sub(r'\s*\(\d{4}.*?\)', '', name)
    # Normalize special characters
    name = name.replace('ø', 'o').replace('æ', 'ae').replace('å', 'a')
    name = name.replace('ö', 'o').replace('ä', 'a').replace('ü', 'u')
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()


def get_surname(name: str) -> str:
    """Extract likely surname from a name."""
    parts = name.strip().split()
    if not parts:
        return ""
    # Last word is usually surname (for Western names)
    return parts[-1].lower()


def load_all_persons() -> list:
    """Load all persons with their file paths."""
    persons = []
    for f in (DATA_DIR / "persons").glob("*.yaml"):
        data = load_yaml(f)
        if data:
            data['_path'] = f
            persons.append(data)
    return persons


def find_references(person_id: int) -> dict:
    """Find all references to a person ID."""
    refs = {
        'plays_playwright': [],
        'plays_composer': [],
        'plays_librettist': [],
        'performances': [],
        'episodes': [],
    }

    # Check plays
    for f in (DATA_DIR / "plays").glob("*.yaml"):
        data = load_yaml(f)
        if data.get('playwright_id') == person_id:
            refs['plays_playwright'].append(f)
        if data.get('composer_id') == person_id:
            refs['plays_composer'].append(f)
        if data.get('librettist_id') == person_id:
            refs['plays_librettist'].append(f)

    # Check performances
    for f in (DATA_DIR / "performances").glob("*.yaml"):
        data = load_yaml(f)
        credits = data.get('credits', [])
        for credit in credits:
            if credit.get('person_id') == person_id:
                refs['performances'].append(f)
                break

    # Check episodes
    for f in (DATA_DIR / "episodes").glob("*.yaml"):
        data = load_yaml(f)
        credits = data.get('credits', [])
        for credit in credits:
            if credit.get('person_id') == person_id:
                refs['episodes'].append(f)
                break

    return refs


def update_references(old_id: int, new_id: int):
    """Update all references from old_id to new_id."""
    count = 0

    # Update plays
    for f in (DATA_DIR / "plays").glob("*.yaml"):
        data = load_yaml(f)
        changed = False
        if data.get('playwright_id') == old_id:
            data['playwright_id'] = new_id
            changed = True
        if data.get('composer_id') == old_id:
            data['composer_id'] = new_id
            changed = True
        if data.get('librettist_id') == old_id:
            data['librettist_id'] = new_id
            changed = True
        if changed:
            save_yaml(f, data)
            count += 1

    # Update performances
    for f in (DATA_DIR / "performances").glob("*.yaml"):
        data = load_yaml(f)
        changed = False
        for credit in data.get('credits', []):
            if credit.get('person_id') == old_id:
                credit['person_id'] = new_id
                changed = True
        if changed:
            save_yaml(f, data)
            count += 1

    # Update episodes
    for f in (DATA_DIR / "episodes").glob("*.yaml"):
        data = load_yaml(f)
        changed = False
        for credit in data.get('credits', []):
            if credit.get('person_id') == old_id:
                credit['person_id'] = new_id
                changed = True
        if changed:
            save_yaml(f, data)
            count += 1

    return count


def merge_persons(keep: dict, remove: dict):
    """Merge person data, keeping the more complete record."""
    # Fields to merge (keep non-empty values)
    for field in ['birth_year', 'death_year', 'nationality', 'bio', 'wikipedia_url', 'sceneweb_url', 'wikidata_id']:
        if not keep.get(field) and remove.get(field):
            keep[field] = remove[field]

    return keep


def find_duplicates(persons: list) -> list:
    """Find potential duplicate persons."""
    duplicates = []

    # Group by surname
    by_surname = defaultdict(list)
    for p in persons:
        surname = get_surname(p.get('name', ''))
        if surname and len(surname) > 2:
            by_surname[surname].append(p)

    # Also group by full normalized name
    by_normalized = defaultdict(list)
    for p in persons:
        normalized = normalize_name(p.get('name', ''))
        if normalized:
            by_normalized[normalized].append(p)

    # Find exact normalized name duplicates
    for normalized, group in by_normalized.items():
        if len(group) > 1:
            duplicates.append({
                'type': 'exact_match',
                'key': normalized,
                'persons': group,
            })

    # Find surname-only variations (e.g., "Grieg" vs "Edvard Grieg")
    for surname, group in by_surname.items():
        if len(group) < 2:
            continue

        # Check for short name vs full name
        short_names = [p for p in group if len(p.get('name', '').split()) == 1]
        full_names = [p for p in group if len(p.get('name', '').split()) > 1]

        if short_names and full_names:
            for short in short_names:
                for full in full_names:
                    if short.get('id') != full.get('id'):
                        duplicates.append({
                            'type': 'short_vs_full',
                            'key': surname,
                            'persons': [short, full],
                        })

    return duplicates


def main():
    print("=" * 60)
    print("Find and Merge Duplicate Persons")
    print("=" * 60)

    persons = load_all_persons()
    print(f"\nLoaded {len(persons)} persons")

    duplicates = find_duplicates(persons)
    print(f"Found {len(duplicates)} potential duplicate groups")

    # Filter to high-confidence duplicates
    confirmed = []
    for dup in duplicates:
        if dup['type'] == 'exact_match':
            # Same normalized name - high confidence
            confirmed.append(dup)
        elif dup['type'] == 'short_vs_full':
            # Short vs full name - check if short is substring
            short = dup['persons'][0]
            full = dup['persons'][1]
            short_name = short.get('name', '').lower()
            full_name = full.get('name', '').lower()
            if short_name in full_name:
                confirmed.append(dup)

    print(f"Confirmed {len(confirmed)} duplicate groups for merging")

    merged = 0
    for i, dup in enumerate(confirmed):
        persons_in_group = dup['persons']

        # Sort by completeness (more fields = better)
        def completeness(p):
            score = 0
            if p.get('birth_year'): score += 1
            if p.get('death_year'): score += 1
            if p.get('bio'): score += 2
            if p.get('wikipedia_url'): score += 1
            if len(p.get('name', '').split()) > 1: score += 1  # Full name
            return score

        persons_in_group.sort(key=completeness, reverse=True)

        keep = persons_in_group[0]
        removes = persons_in_group[1:]

        print(f"\n[{i+1}/{len(confirmed)}] Merging duplicates:")
        print(f"  Keep: {keep.get('name')} (id={keep.get('id')})")
        for r in removes:
            print(f"  Remove: {r.get('name')} (id={r.get('id')})")

            # Update all references
            updated = update_references(r.get('id'), keep.get('id'))
            print(f"    Updated {updated} references")

            # Merge data
            keep = merge_persons(keep, r)

            # Delete the duplicate file
            r_path = r.get('_path')
            if r_path and r_path.exists():
                r_path.unlink()
                print(f"    Deleted {r_path.name}")

            merged += 1

        # Save the merged person
        save_yaml(keep.get('_path'), {k: v for k, v in keep.items() if not k.startswith('_')})

    print("\n" + "=" * 60)
    print("DEDUPLICATION COMPLETE")
    print("=" * 60)
    print(f"Merged {merged} duplicate persons")

    print("\nNext steps:")
    print("1. Run: python3 scripts/validate_data.py")
    print("2. Run: python3 scripts/build_database.py")


if __name__ == "__main__":
    main()
