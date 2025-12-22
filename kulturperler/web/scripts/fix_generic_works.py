#!/usr/bin/env python3
"""
Fix generic works (e.g., "MOZART", "Beethoven") by creating proper work entries
based on the actual video titles.
"""

import yaml
import re
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).parent.parent / 'data'

# Generic work IDs to fix
GENERIC_WORK_IDS = [
    1885, 1783, 1832, 1568, 1802, 1543, 1852, 1798, 1853, 1720,
    1820, 1816, 1877, 1835, 1828, 1930, 1845, 1917, 1921, 1866, 1882
]


def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_yaml(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def get_next_work_id():
    """Find next available work ID."""
    max_id = 0
    for f in (DATA_DIR / 'plays').glob('*.yaml'):
        w = load_yaml(f)
        if w and w.get('id'):
            max_id = max(max_id, w['id'])
    return max_id + 1


def parse_work_title(episode_title, composer_name):
    """Extract actual work title from episode title."""
    title = episode_title

    # Remove composer prefix (e.g., "MOZART - ", "J.S. BACH - ")
    patterns = [
        r'^[A-Z\.\s]+\s*[-–—]\s*',  # "MOZART - ", "J. S. BACH - "
        r'^[A-Z][a-z]+\s*[-–—]\s*',  # "Mozart - "
    ]
    for pattern in patterns:
        title = re.sub(pattern, '', title)

    # Remove movement indicators at the end
    title = re.sub(r'\s*[-–—]\s*(I+V?|IV|V?I{0,3})[:.]?\s*[A-Za-z]+.*$', '', title)
    title = re.sub(r'\s*[-–—]\s*\d+\.\s*[A-Za-z]+.*$', '', title)
    title = re.sub(r'\s*[-–—]\s*(Part|Pt)\s*\d+.*$', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\s*[-–—]\s*COMPLETE.*$', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\s*[-–—]\s*360$', '', title)

    # Clean up
    title = title.strip(' -–—:')

    return title if title else episode_title


def determine_work_type(title):
    """Determine work type from title."""
    title_lower = title.lower()

    if 'symphony' in title_lower or 'symfoni' in title_lower:
        return 'symphony'
    elif 'concerto' in title_lower or 'konsert' in title_lower:
        return 'concerto'
    elif 'quartet' in title_lower or 'quintet' in title_lower or 'trio' in title_lower:
        return 'chamber'
    elif 'sonata' in title_lower or 'sonate' in title_lower:
        return 'chamber'
    elif 'opera' in title_lower or 'figaro' in title_lower or 'flauto' in title_lower:
        return 'opera'
    elif 'requiem' in title_lower or 'mass' in title_lower or 'magnificat' in title_lower:
        return 'choral'
    elif 'suite' in title_lower or 'divertimento' in title_lower:
        return 'orchestral'
    elif 'overture' in title_lower or 'ouverture' in title_lower:
        return 'orchestral'
    else:
        return 'orchestral'


def main():
    print("Fixing generic works...")

    next_work_id = get_next_work_id()
    works_created = 0
    perfs_updated = 0

    for generic_id in GENERIC_WORK_IDS:
        work_file = DATA_DIR / 'plays' / f'{generic_id}.yaml'
        if not work_file.exists():
            continue

        generic_work = load_yaml(work_file)
        composer_name = generic_work.get('title', '')
        composer_id = generic_work.get('composer_id')

        print(f"\n[{generic_id}] {composer_name}")

        # Find all performances linked to this generic work
        perfs_to_fix = []
        for pf in (DATA_DIR / 'performances').glob('*.yaml'):
            perf = load_yaml(pf)
            if perf and perf.get('work_id') == generic_id:
                # Find the episode
                for ef in (DATA_DIR / 'episodes').glob('*.yaml'):
                    ep = load_yaml(ef)
                    if ep and ep.get('performance_id') == perf['id']:
                        perfs_to_fix.append({
                            'perf_file': pf,
                            'perf': perf,
                            'episode_title': ep.get('title', ''),
                        })
                        break

        # Group by actual work title
        works_map = defaultdict(list)  # work_title -> list of (perf_file, perf)

        for item in perfs_to_fix:
            work_title = parse_work_title(item['episode_title'], composer_name)
            works_map[work_title].append((item['perf_file'], item['perf']))

        print(f"  Found {len(perfs_to_fix)} performances, {len(works_map)} unique works")

        # Create new works and update performances
        for work_title, perfs in works_map.items():
            # Create new work
            work_type = determine_work_type(work_title)
            new_work = {
                'id': next_work_id,
                'title': work_title,
                'category': 'konsert',
                'type': work_type,
            }
            if composer_id:
                new_work['composer_id'] = composer_id

            save_yaml(DATA_DIR / 'plays' / f'{next_work_id}.yaml', new_work)
            print(f"    Created [{next_work_id}] {work_title[:50]}... ({len(perfs)} perfs)")

            # Update performances
            for perf_file, perf in perfs:
                perf['work_id'] = next_work_id
                save_yaml(perf_file, perf)
                perfs_updated += 1

            next_work_id += 1
            works_created += 1

        # Delete the generic work
        work_file.unlink()
        print(f"  Deleted generic work {generic_id}")

    print(f"\n\nResults:")
    print(f"  Works created: {works_created}")
    print(f"  Performances updated: {perfs_updated}")
    print(f"  Generic works deleted: {len(GENERIC_WORK_IDS)}")


if __name__ == '__main__':
    main()
