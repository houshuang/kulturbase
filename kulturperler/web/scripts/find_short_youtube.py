#!/usr/bin/env python3
"""Find YouTube performances where all episodes are under 5 minutes."""

import yaml
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path('data')
THRESHOLD_SECONDS = 300  # 5 minutes

def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)

# Load all YouTube episodes
episodes_by_performance = defaultdict(list)
for ep_file in (DATA_DIR / 'episodes').glob('YT_*.yaml'):
    ep = load_yaml(ep_file)
    perf_id = ep.get('performance_id')
    if perf_id:
        episodes_by_performance[perf_id].append({
            'prf_id': ep['prf_id'],
            'title': ep.get('title', ''),
            'duration': ep.get('duration_seconds', 0),
            'file': ep_file
        })

# Find performances where ALL episodes are short
short_performances = []
for perf_id, episodes in episodes_by_performance.items():
    all_short = all(ep['duration'] < THRESHOLD_SECONDS for ep in episodes)
    max_duration = max(ep['duration'] for ep in episodes)
    total_duration = sum(ep['duration'] for ep in episodes)

    if all_short:
        perf_file = DATA_DIR / 'performances' / f'{perf_id}.yaml'
        if perf_file.exists():
            perf = load_yaml(perf_file)
            short_performances.append({
                'perf_id': perf_id,
                'work_id': perf.get('work_id'),
                'title': perf.get('title', ''),
                'episodes': episodes,
                'max_duration': max_duration,
                'total_duration': total_duration,
                'episode_count': len(episodes)
            })

# Sort by max duration
short_performances.sort(key=lambda x: x['max_duration'])

print(f"Found {len(short_performances)} performances where ALL episodes are < 5 min\n")
print("=" * 80)

for p in short_performances:
    print(f"\nPerformance {p['perf_id']}: {p['title']}")
    print(f"  Work ID: {p['work_id']}")
    print(f"  Episodes: {p['episode_count']}, Max: {p['max_duration']}s, Total: {p['total_duration']}s")
    for ep in p['episodes']:
        print(f"    - {ep['prf_id']}: {ep['duration']}s - {ep['title'][:60]}")

# Summary
print("\n" + "=" * 80)
print(f"\nSUMMARY:")
print(f"  Performances to delete: {len(short_performances)}")

# Find which works would become orphaned
work_ids = set(p['work_id'] for p in short_performances if p['work_id'])
print(f"  Unique work IDs referenced: {len(work_ids)}")

# Check if these works have other performances
orphaned_works = []
for work_id in work_ids:
    # Find all performances for this work
    has_other = False
    for perf_file in (DATA_DIR / 'performances').glob('*.yaml'):
        perf = load_yaml(perf_file)
        if perf.get('work_id') == work_id and perf['id'] not in [p['perf_id'] for p in short_performances]:
            has_other = True
            break
    if not has_other:
        work_file = DATA_DIR / 'plays' / f'{work_id}.yaml'
        if work_file.exists():
            work = load_yaml(work_file)
            orphaned_works.append({
                'id': work_id,
                'title': work.get('title', ''),
                'composer_id': work.get('composer_id'),
                'playwright_id': work.get('playwright_id')
            })

print(f"  Works that would become orphaned: {len(orphaned_works)}")
for w in orphaned_works:
    print(f"    - {w['id']}: {w['title']} (composer: {w['composer_id']}, playwright: {w['playwright_id']})")
