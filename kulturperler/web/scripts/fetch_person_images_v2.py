#!/usr/bin/env python3
"""
Enhanced image fetcher that uses multiple strategies:
1. Wikidata API (if wikidata_id exists)
2. Wikipedia pageimages API (if wikipedia_url exists)
3. Wikidata SPARQL search by name (finds wikidata_id by name)
4. Gemini with Google Search grounding (last resort for famous people)

Usage:
    python3 scripts/fetch_person_images_v2.py [--dry-run] [--limit N] [--retry-failed]
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
from dotenv import load_dotenv

load_dotenv()

# Directories
DATA_DIR = Path('data')
PERSONS_DIR = DATA_DIR / 'persons'
IMAGES_DIR = Path('static/images/persons')
PROGRESS_FILE = Path('/tmp/person_images_v2_progress.json')

GEMINI_KEY = os.getenv('GEMINI_KEY')

# Ensure images directory exists
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Session for HTTP requests
session = requests.Session()
session.headers.update({
    'User-Agent': 'KulturbaseBot/1.0 (https://kulturbase.no; contact@kulturbase.no)'
})


def load_progress():
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {'processed': [], 'failed': [], 'success': [], 'updated_wikidata': []}


def save_progress(progress):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)


def save_yaml(path, data):
    with open(path, 'w') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def get_persons_without_images():
    """Get persons who are playwrights/composers but have no image."""
    # Find creator IDs
    playwright_ids = set()
    composer_ids = set()

    for work_file in (DATA_DIR / 'plays').glob('*.yaml'):
        try:
            work = load_yaml(work_file)
            if work.get('playwright_id'):
                playwright_ids.add(work['playwright_id'])
            if work.get('composer_id'):
                composer_ids.add(work['composer_id'])
        except:
            pass

    main_ids = playwright_ids | composer_ids

    # Load persons without images
    persons = []
    for person_file in PERSONS_DIR.glob('*.yaml'):
        try:
            person = load_yaml(person_file)
            if person.get('id') in main_ids and not person.get('image_url'):
                person['_file'] = person_file
                persons.append(person)
        except:
            pass

    persons.sort(key=lambda p: p['id'])
    return persons


def search_wikidata_by_name(name):
    """Search Wikidata for a person by name and return their Q-ID."""
    # Clean name
    search_name = name.strip()

    # Try SPARQL search for humans with this name
    sparql_url = "https://query.wikidata.org/sparql"
    query = f"""
    SELECT ?item ?itemLabel WHERE {{
      ?item wdt:P31 wd:Q5 .  # instance of human
      ?item rdfs:label "{search_name}"@en .
    }} LIMIT 5
    """

    try:
        resp = session.get(sparql_url, params={'query': query, 'format': 'json'}, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get('results', {}).get('bindings', [])
            if results:
                uri = results[0]['item']['value']
                qid = uri.split('/')[-1]
                return qid
    except Exception as e:
        pass

    # Try wbsearchentities API
    api_url = "https://www.wikidata.org/w/api.php"
    params = {
        'action': 'wbsearchentities',
        'search': search_name,
        'language': 'en',
        'type': 'item',
        'limit': 5,
        'format': 'json'
    }

    try:
        resp = session.get(api_url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for result in data.get('search', []):
                # Check if it's a person (has P31=Q5)
                qid = result['id']
                desc = result.get('description', '').lower()
                if any(x in desc for x in ['playwright', 'writer', 'author', 'composer', 'dramatist', 'poet', 'novelist']):
                    return qid
            # If no clear match, return first result
            if data.get('search'):
                return data['search'][0]['id']
    except:
        pass

    return None


def get_wikidata_image(wikidata_id):
    """Fetch image filename from Wikidata P18 property."""
    if not wikidata_id:
        return None

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

        if 'P18' in claims:
            image_value = claims['P18'][0].get('mainsnak', {}).get('datavalue', {}).get('value')
            if image_value:
                return image_value
    except:
        pass

    return None


def get_wikipedia_image(wikipedia_url):
    """Try to extract main image from Wikipedia page."""
    if not wikipedia_url:
        return None

    try:
        match = re.search(r'(\w+)\.wikipedia\.org/wiki/(.+)$', wikipedia_url)
        if not match:
            return None

        lang = match.group(1)
        page_title = unquote(match.group(2))

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
                    img_url = original['source']
                    filename_match = re.search(r'/([^/]+)$', img_url)
                    if filename_match:
                        return unquote(filename_match.group(1))
    except:
        pass

    return None


def search_with_gemini(name, birth_year=None, death_year=None):
    """Use Gemini with Google Search to find a Wikipedia/Wikimedia image URL."""
    if not GEMINI_KEY:
        return None

    # Build search context
    context = f"{name}"
    if birth_year and death_year:
        context += f" ({birth_year}-{death_year})"
    elif birth_year:
        context += f" (born {birth_year})"

    prompt = f"""Find the Wikimedia Commons portrait image filename for {context}.

Search for their Wikipedia page and find the main portrait/photo image.

Return ONLY the Wikimedia Commons filename (e.g., "Portrait_of_Person.jpg") or "NONE" if no portrait exists.
Do not include any other text."""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 200}
    }

    try:
        resp = requests.post(url, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            text = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            text = text.strip()

            if text and text.upper() != 'NONE' and len(text) < 300:
                # Clean up the filename
                # Remove markdown formatting if present
                text = re.sub(r'[`*]', '', text)
                # Extract just the filename if there's extra text
                match = re.search(r'([A-Za-z0-9_\-\.%\(\)]+\.(jpg|jpeg|png|gif|svg|JPG|PNG))', text, re.IGNORECASE)
                if match:
                    return match.group(1).replace(' ', '_')
    except Exception as e:
        print(f"    Gemini error: {e}")

    return None


def get_commons_thumbnail_url(filename, width=200):
    """Convert a Wikimedia Commons filename to a thumbnail URL."""
    if not filename:
        return None
    filename = filename.replace(' ', '_')
    url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{quote(filename)}?width={width}"
    return url


def download_image(url, output_path):
    """Download an image from URL to local path."""
    try:
        resp = session.get(url, timeout=30, stream=True)
        resp.raise_for_status()

        content_type = resp.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            return False

        with open(output_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        if output_path.stat().st_size < 1000:
            output_path.unlink()
            return False

        return True
    except Exception as e:
        if output_path.exists():
            output_path.unlink()
        return False


def process_person(person, dry_run=False, use_gemini=True):
    """Process a single person using multiple strategies."""
    person_id = person['id']
    name = person.get('name', 'Unknown')

    print(f"\nProcessing {person_id}: {name}")

    image_path = IMAGES_DIR / f"{person_id}.jpg"
    if image_path.exists():
        print(f"  Image already exists")
        return 'existing', None

    image_filename = None
    found_wikidata_id = None

    # Strategy 1: Try existing Wikidata ID
    wikidata_id = person.get('wikidata_id')
    if wikidata_id:
        print(f"  Strategy 1: Wikidata ID {wikidata_id}")
        image_filename = get_wikidata_image(wikidata_id)
        if image_filename:
            print(f"    Found: {image_filename[:50]}...")

    # Strategy 2: Try Wikipedia URL
    if not image_filename:
        wikipedia_url = person.get('wikipedia_url')
        if wikipedia_url:
            print(f"  Strategy 2: Wikipedia URL")
            image_filename = get_wikipedia_image(wikipedia_url)
            if image_filename:
                print(f"    Found: {image_filename[:50]}...")

    # Strategy 3: Search Wikidata by name
    if not image_filename:
        print(f"  Strategy 3: Wikidata name search")
        found_wikidata_id = search_wikidata_by_name(name)
        if found_wikidata_id:
            print(f"    Found Wikidata ID: {found_wikidata_id}")
            image_filename = get_wikidata_image(found_wikidata_id)
            if image_filename:
                print(f"    Found image: {image_filename[:50]}...")

    # Strategy 4: Use Gemini with Google Search
    if not image_filename and use_gemini:
        print(f"  Strategy 4: Gemini search")
        image_filename = search_with_gemini(name, person.get('birth_year'), person.get('death_year'))
        if image_filename:
            print(f"    Found: {image_filename[:50]}...")

    if not image_filename:
        print(f"  No image found")
        return 'no_image', found_wikidata_id

    # Download image
    thumbnail_url = get_commons_thumbnail_url(image_filename, width=200)
    print(f"  Downloading from: {thumbnail_url[:60]}...")

    if dry_run:
        print(f"  [DRY RUN] Would download")
        return 'would_download', found_wikidata_id

    if download_image(thumbnail_url, image_path):
        print(f"  Downloaded to {image_path}")

        # Update YAML file
        person_data = {k: v for k, v in person.items() if k != '_file'}
        person_data['image_url'] = f"/images/persons/{person_id}.jpg"

        # Also save the wikidata_id if we found one
        if found_wikidata_id and not person_data.get('wikidata_id'):
            person_data['wikidata_id'] = found_wikidata_id

        save_yaml(person['_file'], person_data)
        print(f"  Updated YAML")

        return 'success', found_wikidata_id
    else:
        return 'download_failed', found_wikidata_id


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Enhanced image fetcher for persons')
    parser.add_argument('--dry-run', action='store_true', help='Do not download or modify files')
    parser.add_argument('--limit', type=int, help='Process only N persons')
    parser.add_argument('--reset', action='store_true', help='Reset progress')
    parser.add_argument('--no-gemini', action='store_true', help='Disable Gemini search')
    args = parser.parse_args()

    if args.reset and PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()

    progress = load_progress()
    processed_ids = set(progress.get('processed', []))

    persons = get_persons_without_images()
    print(f"Persons without images: {len(persons)}")
    print(f"Already processed in v2: {len(processed_ids)}")

    persons_to_process = [p for p in persons if p['id'] not in processed_ids]
    print(f"Remaining: {len(persons_to_process)}")

    if args.limit:
        persons_to_process = persons_to_process[:args.limit]
        print(f"Limited to: {args.limit}")

    stats = {'success': 0, 'no_image': 0, 'download_failed': 0, 'existing': 0}

    for i, person in enumerate(persons_to_process):
        result, found_wikidata = process_person(person, dry_run=args.dry_run, use_gemini=not args.no_gemini)

        if result in stats:
            stats[result] += 1

        if not args.dry_run:
            progress['processed'].append(person['id'])
            if result == 'success':
                progress['success'].append(person['id'])
                if found_wikidata:
                    progress['updated_wikidata'].append({'id': person['id'], 'wikidata_id': found_wikidata})
            elif result in ('no_image', 'download_failed'):
                progress['failed'].append({'id': person['id'], 'reason': result})

            if (i + 1) % 10 == 0:
                save_progress(progress)
                print(f"\n=== Progress saved ({i + 1}/{len(persons_to_process)}) ===")

        time.sleep(0.3)

    if not args.dry_run:
        save_progress(progress)

    print(f"\n=== Summary ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == '__main__':
    main()
