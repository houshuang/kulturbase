#!/usr/bin/env python3
"""
Add Bergen Philharmonic concerts from concerts.txt to external_resources.yaml
"""

import json
import re
import yaml
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / 'data'

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

def parse_date(date_str):
    """Parse Norwegian date string like 'Opptak fra 18. september 2025'"""
    match = re.search(r'(\d+)\.\s*(\w+)\s+(\d{4})', date_str)
    if match:
        day, month_no, year = match.groups()
        month_map = {
            'januar': '01', 'februar': '02', 'mars': '03', 'april': '04',
            'mai': '05', 'juni': '06', 'juli': '07', 'august': '08',
            'september': '09', 'oktober': '10', 'november': '11', 'desember': '12'
        }
        month = month_map.get(month_no.lower(), '01')
        return f"{year}-{month}-{day.zfill(2)}"
    return None

def extract_composer(title):
    """Extract composer from title like 'Dvorak: Fiolinkonsert'"""
    if ':' in title:
        return title.split(':')[0].strip()
    return None

def main():
    # Load concerts from JSON file
    concerts_file = Path(__file__).parent.parent / 'concerts.txt'
    with open(concerts_file, 'r', encoding='utf-8') as f:
        concerts = json.load(f)

    print(f"Loaded {len(concerts)} concerts from concerts.txt")

    # Load existing resources
    resources_file = DATA_DIR / 'external_resources.yaml'
    existing_resources = load_yaml(resources_file)
    existing_urls = {r['url'] for r in existing_resources}

    # Find max ID
    max_id = max([r['id'] for r in existing_resources], default=0)
    next_id = max_id + 1

    # Add new concerts
    new_resources = []
    skipped = 0

    for concert in concerts:
        url = concert['url']
        if url in existing_urls:
            skipped += 1
            continue

        # Parse metadata from title and date
        title = concert['title']
        date_str = concert.get('date', '')
        recording_date = parse_date(date_str)
        composer = extract_composer(title)

        # Build description
        desc_parts = ['Bergen Filharmoniske Orkester']
        if composer:
            desc_parts.append(f"Komponist: {composer}")
        if recording_date:
            desc_parts.append(f"Innspilt: {recording_date}")

        resource = {
            'id': next_id,
            'url': url,
            'title': title,
            'type': 'bergenphilive',
            'description': '. '.join(desc_parts),
            'added_date': datetime.now().isoformat(),
            'is_working': 1
        }

        new_resources.append(resource)
        next_id += 1

    print(f"Skipped {skipped} existing concerts")
    print(f"Adding {len(new_resources)} new concerts")

    if new_resources:
        updated_resources = existing_resources + new_resources
        save_yaml(resources_file, updated_resources)
        print(f"Saved {len(updated_resources)} total resources to {resources_file}")
    else:
        print("No new concerts to add")

if __name__ == '__main__':
    main()
