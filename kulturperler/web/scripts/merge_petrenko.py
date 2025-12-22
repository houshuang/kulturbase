#!/usr/bin/env python3
"""Merge duplicate Vasily Petrenko entries."""

import yaml
from pathlib import Path

DATA_DIR = Path('data')

def load_yaml(path: Path):
    with open(path) as f:
        return yaml.safe_load(f)

def save_yaml(path: Path, data):
    with open(path, 'w') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

# Replace 4070 with 4063 in all performances
perf_files = list((DATA_DIR / 'performances').glob('*.yaml'))
count = 0

for perf_file in perf_files:
    perf = load_yaml(perf_file)
    changed = False

    for credit in perf.get('credits', []):
        if credit.get('person_id') == 4070:
            credit['person_id'] = 4063
            changed = True

    if changed:
        save_yaml(perf_file, perf)
        count += 1

print(f"Updated {count} performance files")

# Remove duplicate person file
person_file = DATA_DIR / 'persons' / '4070.yaml'
if person_file.exists():
    person_file.unlink()
    print("Removed duplicate person file 4070.yaml")

person_file = DATA_DIR / 'persons' / '4073.yaml'
if person_file.exists():
    person_file.unlink()
    print("Removed duplicate person file 4073.yaml")

print("Done!")
