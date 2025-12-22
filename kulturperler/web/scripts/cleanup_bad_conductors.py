#!/usr/bin/env python3
"""Remove bad conductor credits (person_id 4203) from performance files."""

import yaml
from pathlib import Path

PERFORMANCES_DIR = Path('data/performances')

fixed_count = 0

for perf_file in PERFORMANCES_DIR.glob('*.yaml'):
    with open(perf_file) as f:
        perf_data = yaml.safe_load(f)

    if 'credits' not in perf_data:
        continue

    # Filter out person_id 4203 conductors
    original_credits = perf_data['credits']
    new_credits = [c for c in original_credits if not (c.get('person_id') == 4203 and c.get('role') == 'conductor')]

    if len(new_credits) != len(original_credits):
        perf_data['credits'] = new_credits
        if not new_credits:
            del perf_data['credits']

        with open(perf_file, 'w') as f:
            yaml.dump(perf_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        fixed_count += 1
        print(f"Fixed {perf_file.name}")

print(f"\nCleaned up {fixed_count} performance files")
