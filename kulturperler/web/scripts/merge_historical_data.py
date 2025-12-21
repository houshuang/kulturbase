#!/usr/bin/env python3
"""
Merge data from historical database commits into YAML files.

This script extracts data that was lost in previous commits and
merges it into the current YAML-based data structure.
"""

import sqlite3
import yaml
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).parent.parent / 'data'
HISTORY_DIR = Path('/tmp/kulturperler_history')


def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_yaml(path, data):
    # Custom representer for multiline strings
    def str_representer(dumper, data):
        if '\n' in data:
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
        return dumper.represent_scalar('tag:yaml.org,2002:str', data)
    yaml.add_representer(str, str_representer)

    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def merge_play_external_links():
    """Merge play_external_links from ec33ad9 commit."""
    print("Merging play_external_links from ec33ad9...")

    db_path = HISTORY_DIR / 'db_ec33ad9.db'
    if not db_path.exists():
        print(f"  Database not found: {db_path}")
        return 0

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    cursor = conn.execute("SELECT * FROM play_external_links")
    links = cursor.fetchall()

    # Group links by play_id
    links_by_play = defaultdict(list)
    for link in links:
        links_by_play[link['play_id']].append({
            'url': link['url'],
            'title': link['title'],
            'type': link['type'],
            'access_note': link['access_note'] if link['access_note'] else None,
        })

    conn.close()

    # Update play YAML files
    updated = 0
    for play_id, play_links in links_by_play.items():
        play_path = DATA_DIR / 'plays' / f'{play_id}.yaml'
        if not play_path.exists():
            print(f"  Warning: Play {play_id} not found, skipping links")
            continue

        play = load_yaml(play_path)

        # Add external_links if not present
        if 'external_links' not in play:
            play['external_links'] = []

        # Check for duplicates
        existing_urls = {link.get('url') for link in play.get('external_links', [])}
        new_links = [link for link in play_links if link['url'] not in existing_urls]

        if new_links:
            # Clean up None values
            for link in new_links:
                if link['access_note'] is None:
                    del link['access_note']

            play['external_links'].extend(new_links)
            save_yaml(play_path, play)
            updated += 1
            print(f"  Added {len(new_links)} links to play {play_id}")

    print(f"  Updated {updated} plays with external links")
    return updated


def compare_enrichment_data():
    """Compare person/play enrichment across commits to find any lost data."""
    print("\nComparing enrichment data across commits...")

    commits = ['7477a00', 'c7fe3be', 'e476274', '0d9fb39', '78443d0', 'f29adb9']

    for commit in commits:
        db_path = HISTORY_DIR / f'db_{commit}.db'
        if not db_path.exists():
            continue

        conn = sqlite3.connect(db_path)

        # Check person enrichment
        try:
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(wikipedia_url) as wiki,
                    COUNT(wikidata_id) as wikidata,
                    COUNT(bio) as bio,
                    COUNT(birth_year) as birth,
                    COUNT(image_url) as image
                FROM persons
            """)
            row = cursor.fetchone()
            print(f"  {commit}: persons={row[0]} wiki={row[1]} wikidata={row[2]} bio={row[3]} birth={row[4]} image={row[5]}")
        except:
            pass

        conn.close()


def find_missing_person_data():
    """Find person data that exists in old commits but not current."""
    print("\nFinding missing person enrichment data...")

    # Load current YAML persons
    current_persons = {}
    for f in (DATA_DIR / 'persons').glob('*.yaml'):
        p = load_yaml(f)
        current_persons[p['id']] = p

    # Check oldest commit with most data
    commits_to_check = ['c7fe3be', 'e476274', '0d9fb39']

    fields_to_check = ['wikipedia_url', 'wikidata_id', 'bio', 'birth_year', 'death_year', 'image_url']

    for commit in commits_to_check:
        db_path = HISTORY_DIR / f'db_{commit}.db'
        if not db_path.exists():
            continue

        print(f"\n  Checking {commit}...")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        cursor = conn.execute("SELECT * FROM persons")
        old_persons = {row['id']: dict(row) for row in cursor.fetchall()}

        updates_needed = defaultdict(list)

        for pid, old in old_persons.items():
            if pid not in current_persons:
                continue

            current = current_persons[pid]

            for field in fields_to_check:
                old_val = old.get(field)
                current_val = current.get(field)

                if old_val and not current_val:
                    updates_needed[pid].append((field, old_val))

        conn.close()

        if updates_needed:
            print(f"    Found {len(updates_needed)} persons with missing data")
            for pid, fields in list(updates_needed.items())[:5]:
                print(f"      Person {pid}: {[f[0] for f in fields]}")
        else:
            print(f"    No missing data found")


def apply_missing_person_data():
    """Apply missing person data from historical commits."""
    print("\nApplying missing person data...")

    # Load current persons
    current_persons = {}
    for f in (DATA_DIR / 'persons').glob('*.yaml'):
        p = load_yaml(f)
        current_persons[p['id']] = (f, p)

    # Check c7fe3be which had good enrichment
    db_path = HISTORY_DIR / 'db_c7fe3be.db'
    if not db_path.exists():
        print("  Database not found")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    cursor = conn.execute("SELECT * FROM persons")
    old_persons = {row['id']: dict(row) for row in cursor.fetchall()}
    conn.close()

    fields_to_check = ['wikipedia_url', 'wikidata_id', 'bio', 'birth_year', 'death_year', 'sceneweb_url', 'sceneweb_id']

    updated = 0
    for pid, (path, current) in current_persons.items():
        if pid not in old_persons:
            continue

        old = old_persons[pid]
        changed = False

        for field in fields_to_check:
            old_val = old.get(field)
            current_val = current.get(field)

            if old_val and not current_val:
                current[field] = old_val
                changed = True

        if changed:
            save_yaml(path, current)
            updated += 1

    print(f"  Updated {updated} persons with recovered data")
    return updated


def apply_missing_play_data():
    """Apply missing play data from historical commits."""
    print("\nApplying missing play data...")

    # Load current plays
    current_plays = {}
    for f in (DATA_DIR / 'plays').glob('*.yaml'):
        p = load_yaml(f)
        current_plays[p['id']] = (f, p)

    db_path = HISTORY_DIR / 'db_c7fe3be.db'
    if not db_path.exists():
        print("  Database not found")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    cursor = conn.execute("SELECT * FROM plays")
    old_plays = {row['id']: dict(row) for row in cursor.fetchall()}
    conn.close()

    fields_to_check = ['synopsis', 'playwright_id', 'year_written', 'original_title', 'wikipedia_url', 'wikidata_id', 'sceneweb_url', 'sceneweb_id']

    updated = 0
    for pid, (path, current) in current_plays.items():
        if pid not in old_plays:
            continue

        old = old_plays[pid]
        changed = False

        for field in fields_to_check:
            old_val = old.get(field)
            current_val = current.get(field)

            if old_val and not current_val:
                current[field] = old_val
                changed = True

        if changed:
            save_yaml(path, current)
            updated += 1

    print(f"  Updated {updated} plays with recovered data")
    return updated


def main():
    print("=" * 60)
    print("Merging historical data into YAML files")
    print("=" * 60)

    # Step 1: Merge play_external_links
    merge_play_external_links()

    # Step 2: Compare enrichment
    compare_enrichment_data()

    # Step 3: Find missing person data
    find_missing_person_data()

    # Step 4: Apply missing data
    apply_missing_person_data()
    apply_missing_play_data()

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == '__main__':
    main()
