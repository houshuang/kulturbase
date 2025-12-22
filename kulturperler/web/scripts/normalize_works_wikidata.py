#!/usr/bin/env python3
"""
Normalize concert works using Wikidata.

For each concert work:
1. Use Gemini to extract structured info (composer, title, opus, key)
2. Search Wikidata for the work
3. Store wikidata_id, wikipedia_url, and summary
4. Also enrich composers with Wikidata links

Batch processing for efficiency.
"""

import yaml
import json
import re
import os
import requests
import time
from pathlib import Path
from urllib.parse import quote
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / 'data'
GEMINI_KEY = os.getenv('GEMINI_KEY')
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"

# Rate limiting
WIKIDATA_DELAY = 0.1  # seconds between Wikidata requests


def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_yaml(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def call_gemini(prompt, retries=3):
    """Call Gemini API with retries."""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1}
    }

    for attempt in range(retries):
        try:
            r = requests.post(GEMINI_URL, json=payload, timeout=60)
            if r.status_code == 200:
                data = r.json()
                return data['candidates'][0]['content']['parts'][0]['text']
            elif r.status_code == 429:
                time.sleep(2 ** attempt)
                continue
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
                continue
            print(f"  Gemini error: {e}")
    return None


def search_wikidata(query, language='en'):
    """Search Wikidata for an entity."""
    url = "https://www.wikidata.org/w/api.php"
    params = {
        'action': 'wbsearchentities',
        'search': query,
        'language': language,
        'format': 'json',
        'limit': 5,
    }
    headers = {'User-Agent': 'Kulturperler/1.0'}

    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return data.get('search', [])
    except Exception as e:
        pass
    return []


def get_wikidata_entity(qid):
    """Get full Wikidata entity data."""
    url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
    headers = {'User-Agent': 'Kulturperler/1.0'}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return data.get('entities', {}).get(qid)
    except Exception:
        pass
    return None


def get_wikipedia_summary(title, lang='en'):
    """Get Wikipedia summary for a title."""
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(title)}"
    headers = {'User-Agent': 'Kulturperler/1.0'}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return {
                'extract': data.get('extract', ''),
                'url': data.get('content_urls', {}).get('desktop', {}).get('page'),
            }
    except Exception:
        pass
    return None


def extract_wikipedia_title_from_wikidata(entity, lang='en'):
    """Extract Wikipedia article title from Wikidata entity."""
    sitelinks = entity.get('sitelinks', {})
    wiki_key = f"{lang}wiki"
    if wiki_key in sitelinks:
        return sitelinks[wiki_key].get('title')
    # Try Norwegian
    if 'nowiki' in sitelinks:
        return sitelinks['nowiki'].get('title')
    return None


def get_label(entity, lang='en'):
    """Get label from Wikidata entity."""
    labels = entity.get('labels', {})
    if lang in labels:
        return labels[lang].get('value')
    if 'en' in labels:
        return labels['en'].get('value')
    if 'no' in labels:
        return labels['no'].get('value')
    return None


def get_description(entity, lang='en'):
    """Get description from Wikidata entity."""
    descriptions = entity.get('descriptions', {})
    if lang in descriptions:
        return descriptions[lang].get('value')
    if 'en' in descriptions:
        return descriptions['en'].get('value')
    return None


def parse_works_batch(works_batch):
    """Use Gemini to parse a batch of work titles."""
    works_text = "\n".join([
        f"{i+1}. [{w['id']}] \"{w['title']}\" (composer_id: {w.get('composer_id')})"
        for i, w in enumerate(works_batch)
    ])

    prompt = f"""Parse these classical music work titles and extract structured information.

Works:
{works_text}

For each work, extract:
- id: the work ID in brackets
- composer: full composer name (e.g., "Ludwig van Beethoven", "Wolfgang Amadeus Mozart")
- work_title: canonical work title without composer name (e.g., "Symphony No. 5 in C minor", "Piano Concerto No. 21")
- opus: opus or catalog number if present (e.g., "Op. 67", "K. 467", "BWV 1048")
- key: musical key if mentioned (e.g., "C minor", "D major")

Return ONLY a JSON array like:
[
  {{"id": 123, "composer": "Ludwig van Beethoven", "work_title": "Symphony No. 5", "opus": "Op. 67", "key": "C minor"}},
  ...
]

If composer is unclear or title is just a composer name, set work_title to null.
If a field is not present, use null."""

    response = call_gemini(prompt)
    if not response:
        return []

    # Parse JSON from response
    try:
        # Find JSON array in response
        match = re.search(r'\[[\s\S]*\]', response)
        if match:
            return json.loads(match.group())
    except json.JSONDecodeError:
        pass
    return []


def find_work_on_wikidata(parsed_work, composer_qid=None):
    """Search Wikidata for a musical work."""
    composer = parsed_work.get('composer', '')
    title = parsed_work.get('work_title', '')
    opus = parsed_work.get('opus', '')

    if not title:
        return None

    # Build search query
    queries = []

    # Try composer + title + opus
    if composer and opus:
        queries.append(f"{composer} {title} {opus}")
    if composer:
        queries.append(f"{composer} {title}")
    queries.append(title)

    for query in queries:
        results = search_wikidata(query)
        time.sleep(WIKIDATA_DELAY)

        for result in results:
            qid = result.get('id')
            desc = result.get('description', '').lower()

            # Check if it's a musical composition
            if any(x in desc for x in ['composition', 'symphony', 'concerto', 'opera', 'sonata', 'quartet', 'music', 'piece', 'work']):
                return {
                    'qid': qid,
                    'label': result.get('label'),
                    'description': result.get('description'),
                }

    return None


def find_composer_on_wikidata(name):
    """Search Wikidata for a composer."""
    results = search_wikidata(f"{name} composer")
    time.sleep(WIKIDATA_DELAY)

    for result in results:
        desc = result.get('description', '').lower()
        if any(x in desc for x in ['composer', 'musician', 'pianist', 'conductor']):
            return {
                'qid': result.get('id'),
                'label': result.get('label'),
                'description': result.get('description'),
            }

    # Try without "composer" suffix
    results = search_wikidata(name)
    time.sleep(WIKIDATA_DELAY)

    for result in results:
        desc = result.get('description', '').lower()
        if any(x in desc for x in ['composer', 'musician']):
            return {
                'qid': result.get('id'),
                'label': result.get('label'),
                'description': result.get('description'),
            }

    return None


def enrich_composer(person_file):
    """Enrich a composer with Wikidata info."""
    person = load_yaml(person_file)
    if not person:
        return False

    # Skip if already has wikidata_id
    if person.get('wikidata_id'):
        return False

    name = person.get('name', '')
    if not name:
        return False

    # Search Wikidata
    result = find_composer_on_wikidata(name)
    if not result:
        return False

    qid = result['qid']

    # Get full entity data
    entity = get_wikidata_entity(qid)
    if not entity:
        return False

    # Update person data
    person['wikidata_id'] = qid

    # Get Wikipedia link and summary if not already present
    if not person.get('wikipedia_url'):
        wiki_title = extract_wikipedia_title_from_wikidata(entity, 'no')
        if wiki_title:
            wiki_data = get_wikipedia_summary(wiki_title, 'no')
            if wiki_data and wiki_data.get('url'):
                person['wikipedia_url'] = wiki_data['url']
        else:
            wiki_title = extract_wikipedia_title_from_wikidata(entity, 'en')
            if wiki_title:
                wiki_data = get_wikipedia_summary(wiki_title, 'en')
                if wiki_data and wiki_data.get('url'):
                    person['wikipedia_url'] = wiki_data['url']

    save_yaml(person_file, person)
    return True


def main():
    print("Normalizing concert works with Wikidata...")

    if not GEMINI_KEY:
        print("Error: GEMINI_KEY not found in .env")
        return

    # Load all concert works
    concert_works = []
    for f in sorted((DATA_DIR / 'plays').glob('*.yaml')):
        w = load_yaml(f)
        if w and w.get('category') == 'konsert':
            concert_works.append({
                'id': w['id'],
                'title': w.get('title', ''),
                'composer_id': w.get('composer_id'),
                'file': f,
                'data': w,
            })

    print(f"Found {len(concert_works)} concert works")

    # Process in batches
    batch_size = 15
    stats = {
        'works_processed': 0,
        'works_enriched': 0,
        'wikidata_found': 0,
        'wikipedia_added': 0,
    }

    for i in range(0, len(concert_works), batch_size):
        batch = concert_works[i:i+batch_size]
        print(f"\nProcessing batch {i//batch_size + 1}/{(len(concert_works) + batch_size - 1)//batch_size}...")

        # Parse batch with Gemini
        parsed = parse_works_batch(batch)

        if not parsed:
            print("  Failed to parse batch")
            continue

        # Match parsed results back to works
        parsed_by_id = {p['id']: p for p in parsed if p.get('id')}

        for work in batch:
            work_id = work['id']
            parsed_work = parsed_by_id.get(work_id, {})

            if not parsed_work.get('work_title'):
                continue

            stats['works_processed'] += 1

            # Search Wikidata for the work
            wikidata_result = find_work_on_wikidata(parsed_work)

            if wikidata_result:
                stats['wikidata_found'] += 1
                qid = wikidata_result['qid']

                # Get full entity
                entity = get_wikidata_entity(qid)
                if entity:
                    # Update work data
                    work_data = work['data']
                    work_data['wikidata_id'] = qid

                    # Use canonical title from Wikidata
                    canonical_title = get_label(entity, 'en') or get_label(entity, 'no')
                    if canonical_title:
                        work_data['title'] = canonical_title

                    # Get Wikipedia summary
                    wiki_title = extract_wikipedia_title_from_wikidata(entity, 'en')
                    if wiki_title:
                        wiki_data = get_wikipedia_summary(wiki_title, 'en')
                        if wiki_data:
                            if wiki_data.get('url'):
                                work_data['wikipedia_url'] = wiki_data['url']
                                stats['wikipedia_added'] += 1
                            if wiki_data.get('extract'):
                                # Truncate to 2-3 sentences
                                extract = wiki_data['extract']
                                sentences = extract.split('. ')
                                work_data['synopsis'] = '. '.join(sentences[:3]) + ('.' if len(sentences) > 3 else '')

                    save_yaml(work['file'], work_data)
                    stats['works_enriched'] += 1
                    print(f"  [{work_id}] {work_data['title'][:50]} -> {qid}")

        # Rate limiting
        time.sleep(0.5)

    print(f"\n\nWork normalization results:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Now enrich composers
    print("\n\nEnriching composers with Wikidata...")

    # Get all composer IDs referenced by works
    composer_ids = set()
    for f in (DATA_DIR / 'plays').glob('*.yaml'):
        w = load_yaml(f)
        if w and w.get('composer_id'):
            composer_ids.add(w['composer_id'])

    print(f"Found {len(composer_ids)} composers to check")

    composers_enriched = 0
    for i, cid in enumerate(sorted(composer_ids)):
        if i % 20 == 0:
            print(f"  Processing composer {i+1}/{len(composer_ids)}...")

        person_file = DATA_DIR / 'persons' / f'{cid}.yaml'
        if person_file.exists():
            if enrich_composer(person_file):
                composers_enriched += 1

        time.sleep(WIKIDATA_DELAY)

    print(f"\nComposer enrichment results:")
    print(f"  Composers enriched: {composers_enriched}")


if __name__ == '__main__':
    main()
