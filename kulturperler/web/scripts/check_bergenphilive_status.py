#!/usr/bin/env python3
"""
Check the current status of bergenphilive performances.
Shows how many have conductors, how many need enrichment, etc.
"""

import yaml
from pathlib import Path
from collections import Counter

DATA_DIR = Path('data')
PERFORMANCES_DIR = DATA_DIR / 'performances'

def load_yaml(path):
    """Load YAML file."""
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f)

def main():
    print("=" * 70)
    print("Bergen Philharmonic Performance Status")
    print("=" * 70)
    print()

    # Find all bergenphilive performances
    performances = []
    for perf_file in sorted(PERFORMANCES_DIR.glob('*.yaml')):
        perf = load_yaml(perf_file)
        if perf.get('source') == 'bergenphilive':
            performances.append(perf)

    print(f"Total bergenphilive performances: {len(performances)}")
    print()

    # Analyze credits
    with_credits = 0
    with_conductor = 0
    without_credits = 0
    role_counts = Counter()

    for perf in performances:
        credits = perf.get('credits', [])
        if credits:
            with_credits += 1
            for credit in credits:
                role = credit.get('role', 'unknown')
                role_counts[role] += 1
                if role == 'conductor':
                    with_conductor += 1
                    break
        else:
            without_credits += 1

    print("Credit Status:")
    print(f"  Performances with any credits:    {with_credits}")
    print(f"  Performances with conductor:      {with_conductor}")
    print(f"  Performances without credits:     {without_credits}")
    print()

    if role_counts:
        print("Credits by role:")
        for role, count in role_counts.most_common():
            print(f"  {role:20s} {count:3d}")
        print()

    # Show some examples
    print("Sample performances WITHOUT conductor:")
    count = 0
    for perf in performances:
        credits = perf.get('credits', [])
        has_conductor = any(c.get('role') == 'conductor' for c in credits)
        if not has_conductor:
            print(f"  - {perf.get('title')} ({perf.get('year')})")
            count += 1
            if count >= 5:
                break
    print()

    print("Sample performances WITH conductor:")
    count = 0
    for perf in performances:
        credits = perf.get('credits', [])
        has_conductor = any(c.get('role') == 'conductor' for c in credits)
        if has_conductor:
            conductor_credit = next(c for c in credits if c.get('role') == 'conductor')
            person_id = conductor_credit.get('person_id')
            print(f"  - {perf.get('title')} ({perf.get('year')}) - person_id: {person_id}")
            count += 1
            if count >= 5:
                break
    print()

    print("=" * 70)
    print(f"Performances needing conductor enrichment: {len(performances) - with_conductor}")
    print("=" * 70)

if __name__ == '__main__':
    main()
