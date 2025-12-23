#!/usr/bin/env python3
"""
Link bokselskap.no authors to persons in our database.

Fetches the list of authors from bokselskap.no/forfattere and matches them
with existing persons in data/persons/*.yaml by name.

Usage:
    python3 scripts/link_bokselskap_authors.py [--dry-run]
"""

import re
import yaml
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from difflib import SequenceMatcher

DATA_DIR = Path('data')
PERSONS_DIR = DATA_DIR / 'persons'

session = requests.Session()
session.headers.update({
    'User-Agent': 'KulturbaseBot/1.0 (https://kulturbase.no)'
})


def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)


def save_yaml(path, data):
    with open(path, 'w') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def fetch_bokselskap_authors():
    """Fetch all authors from bokselskap.no"""
    url = "https://www.bokselskap.no/forfattere"
    resp = session.get(url, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, 'html.parser')

    authors = []
    # Find author list - it's in <ul> inside div.author_list or directly with class
    author_list = soup.find('div', class_='author_list') or soup.find('ul')

    if author_list:
        for li in author_list.find_all('li', class_='page_item'):
            link = li.find('a', href=True)
            if link:
                href = link.get('href', '')
                # Get text content, excluding img alt text
                name = link.get_text(strip=True)
                if name and '/forfattere/' in href:
                    slug = href.split('/forfattere/')[-1]
                    authors.append({
                        'name': name,
                        'slug': slug,
                        'url': href if href.startswith('http') else f"https://www.bokselskap.no{href}"
                    })

    # Deduplicate by slug
    seen = set()
    unique = []
    for a in authors:
        if a['slug'] not in seen:
            seen.add(a['slug'])
            unique.append(a)

    return unique


def normalize_name(name):
    """Normalize a name for comparison"""
    # Remove parenthetical suffixes like (d.e.), (d.y.)
    name = re.sub(r'\s*\([^)]+\)\s*', ' ', name)
    # Lowercase and strip
    name = name.lower().strip()
    # Remove extra whitespace
    name = ' '.join(name.split())
    # Remove common prefixes/suffixes
    name = re.sub(r'^(dr\.|prof\.|hr\.|fru\.|frk\.)\s*', '', name)
    return name


def name_similarity(name1, name2):
    """Calculate similarity between two names"""
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)

    # Exact match
    if n1 == n2:
        return 1.0

    parts1 = n1.split()
    parts2 = n2.split()

    # Count non-abbreviated parts (parts without dots and longer than 2 chars)
    full_parts1 = [p for p in parts1 if '.' not in p and len(p) > 2]
    full_parts2 = [p for p in parts2 if '.' not in p and len(p) > 2]

    # If bokselskap has MORE full name parts than our db, don't match
    # e.g., "Nils Collett Vogt" (3 full) should NOT match "Nils Vogt" (2 full)
    if len(full_parts1) > len(full_parts2):
        return 0.0

    # Check if names match (allowing abbreviations to be ignored)
    set1 = set(full_parts1)
    set2 = set(full_parts2)

    if set1 and set2:
        # All full parts of bokselskap name should be in our db
        if set1.issubset(set2):
            return 0.95

        # Jaccard similarity on name parts
        intersection = len(set1 & set2)
        if intersection >= 2:  # At least 2 name parts match
            return 0.9

    # Sequence matching for fuzzy match
    return SequenceMatcher(None, n1, n2).ratio()


def load_all_persons():
    """Load all persons from YAML files"""
    persons = []
    for path in PERSONS_DIR.glob('*.yaml'):
        try:
            person = load_yaml(path)
            person['_path'] = path
            persons.append(person)
        except Exception as e:
            print(f"Error loading {path}: {e}")
    return persons


def find_best_match(author_name, persons, threshold=0.95):
    """Find the best matching person for an author name"""
    best_match = None
    best_score = 0
    best_name_len = float('inf')

    for person in persons:
        person_name = person.get('name', '')
        score = name_similarity(author_name, person_name)

        if score >= threshold:
            name_len = len(person_name)
            # Prefer higher score, then shorter name (more specific match)
            if score > best_score or (score == best_score and name_len < best_name_len):
                best_score = score
                best_match = person
                best_name_len = name_len

    return best_match, best_score


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Do not modify files')
    args = parser.parse_args()

    print("Fetching authors from bokselskap.no...")
    authors = fetch_bokselskap_authors()
    print(f"Found {len(authors)} authors on bokselskap.no")

    print("\nLoading persons from database...")
    persons = load_all_persons()
    print(f"Loaded {len(persons)} persons")

    # Filter to only persons who might be authors (have some indication)
    # But actually try to match all since we don't know who wrote plays

    matched = []
    unmatched = []
    already_linked = []

    for author in authors:
        # Skip composite entries
        if ' og ' in author['name'] or 'Familien' in author['name']:
            print(f"  Skipping composite: {author['name']}")
            continue

        match, score = find_best_match(author['name'], persons)

        if match:
            if match.get('bokselskap_url'):
                already_linked.append((author, match))
            else:
                matched.append((author, match, score))
        else:
            unmatched.append(author)

    print(f"\n=== Results ===")
    print(f"Matched: {len(matched)}")
    print(f"Already linked: {len(already_linked)}")
    print(f"Unmatched: {len(unmatched)}")

    if matched:
        print(f"\n=== Matches to add ({len(matched)}) ===")
        for author, person, score in sorted(matched, key=lambda x: x[2], reverse=True):
            print(f"  {author['name']:30} -> {person['name']:30} (score: {score:.2f})")

    if unmatched:
        print(f"\n=== Unmatched authors ({len(unmatched)}) ===")
        for author in unmatched:
            print(f"  {author['name']}")

    if args.dry_run:
        print("\n[DRY RUN] No files modified")
        return

    # Update YAML files
    updated = 0
    for author, person, score in matched:
        person_data = load_yaml(person['_path'])
        person_data['bokselskap_url'] = author['url']
        save_yaml(person['_path'], person_data)
        updated += 1
        print(f"Updated {person['_path'].name}: added bokselskap_url")

    print(f"\n=== Summary ===")
    print(f"Updated {updated} person files with bokselskap_url")


if __name__ == '__main__':
    main()
