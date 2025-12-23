#!/usr/bin/env python3
"""
Find and delete YouTube performances where all episodes are under 5 minutes.
Efficient version - loads all data into memory first.
"""

import yaml
import sys
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(line_buffering=True)

DATA_DIR = Path('data')
THRESHOLD_SECONDS = 300  # 5 minutes

def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)

def main():
    print("Loading all data into memory...")

    # Load all episodes
    all_episodes = {}
    episodes_by_performance = defaultdict(list)
    for ep_file in sorted((DATA_DIR / 'episodes').glob('*.yaml')):
        ep = load_yaml(ep_file)
        all_episodes[ep['prf_id']] = {
            'data': ep,
            'file': ep_file,
            'performance_id': ep.get('performance_id')
        }
        if ep.get('performance_id'):
            episodes_by_performance[ep['performance_id']].append(ep['prf_id'])
    print(f"  Loaded {len(all_episodes)} episodes")

    # Load all performances
    all_performances = {}
    for perf_file in sorted((DATA_DIR / 'performances').glob('*.yaml')):
        perf = load_yaml(perf_file)
        all_performances[perf['id']] = {
            'data': perf,
            'file': perf_file
        }
    print(f"  Loaded {len(all_performances)} performances")

    # Load all works (plays)
    all_works = {}
    for work_file in sorted((DATA_DIR / 'plays').glob('*.yaml')):
        work = load_yaml(work_file)
        all_works[work['id']] = {
            'data': work,
            'file': work_file
        }
    print(f"  Loaded {len(all_works)} works")

    # Load all persons
    all_persons = {}
    for person_file in sorted((DATA_DIR / 'persons').glob('*.yaml')):
        person = load_yaml(person_file)
        all_persons[person['id']] = {
            'data': person,
            'file': person_file
        }
    print(f"  Loaded {len(all_persons)} persons")

    # Find YouTube performances where ALL episodes are short
    print("\nAnalyzing YouTube performances...")
    short_performances = []

    for perf_id, perf_info in all_performances.items():
        perf = perf_info['data']
        if perf.get('source') != 'youtube':
            continue

        ep_ids = episodes_by_performance.get(perf_id, [])
        if not ep_ids:
            continue

        # Check all episodes
        durations = []
        for ep_id in ep_ids:
            if ep_id in all_episodes:
                durations.append(all_episodes[ep_id]['data'].get('duration_seconds', 0))

        if not durations:
            continue

        max_duration = max(durations)
        if all(d < THRESHOLD_SECONDS for d in durations):
            short_performances.append({
                'perf_id': perf_id,
                'work_id': perf.get('work_id'),
                'title': perf.get('title', ''),
                'max_duration': max_duration,
                'total_duration': sum(durations),
                'episode_count': len(durations),
                'episode_ids': ep_ids
            })

    short_performances.sort(key=lambda x: x['max_duration'])
    print(f"Found {len(short_performances)} performances where ALL episodes are < 5 min")

    if not short_performances:
        print("Nothing to delete!")
        return

    # Show first 20
    print("\n" + "=" * 80)
    print("PERFORMANCES TO DELETE:")
    print("=" * 80)
    for p in short_performances[:20]:
        print(f"\n{p['perf_id']}: {p['title'][:60]}")
        print(f"  Work: {p['work_id']}, Max: {p['max_duration']}s, Episodes: {p['episode_count']}")
    if len(short_performances) > 20:
        print(f"\n... and {len(short_performances) - 20} more")

    # Find which works would become orphaned
    print("\nFinding orphaned works...")
    perf_ids_to_delete = set(p['perf_id'] for p in short_performances)
    work_ids_in_short = set(p['work_id'] for p in short_performances if p['work_id'])

    # For each work, check if it has performances NOT being deleted
    works_with_other_perfs = set()
    for perf_id, perf_info in all_performances.items():
        if perf_id in perf_ids_to_delete:
            continue
        work_id = perf_info['data'].get('work_id')
        if work_id:
            works_with_other_perfs.add(work_id)

    orphaned_work_ids = work_ids_in_short - works_with_other_perfs
    orphaned_works = [all_works[wid] for wid in orphaned_work_ids if wid in all_works]

    print(f"  {len(orphaned_works)} works would become orphaned")

    # Find which persons would become orphaned
    print("Finding orphaned persons...")
    person_ids_from_orphaned_works = set()
    for wid in orphaned_work_ids:
        if wid in all_works:
            work = all_works[wid]['data']
            if work.get('composer_id'):
                person_ids_from_orphaned_works.add(work['composer_id'])
            if work.get('playwright_id'):
                person_ids_from_orphaned_works.add(work['playwright_id'])

    # Check if these persons are used elsewhere
    persons_used_elsewhere = set()

    # Check other works
    for wid, work_info in all_works.items():
        if wid in orphaned_work_ids:
            continue
        work = work_info['data']
        if work.get('composer_id') in person_ids_from_orphaned_works:
            persons_used_elsewhere.add(work['composer_id'])
        if work.get('playwright_id') in person_ids_from_orphaned_works:
            persons_used_elsewhere.add(work['playwright_id'])

    # Check episode credits
    for ep_id, ep_info in all_episodes.items():
        perf_id = ep_info['performance_id']
        if perf_id in perf_ids_to_delete:
            continue
        for credit in ep_info['data'].get('credits', []):
            pid = credit.get('person_id')
            if pid in person_ids_from_orphaned_works:
                persons_used_elsewhere.add(pid)

    # Check performance credits
    for perf_id, perf_info in all_performances.items():
        if perf_id in perf_ids_to_delete:
            continue
        for credit in perf_info['data'].get('credits', []):
            pid = credit.get('person_id')
            if pid in person_ids_from_orphaned_works:
                persons_used_elsewhere.add(pid)

    orphaned_person_ids = person_ids_from_orphaned_works - persons_used_elsewhere
    orphaned_persons = [all_persons[pid] for pid in orphaned_person_ids if pid in all_persons]

    print(f"  {len(orphaned_persons)} persons would become orphaned:")
    for p in orphaned_persons:
        print(f"    - {p['data']['id']}: {p['data'].get('name', 'unknown')}")

    # Summary and delete
    print("\n" + "=" * 80)
    print(f"DELETING: {len(short_performances)} performances, {len(orphaned_works)} works, {len(orphaned_persons)} persons")
    print("=" * 80)

    # Delete episodes
    deleted_episodes = 0
    for p in short_performances:
        for ep_id in p['episode_ids']:
            if ep_id in all_episodes:
                all_episodes[ep_id]['file'].unlink()
                deleted_episodes += 1
    print(f"  Deleted {deleted_episodes} episodes")

    # Delete performances
    for p in short_performances:
        if p['perf_id'] in all_performances:
            all_performances[p['perf_id']]['file'].unlink()
    print(f"  Deleted {len(short_performances)} performances")

    # Delete orphaned works
    for work_info in orphaned_works:
        work_info['file'].unlink()
    print(f"  Deleted {len(orphaned_works)} works")

    # Delete orphaned persons
    for person_info in orphaned_persons:
        person_info['file'].unlink()
    print(f"  Deleted {len(orphaned_persons)} persons")

    print("\nDone! Run validate_data.py and build_database.py")

if __name__ == '__main__':
    main()
