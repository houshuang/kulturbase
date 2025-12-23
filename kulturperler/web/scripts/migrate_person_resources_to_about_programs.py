#!/usr/bin/env python3
"""
Migrate NRK resources from person YAML files to nrk_about_programs.

This script:
1. Reads all person YAML files with embedded resources
2. For NRK TV/radio URLs, creates nrk_about_programs entries
3. Fetches metadata from NRK API to enrich the entries
4. Keeps non-NRK resources (YouTube, etc.) in person files

Usage:
    python3 scripts/migrate_person_resources_to_about_programs.py [--dry-run]
"""

import yaml
import re
import requests
import time
from pathlib import Path
from datetime import datetime

DATA_DIR = Path('data')
PERSONS_DIR = DATA_DIR / 'persons'
ABOUT_PROGRAMS_DIR = DATA_DIR / 'nrk_about_programs'


def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)


def save_yaml(path, data):
    with open(path, 'w') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def extract_nrk_program_id(url):
    """Extract NRK program ID from URL."""
    # https://tv.nrk.no/se?v=FTEA00004184 -> FTEA00004184
    match = re.search(r'[?&]v=([A-Z]{4}\d+)', url)
    if match:
        return match.group(1)

    # https://tv.nrk.no/program/FTEA00004184 -> FTEA00004184
    match = re.search(r'/program/([A-Z]{4}\d+)', url)
    if match:
        return match.group(1)

    # https://tv.nrk.no/serie/en-udoedelig-mann -> en-udoedelig-mann
    match = re.search(r'/serie/([a-z0-9-]+)(?:/|$)', url)
    if match:
        return match.group(1)

    # https://radio.nrk.no/serie/radioteatret/MKDR62090012 -> MKDR62090012
    match = re.search(r'/([A-Z]{4}\d+)(?:/|$)', url)
    if match:
        return match.group(1)

    return None


def is_nrk_url(url):
    """Check if URL is an NRK TV or radio URL."""
    return 'tv.nrk.no' in url or 'radio.nrk.no' in url


def fetch_nrk_metadata(program_id):
    """Fetch metadata from NRK API."""
    # Try program endpoint first
    url = f'https://psapi.nrk.no/programs/{program_id}'
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json(), 'program'
    except:
        pass

    # Try series endpoint
    url = f'https://psapi.nrk.no/tv/catalog/series/{program_id}'
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json(), 'series'
    except:
        pass

    return None, None


def parse_duration(duration_str):
    """Parse ISO8601 duration to seconds."""
    if not duration_str:
        return None
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?', duration_str)
    if match:
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = float(match.group(3) or 0)
        return int(hours * 3600 + minutes * 60 + seconds)
    return None


def create_about_program_from_resource(resource, person_id, nrk_data, data_type):
    """Create nrk_about_program entry from resource and NRK API data."""
    program_id = extract_nrk_program_id(resource['url'])
    if not program_id:
        return None

    entry = {
        'id': program_id,
        'person_id': person_id,
        'title': resource.get('title', ''),
    }

    # Add description
    if resource.get('description'):
        # Truncate long descriptions
        desc = resource['description']
        if len(desc) > 500:
            desc = desc[:497] + '...'
        entry['description'] = desc

    # Add NRK API data if available
    if nrk_data:
        if data_type == 'program':
            if nrk_data.get('duration'):
                entry['duration_seconds'] = parse_duration(nrk_data['duration'])
            if nrk_data.get('productionYear'):
                entry['year'] = nrk_data['productionYear']
            if nrk_data.get('image', {}).get('webImages'):
                images = nrk_data['image']['webImages']
                entry['image_url'] = images[-1].get('imageUrl', images[0].get('imageUrl'))
            entry['program_type'] = 'portrait'

        elif data_type == 'series':
            seq = nrk_data.get('sequential', {})
            if seq.get('titles', {}).get('title'):
                entry['title'] = seq['titles']['title']
            if seq.get('titles', {}).get('subtitle'):
                entry['description'] = seq['titles']['subtitle']
            if seq.get('image'):
                images = seq['image']
                entry['image_url'] = images[-1].get('url', images[0].get('url'))

            # Get episode count and total duration from embedded seasons
            embedded = nrk_data.get('_embedded', {})
            seasons = embedded.get('seasons', [])
            total_duration = 0
            episode_count = 0
            for season in seasons:
                episodes = season.get('_embedded', {}).get('episodes', [])
                for ep in episodes:
                    episode_count += 1
                    total_duration += ep.get('durationInSeconds', 0)
                    if not entry.get('year') and ep.get('productionYear'):
                        entry['year'] = ep['productionYear']

            if total_duration:
                entry['duration_seconds'] = total_duration
            if episode_count:
                entry['episode_count'] = episode_count
            entry['program_type'] = 'serie'

    # Build NRK URL
    if program_id.startswith(('FTEA', 'ODRP', 'FOLA', 'KOID', 'MKDR', 'DVFJ')):
        entry['nrk_url'] = f'https://tv.nrk.no/program/{program_id}'
    elif re.match(r'^[a-z]', program_id):
        entry['nrk_url'] = f'https://tv.nrk.no/serie/{program_id}'
    else:
        entry['nrk_url'] = resource['url']

    # Set interest score based on content
    entry['interest_score'] = 80

    return entry


def main(dry_run=False):
    print(f"Scanning person files for NRK resources...")

    # Load existing about_programs to avoid duplicates
    existing_ids = set()
    for f in ABOUT_PROGRAMS_DIR.glob('*.yaml'):
        try:
            data = load_yaml(f)
            existing_ids.add(data.get('id'))
        except:
            pass
    print(f"  Found {len(existing_ids)} existing about_programs")

    # Scan person files
    persons_with_resources = []
    for person_file in sorted(PERSONS_DIR.glob('*.yaml')):
        person = load_yaml(person_file)
        if person.get('resources'):
            persons_with_resources.append((person_file, person))

    print(f"  Found {len(persons_with_resources)} persons with resources")

    # Process each person
    created = 0
    skipped_existing = 0
    skipped_non_nrk = 0

    for person_file, person in persons_with_resources:
        person_id = person['id']
        person_name = person.get('name', f'Person {person_id}')

        nrk_resources = []
        other_resources = []

        for resource in person.get('resources', []):
            url = resource.get('url', '')
            if is_nrk_url(url):
                nrk_resources.append(resource)
            else:
                other_resources.append(resource)
                skipped_non_nrk += 1

        if not nrk_resources:
            continue

        print(f"\n{person_name} (ID: {person_id}):")

        for resource in nrk_resources:
            program_id = extract_nrk_program_id(resource['url'])
            if not program_id:
                print(f"  - Could not extract ID from: {resource['url']}")
                continue

            if program_id in existing_ids:
                print(f"  - Already exists: {program_id}")
                skipped_existing += 1
                continue

            print(f"  + Creating: {program_id} - {resource.get('title', 'Untitled')}")

            # Fetch NRK metadata
            nrk_data, data_type = None, None
            if not dry_run:
                nrk_data, data_type = fetch_nrk_metadata(program_id)
                time.sleep(0.2)  # Rate limiting

            # Create about_program entry
            entry = create_about_program_from_resource(resource, person_id, nrk_data, data_type)
            if entry:
                if not dry_run:
                    output_file = ABOUT_PROGRAMS_DIR / f'{program_id}.yaml'
                    save_yaml(output_file, entry)
                existing_ids.add(program_id)
                created += 1

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Summary:")
    print(f"  Created: {created} about_programs")
    print(f"  Skipped (already exists): {skipped_existing}")
    print(f"  Skipped (non-NRK): {skipped_non_nrk}")


if __name__ == '__main__':
    import sys
    dry_run = '--dry-run' in sys.argv
    main(dry_run=dry_run)
