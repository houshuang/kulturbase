#!/usr/bin/env python3
"""
Fix external links by matching on title instead of ID.

The previous merge used old database IDs which don't match current YAML IDs.
This script:
1. Removes all external_links from YAML files
2. Reads old database to get title -> links mapping
3. Finds plays by title in current YAML
4. Adds links to correct files
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
    def str_representer(dumper, data):
        if '\n' in data:
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
        return dumper.represent_scalar('tag:yaml.org,2002:str', data)
    yaml.add_representer(str, str_representer)

    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def normalize_title(title):
    """Normalize title for matching."""
    if not title:
        return ""
    # Lowercase and strip
    t = title.lower().strip()
    # Handle common variations
    t = t.replace('gjengangere', 'gengangere')
    t = t.replace(' / ', ' ')
    return t


def step1_remove_external_links():
    """Remove external_links from all play YAML files."""
    print("Step 1: Removing external_links from all play YAML files...")

    removed = 0
    for play_file in (DATA_DIR / 'plays').glob('*.yaml'):
        play = load_yaml(play_file)
        if 'external_links' in play:
            del play['external_links']
            save_yaml(play_file, play)
            removed += 1

    print(f"  Removed external_links from {removed} files")
    return removed


def step2_get_links_by_title():
    """Read old database and get links grouped by play title."""
    print("\nStep 2: Reading external links from old database...")

    db_path = HISTORY_DIR / 'db_ec33ad9.db'
    if not db_path.exists():
        print(f"  ERROR: Database not found: {db_path}")
        return {}

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    cursor = conn.execute("""
        SELECT p.title, pel.url, pel.title as link_title, pel.type, pel.access_note
        FROM play_external_links pel
        JOIN plays p ON pel.play_id = p.id
    """)

    links_by_title = defaultdict(list)
    for row in cursor.fetchall():
        link = {
            'url': row['url'],
            'title': row['link_title'],
            'type': row['type'],
        }
        if row['access_note']:
            link['access_note'] = row['access_note']
        links_by_title[row['title']].append(link)

    conn.close()

    print(f"  Found links for {len(links_by_title)} plays")
    for title in sorted(links_by_title.keys()):
        print(f"    - {title}: {len(links_by_title[title])} links")

    return links_by_title


def step3_build_title_to_file_map():
    """Build a map of normalized titles to YAML file paths."""
    print("\nStep 3: Building title -> file map from current YAML files...")

    title_to_file = {}
    for play_file in (DATA_DIR / 'plays').glob('*.yaml'):
        play = load_yaml(play_file)
        title = play.get('title', '')
        norm_title = normalize_title(title)
        title_to_file[norm_title] = (play_file, play, title)

    print(f"  Indexed {len(title_to_file)} plays")
    return title_to_file


def step4_apply_links(links_by_title, title_to_file):
    """Apply links to correct YAML files by matching titles."""
    print("\nStep 4: Applying links to correct YAML files...")

    applied = 0
    not_found = []

    for old_title, links in links_by_title.items():
        norm_title = normalize_title(old_title)

        if norm_title in title_to_file:
            play_file, play, current_title = title_to_file[norm_title]
            play['external_links'] = links
            save_yaml(play_file, play)
            applied += 1
            print(f"  ✓ {old_title} -> {play_file.name}")
        else:
            not_found.append(old_title)

    print(f"\n  Applied links to {applied} plays")

    if not_found:
        print(f"\n  WARNING: Could not find matching plays for:")
        for title in not_found:
            print(f"    - {title}")

    return applied, not_found


def main():
    print("=" * 60)
    print("Fixing external links - matching by title")
    print("=" * 60)

    step1_remove_external_links()
    links_by_title = step2_get_links_by_title()
    title_to_file = step3_build_title_to_file_map()
    applied, not_found = step4_apply_links(links_by_title, title_to_file)

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == '__main__':
    main()
