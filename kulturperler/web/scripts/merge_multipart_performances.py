#!/usr/bin/env python3
"""
Merge multi-part YouTube performances that are clearly from the same concert.

STRICT matching - only merges when:
- Same work_id
- Title has clear movement indicator (I:, II:, 1st mvt, etc.)
- Base title before movement indicator is nearly identical
"""

import yaml
import re
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).parent.parent / 'data'


def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)


def save_yaml(path, data):
    with open(path, 'w') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


# Strict movement patterns - must have these to be considered a "part"
MOVEMENT_PATTERNS = [
    # Roman numerals with separator
    r'(.*?)\s*[-–:]\s*(I|II|III|IV|V|VI|VII|VIII|IX|X)\s*[-–:.]',
    r'(.*?)\s*[-–:]\s*(I|II|III|IV|V|VI|VII|VIII|IX|X)\s*$',
    # Part numbers
    r'(.*?)\s*[-–:]\s*Part\s*(\d+)',
    r'(.*?)\s*[-–:]\s*part\s*(\d+)\s*of\s*\d+',
    # Movement with number
    r'(.*?)\s*[-–:]\s*(\d+)\s*(st|nd|rd|th)\s*(mov|mvt|movement)',
    # Numbered parts in parens
    r'(.*?)\s*\((\d+)/\d+\)',
    # BWV parts
    r'(.*?BWV\s*\d+)\s*[-–:]\s*Part\s*(\d+)',
]


def extract_series_key(title):
    """
    Extract series key if title appears to be part of a multi-part series.
    Returns (base_title, part_indicator) or (None, None) if not a series.
    """
    for pattern in MOVEMENT_PATTERNS:
        match = re.match(pattern, title, re.IGNORECASE)
        if match:
            base = match.group(1).strip()
            part = match.group(2)
            # Normalize base
            base = re.sub(r'\s+', ' ', base)
            base = base.rstrip(' -–:')
            if len(base) > 15:  # Must have substantial base title
                return base, part
    return None, None


def normalize_base(base):
    """Normalize base title for comparison."""
    # Lowercase and remove special chars
    norm = re.sub(r'[^\w\s]', '', base.lower())
    norm = ' '.join(norm.split())
    return norm


def main():
    print("Finding multi-part YouTube performances to merge (STRICT mode)...")
    print()

    # Load all YouTube performances
    youtube_perfs = []
    for f in sorted((DATA_DIR / 'performances').glob('*.yaml')):
        data = load_yaml(f)
        if data and data.get('source') == 'youtube' and data.get('work_id'):
            base, part = extract_series_key(data.get('title', ''))
            if base:
                youtube_perfs.append({
                    'id': data['id'],
                    'work_id': data['work_id'],
                    'title': data.get('title', ''),
                    'base': base,
                    'part': part,
                    'norm_base': normalize_base(base),
                    'file': f,
                    'data': data,
                })

    print(f"Found {len(youtube_perfs)} performances with movement indicators")

    # Group by work_id + normalized base title
    groups = defaultdict(list)
    for p in youtube_perfs:
        key = (p['work_id'], p['norm_base'])
        groups[key].append(p)

    # Filter to groups with multiple parts
    merge_groups = []
    for key, perfs in groups.items():
        if len(perfs) >= 2:
            merge_groups.append({
                'work_id': key[0],
                'base': perfs[0]['base'],
                'performances': sorted(perfs, key=lambda x: x['id']),
            })

    print(f"Found {len(merge_groups)} groups to merge")
    print()

    if not merge_groups:
        print("No groups to merge.")
        return

    # Preview
    print("=" * 70)
    print("PREVIEW - Groups to merge:")
    print("=" * 70)

    for g in merge_groups:
        print(f"\nWork {g['work_id']}: {g['base'][:55]}")
        for p in g['performances']:
            print(f"  {p['id']}: {p['title'][:60]}")

    print()
    print("=" * 70)
    print(f"Total: {len(merge_groups)} groups, {sum(len(g['performances']) for g in merge_groups)} performances")
    print()

    response = input("Proceed with merge? (yes/no): ")
    if response.lower() != 'yes':
        print("Aborted.")
        return

    # Load episodes for updating
    episodes = {}
    for f in (DATA_DIR / 'episodes').glob('*.yaml'):
        data = load_yaml(f)
        if data:
            episodes[f] = data

    # Perform merges
    stats = {'groups_merged': 0, 'performances_deleted': 0, 'episodes_updated': 0}

    for g in merge_groups:
        perfs = g['performances']
        keep = perfs[0]  # Keep lowest ID
        delete_perfs = perfs[1:]
        delete_ids = [p['id'] for p in delete_perfs]

        # Update kept performance title to base
        keep['data']['title'] = g['base']
        save_yaml(keep['file'], keep['data'])

        # Update episodes
        for ep_file, ep_data in episodes.items():
            if ep_data.get('performance_id') in delete_ids:
                ep_data['performance_id'] = keep['id']
                save_yaml(ep_file, ep_data)
                stats['episodes_updated'] += 1

        # Delete merged
        for p in delete_perfs:
            p['file'].unlink()
            stats['performances_deleted'] += 1

        stats['groups_merged'] += 1
        print(f"Merged work {g['work_id']}: kept {keep['id']}, deleted {delete_ids}")

    print(f"\nResults:")
    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == '__main__':
    main()
