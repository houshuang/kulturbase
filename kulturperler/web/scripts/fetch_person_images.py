#!/usr/bin/env python3
"""
Fetch portrait images for main people (playwrights/composers) from Wikidata/Wikipedia.

Usage:
    python3 scripts/fetch_person_images.py [--dry-run] [--limit N]

Progress is saved to /tmp/person_images_progress.json for restartability.
"""

import os
import sys
import json
import time
import re
import requests
import yaml
from pathlib import Path
from urllib.parse import unquote, quote

# Directories
DATA_DIR = Path('data')
PERSONS_DIR = DATA_DIR / 'persons'
IMAGES_DIR = Path('static/images/persons')
PROGRESS_FILE = Path('/tmp/person_images_progress.json')

# Ensure images directory exists
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Session for HTTP requests
session = requests.Session()
session.headers.update({
    'User-Agent': 'KulturbaseBot/1.0 (https://kulturbase.no; contact@kulturbase.no)'
})


def load_progress():
    """Load progress from file."""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {'processed': [], 'failed': [], 'success': []}


def save_progress(progress):
    """Save progress to file."""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def load_yaml(path):
    """Load a YAML file."""
    with open(path) as f:
        return yaml.safe_load(f)


def save_yaml(path, data):
    """Save a YAML file."""
    with open(path, 'w') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def get_main_persons():
    """Get all persons who are playwrights or composers."""
    # First, find which person IDs are playwrights or composers
    playwright_ids = set()
    composer_ids = set()

    plays_dir = DATA_DIR / 'plays'
    if plays_dir.exists():
        for play_file in plays_dir.glob('*.yaml'):
            try:
                play = load_yaml(play_file)
                if play.get('playwright_id'):
                    playwright_ids.add(play['playwright_id'])
                if play.get('composer_id'):
                    composer_ids.add(play['composer_id'])
            except Exception as e:
                print(f"Error loading {play_file}: {e}")

    # Also check works directory if it exists
    works_dir = DATA_DIR / 'works'
    if works_dir.exists():
        for work_file in works_dir.glob('*.yaml'):
            try:
                work = load_yaml(work_file)
                if work.get('playwright_id'):
                    playwright_ids.add(work['playwright_id'])
                if work.get('composer_id'):
                    composer_ids.add(work['composer_id'])
            except Exception as e:
                print(f"Error loading {work_file}: {e}")

    main_ids = playwright_ids | composer_ids
    print(f"Found {len(main_ids)} main people ({len(playwright_ids)} playwrights, {len(composer_ids)} composers)")

    # Load person data
    persons = []
    for person_file in PERSONS_DIR.glob('*.yaml'):
        try:
            person = load_yaml(person_file)
            if person.get('id') in main_ids:
                person['_file'] = person_file
                persons.append(person)
        except Exception as e:
            print(f"Error loading {person_file}: {e}")

    # Sort by ID for consistent ordering
    persons.sort(key=lambda p: p['id'])
    return persons


def get_wikidata_image(wikidata_id):
    """Fetch image filename from Wikidata P18 property."""
    if not wikidata_id:
        return None

    # Clean the ID
    wikidata_id = wikidata_id.strip()
    if not wikidata_id.startswith('Q'):
        wikidata_id = 'Q' + wikidata_id

    url = f"https://www.wikidata.org/wiki/Special:EntityData/{wikidata_id}.json"

    try:
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        entity = data.get('entities', {}).get(wikidata_id, {})
        claims = entity.get('claims', {})

        # P18 is the "image" property
        if 'P18' in claims:
            image_claim = claims['P18'][0]
            image_value = image_claim.get('mainsnak', {}).get('datavalue', {}).get('value')
            if image_value:
                return image_value
    except Exception as e:
        print(f"  Wikidata error for {wikidata_id}: {e}")

    return None


def get_wikipedia_image(wikipedia_url):
    """Try to extract main image from Wikipedia page."""
    if not wikipedia_url:
        return None

    try:
        # Extract page title from URL
        match = re.search(r'wikipedia\.org/wiki/(.+)$', wikipedia_url)
        if not match:
            return None

        page_title = unquote(match.group(1))

        # Determine language
        lang_match = re.search(r'(\w+)\.wikipedia\.org', wikipedia_url)
        lang = lang_match.group(1) if lang_match else 'en'

        # Use Wikipedia API to get page images
        api_url = f"https://{lang}.wikipedia.org/w/api.php"
        params = {
            'action': 'query',
            'titles': page_title,
            'prop': 'pageimages',
            'piprop': 'original',
            'format': 'json'
        }

        resp = session.get(api_url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        pages = data.get('query', {}).get('pages', {})
        for page_id, page_data in pages.items():
            if page_id != '-1':
                original = page_data.get('original', {})
                if original.get('source'):
                    # Return the filename from the URL
                    img_url = original['source']
                    # Extract filename from URL
                    filename_match = re.search(r'/([^/]+)$', img_url)
                    if filename_match:
                        return unquote(filename_match.group(1))
    except Exception as e:
        print(f"  Wikipedia error: {e}")

    return None


def get_commons_thumbnail_url(filename, width=200):
    """Convert a Wikimedia Commons filename to a thumbnail URL."""
    if not filename:
        return None

    # Clean filename
    filename = filename.replace(' ', '_')

    # Use the Wikimedia thumbnail service
    # Format: https://commons.wikimedia.org/wiki/Special:FilePath/{filename}?width={width}
    url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{quote(filename)}?width={width}"
    return url


def download_image(url, output_path):
    """Download an image from URL to local path."""
    try:
        resp = session.get(url, timeout=30, stream=True)
        resp.raise_for_status()

        # Check content type
        content_type = resp.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            print(f"  Not an image: {content_type}")
            return False

        # Save the image
        with open(output_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        # Verify file size
        if output_path.stat().st_size < 1000:
            print(f"  Image too small: {output_path.stat().st_size} bytes")
            output_path.unlink()
            return False

        return True
    except Exception as e:
        print(f"  Download error: {e}")
        if output_path.exists():
            output_path.unlink()
        return False


def process_person(person, dry_run=False):
    """Process a single person to fetch their image."""
    person_id = person['id']
    name = person.get('name', 'Unknown')

    print(f"\nProcessing {person_id}: {name}")

    # Check if already has image_url
    if person.get('image_url'):
        print(f"  Already has image: {person['image_url']}")
        return 'already_has'

    # Check if image already exists
    image_path = IMAGES_DIR / f"{person_id}.jpg"
    if image_path.exists():
        print(f"  Image file already exists")
        # Update YAML if needed
        if not dry_run:
            person['image_url'] = f"/images/persons/{person_id}.jpg"
            save_yaml(person['_file'], {k: v for k, v in person.items() if k != '_file'})
        return 'existing_file'

    # Try Wikidata first
    image_filename = None
    wikidata_id = person.get('wikidata_id')

    if wikidata_id:
        print(f"  Trying Wikidata: {wikidata_id}")
        image_filename = get_wikidata_image(wikidata_id)
        if image_filename:
            print(f"  Found via Wikidata: {image_filename[:50]}...")

    # Fallback to Wikipedia
    if not image_filename:
        wikipedia_url = person.get('wikipedia_url')
        if wikipedia_url:
            print(f"  Trying Wikipedia: {wikipedia_url}")
            image_filename = get_wikipedia_image(wikipedia_url)
            if image_filename:
                print(f"  Found via Wikipedia: {image_filename[:50]}...")

    if not image_filename:
        print(f"  No image found")
        return 'no_image'

    # Get thumbnail URL
    thumbnail_url = get_commons_thumbnail_url(image_filename, width=200)
    print(f"  Thumbnail URL: {thumbnail_url[:80]}...")

    if dry_run:
        print(f"  [DRY RUN] Would download to {image_path}")
        return 'would_download'

    # Download image
    if download_image(thumbnail_url, image_path):
        print(f"  Downloaded to {image_path}")

        # Update YAML file
        person_data = {k: v for k, v in person.items() if k != '_file'}
        person_data['image_url'] = f"/images/persons/{person_id}.jpg"
        save_yaml(person['_file'], person_data)
        print(f"  Updated YAML file")

        return 'success'
    else:
        return 'download_failed'


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Fetch portrait images for main people')
    parser.add_argument('--dry-run', action='store_true', help='Do not download or modify files')
    parser.add_argument('--limit', type=int, help='Process only N persons')
    parser.add_argument('--reset', action='store_true', help='Reset progress and start fresh')
    args = parser.parse_args()

    # Load progress
    if args.reset and PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()

    progress = load_progress()
    processed_ids = set(progress.get('processed', []))

    # Get main persons
    persons = get_main_persons()
    print(f"\nTotal main persons: {len(persons)}")
    print(f"Already processed: {len(processed_ids)}")

    # Filter to unprocessed
    persons_to_process = [p for p in persons if p['id'] not in processed_ids]
    print(f"Remaining to process: {len(persons_to_process)}")

    if args.limit:
        persons_to_process = persons_to_process[:args.limit]
        print(f"Limited to: {args.limit}")

    # Process each person
    stats = {'success': 0, 'no_image': 0, 'failed': 0, 'already_has': 0, 'existing_file': 0}

    for i, person in enumerate(persons_to_process):
        result = process_person(person, dry_run=args.dry_run)

        if result in stats:
            stats[result] += 1

        # Update progress
        if not args.dry_run:
            progress['processed'].append(person['id'])
            if result == 'success':
                progress['success'].append(person['id'])
            elif result in ('no_image', 'download_failed'):
                progress['failed'].append({'id': person['id'], 'reason': result})

            # Save progress every 10 persons
            if (i + 1) % 10 == 0:
                save_progress(progress)
                print(f"\n=== Progress saved ({i + 1}/{len(persons_to_process)}) ===")

        # Rate limiting
        time.sleep(0.5)

    # Final save
    if not args.dry_run:
        save_progress(progress)

    # Print summary
    print(f"\n=== Summary ===")
    print(f"Success: {stats.get('success', 0)}")
    print(f"Already had image: {stats.get('already_has', 0)}")
    print(f"Existing file: {stats.get('existing_file', 0)}")
    print(f"No image found: {stats.get('no_image', 0)}")
    print(f"Download failed: {stats.get('failed', 0)}")


if __name__ == '__main__':
    main()
