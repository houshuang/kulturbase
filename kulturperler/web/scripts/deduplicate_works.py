#!/usr/bin/env python3
"""
Deduplicate works that share the same wikidata_id.

For each group of duplicates:
1. Keep the first/best work entry
2. Update all performances/episodes to point to the kept work
3. Delete the duplicate work entries
"""

import yaml
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).parent.parent / 'data'


def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_yaml(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def main():
    print("Deduplicating works by wikidata_id...")

    # Group works by wikidata_id
    works_by_qid = defaultdict(list)
    for f in sorted((DATA_DIR / 'plays').glob('*.yaml')):
        data = load_yaml(f)
        if data and data.get('wikidata_id'):
            qid = data['wikidata_id']
            works_by_qid[qid].append({
                'id': data['id'],
                'title': data.get('title', ''),
                'file': f,
                'data': data,
            })

    # Find duplicates
    duplicates = {qid: works for qid, works in works_by_qid.items() if len(works) > 1}
    print(f"Found {len(duplicates)} groups of duplicates ({sum(len(w) for w in duplicates.values())} works total)")

    # Load all performances and episodes to update references
    performances = {}
    for f in (DATA_DIR / 'performances').glob('*.yaml'):
        data = load_yaml(f)
        if data:
            performances[f] = data

    episodes = {}
    for f in (DATA_DIR / 'episodes').glob('*.yaml'):
        data = load_yaml(f)
        if data:
            episodes[f] = data

    stats = {
        'works_merged': 0,
        'works_deleted': 0,
        'performances_updated': 0,
        'episodes_updated': 0,
    }

    # Process each duplicate group
    for qid, works in sorted(duplicates.items()):
        # Choose the "best" work to keep (prefer one with most fields filled)
        def score_work(w):
            d = w['data']
            score = 0
            if d.get('composer_id'): score += 10
            if d.get('wikipedia_url'): score += 5
            if d.get('synopsis'): score += 5
            if d.get('original_title'): score += 2
            if d.get('work_type'): score += 1
            return score

        works_sorted = sorted(works, key=score_work, reverse=True)
        keep_work = works_sorted[0]
        delete_works = works_sorted[1:]

        keep_id = keep_work['id']
        delete_ids = [w['id'] for w in delete_works]

        print(f"\n{qid}: Keep {keep_id} ({keep_work['title'][:40]}), delete {delete_ids}")

        # Update performances that reference deleted works
        for perf_file, perf_data in performances.items():
            if perf_data.get('work_id') in delete_ids:
                old_id = perf_data['work_id']
                perf_data['work_id'] = keep_id
                save_yaml(perf_file, perf_data)
                stats['performances_updated'] += 1
                print(f"  Updated performance {perf_data['id']}: work_id {old_id} -> {keep_id}")

        # Update episodes that reference deleted works
        for ep_file, ep_data in episodes.items():
            if ep_data.get('play_id') in delete_ids:
                old_id = ep_data['play_id']
                ep_data['play_id'] = keep_id
                save_yaml(ep_file, ep_data)
                stats['episodes_updated'] += 1
                print(f"  Updated episode {ep_data['prf_id']}: play_id {old_id} -> {keep_id}")

        # Delete duplicate work files
        for work in delete_works:
            work['file'].unlink()
            stats['works_deleted'] += 1
            print(f"  Deleted work {work['id']}")

        stats['works_merged'] += 1

    print(f"\n\nResults:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == '__main__':
    main()
