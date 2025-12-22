#!/usr/bin/env python3
"""
Normalize concert works using Wikidata.

For each concert work:
1. Use Gemini to extract structured info (composer, title, opus, key)
2. Search Wikidata for the SPECIFIC work (not genre)
3. Verify composer matches (P86 property)
4. Store wikidata_id, wikipedia_url, and summary

Key improvements:
- Always search with composer name
- Verify P86 (composer) property exists (specific works have composers)
- Check P31 (instance of) is NOT a genre
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

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / 'data'
GEMINI_KEY = os.getenv('GEMINI_KEY')
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"

# Wikidata properties
P_INSTANCE_OF = 'P31'
P_COMPOSER = 'P86'

# Wikidata items to REJECT (genres, forms, not specific works)
REJECT_QIDS = {
    'Q188451',     # music genre
    'Q5',          # human
    'Q43229',      # organization
    'Q2088357',    # musical ensemble
    'Q207338',     # string quartet (genre/form)
    'Q633441',     # violin concerto (genre)
    'Q9730',       # symphony (genre)
    'Q5321',       # concerto (genre)
    'Q9734',       # sonata (genre)
    'Q186472',     # piano concerto (genre)
    'Q178401',     # concerto (genre)
    'Q131289',     # trio (genre)
    'Q208569',     # cello concerto (genre)
    'Q215380',     # musical work (too generic)
    'Q2986124',    # Norwegian Radio Orchestra
    'Q1954097',    # triple concerto (genre)
    'Q547833',     # septet (genre)
    'Q208494',     # sextet (genre)
    'Q83270',      # octet (genre)
    'Q207628',     # quintet (genre)
    'Q192072',     # quartet (genre)
    'Q189201',     # duet (genre)
    'Q56816998',   # double concerto (genre)
    'Q241562',     # piano trio (genre)
    'Q842324',     # wind quintet (genre)
    'Q859886',     # brass quintet (genre)
    'Q188447',     # mass (genre)
    'Q131578',     # requiem (genre)
    'Q7366',       # song (genre)
    'Q26443',      # lied (genre)
    'Q2188189',    # étude (genre)
    'Q243090',     # nocturne (genre)
    'Q131686',     # waltz (genre)
    'Q184831',     # minuet (genre)
    'Q243340',     # scherzo (genre)
    'Q189290',     # rondo (genre)
    'Q1344',       # opera (genre)
    'Q2742',       # ballet (genre)
    'Q21198342',   # type of musical work
    'Q1298934',    # musical form
}

# Words in descriptions that indicate a genre/form rather than specific work
GENRE_DESCRIPTION_KEYWORDS = [
    'type of', 'form of', 'genre of', 'kind of',
    'musical form', 'musical genre', 'musical composition form',
    'category of', 'class of', 'style of',
    'chamber music', 'orchestral form',
]

RATE_LIMIT = 0.15


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
    """Search Wikidata for an entity (fallback)."""
    url = "https://www.wikidata.org/w/api.php"
    params = {
        'action': 'wbsearchentities',
        'search': query,
        'language': language,
        'format': 'json',
        'limit': 10,
    }
    headers = {'User-Agent': 'Kulturperler/1.0 (https://kulturperler.no)'}

    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return data.get('search', [])
    except Exception:
        pass
    return []


def search_wikipedia_for_wikidata(query, language='en'):
    """Search Wikipedia and return Wikidata IDs in order of relevance."""
    headers = {'User-Agent': 'Kulturperler/1.0 (https://kulturperler.no)'}

    # Search Wikipedia
    url = f"https://{language}.wikipedia.org/w/api.php"
    params = {
        'action': 'query',
        'list': 'search',
        'srsearch': query,
        'srlimit': 10,
        'format': 'json',
    }

    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        if r.status_code != 200:
            return []
        search_results = r.json().get('query', {}).get('search', [])

        if not search_results:
            return []

        # Keep track of titles in order
        ordered_titles = [s['title'] for s in search_results[:5]]

        # Get Wikidata IDs for these articles
        titles = '|'.join(ordered_titles)
        params = {
            'action': 'query',
            'titles': titles,
            'prop': 'pageprops',
            'ppprop': 'wikibase_item',
            'format': 'json',
        }
        r = requests.get(url, params=params, headers=headers, timeout=10)
        if r.status_code != 200:
            return []

        # Build a map of title -> qid
        pages = r.json().get('query', {}).get('pages', {})
        title_to_qid = {}
        for page in pages.values():
            qid = page.get('pageprops', {}).get('wikibase_item')
            title = page.get('title')
            if qid and title:
                title_to_qid[title] = qid

        # Return results in search order
        results = []
        for title in ordered_titles:
            if title in title_to_qid:
                results.append({
                    'id': title_to_qid[title],
                    'label': title,
                })
        return results
    except Exception:
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


def get_claim_values(entity, prop):
    """Get values for a claim property."""
    claims = entity.get('claims', {})
    if prop not in claims:
        return []

    values = []
    for claim in claims[prop]:
        mainsnak = claim.get('mainsnak', {})
        datavalue = mainsnak.get('datavalue', {})
        if datavalue.get('type') == 'wikibase-entityid':
            values.append(datavalue.get('value', {}).get('id'))
        elif datavalue.get('type') == 'string':
            values.append(datavalue.get('value'))
    return values


def get_description(entity, lang='en'):
    """Get description from Wikidata entity."""
    descriptions = entity.get('descriptions', {})
    if lang in descriptions:
        return descriptions[lang].get('value', '')
    if 'en' in descriptions:
        return descriptions['en'].get('value', '')
    return ''


def is_specific_composition(entity):
    """Check if entity is a specific musical composition (not a genre)."""
    qid = entity.get('id', '')

    # Reject known bad IDs
    if qid in REJECT_QIDS:
        return False

    # Check instance_of - reject if it's a genre
    instance_of = get_claim_values(entity, P_INSTANCE_OF)
    for inst_qid in instance_of:
        if inst_qid in REJECT_QIDS:
            return False

    # Check description for genre keywords
    description = get_description(entity).lower()
    for keyword in GENRE_DESCRIPTION_KEYWORDS:
        if keyword in description:
            return False

    # Must have a composer (P86) to be a specific work
    composers = get_claim_values(entity, P_COMPOSER)
    if not composers:
        return False

    return True


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


def load_composers_cache():
    """Load composers into a cache."""
    cache = {}  # person_id -> {'name': ..., 'wikidata_id': ...}
    for f in (DATA_DIR / 'persons').glob('*.yaml'):
        p = load_yaml(f)
        if p:
            cache[p['id']] = {
                'name': p.get('name', ''),
                'wikidata_id': p.get('wikidata_id'),
            }
    return cache


def parse_works_batch(works_batch, composers_cache):
    """Use Gemini to parse a batch of work titles."""
    works_text = "\n".join([
        f"{i+1}. [{w['id']}] \"{w['title']}\" (composer: {composers_cache.get(w.get('composer_id'), {}).get('name', 'Unknown')})"
        for i, w in enumerate(works_batch)
    ])

    prompt = f"""Parse these classical music works and provide search queries to find them on Wikidata.

Works:
{works_text}

For each work, provide:
- id: the work ID in brackets
- composer_full_name: the full composer name
- canonical_title: the standard title for this specific work
- search_query: a search query to find this SPECIFIC work on Wikidata

IMPORTANT: The search_query must be specific enough to find the EXACT work, not a genre.
- BAD: "Violin Concerto" (finds the genre)
- GOOD: "Sibelius Violin Concerto" or "Bartók Violin Concerto No. 2"
- Include opus numbers when known: "Beethoven Symphony No. 5 Op. 67"

Return ONLY a JSON array:
[
  {{"id": 123, "composer_full_name": "Ludwig van Beethoven", "canonical_title": "Symphony No. 5 in C minor, Op. 67", "search_query": "Beethoven Symphony No. 5 Op. 67"}},
  ...
]

If the title is just a composer name or unclear, set search_query to null."""

    response = call_gemini(prompt)
    if not response:
        return []

    try:
        match = re.search(r'\[[\s\S]*\]', response)
        if match:
            return json.loads(match.group())
    except json.JSONDecodeError:
        pass
    return []


def find_specific_work_on_wikidata(search_query):
    """Search for a specific musical work using Wikipedia then Wikidata."""
    if not search_query:
        return None

    # Try Wikipedia search first (better for full-text queries)
    results = search_wikipedia_for_wikidata(search_query)
    time.sleep(RATE_LIMIT)

    # Fall back to Wikidata search if Wikipedia finds nothing
    if not results:
        results = search_wikidata(search_query)
        time.sleep(RATE_LIMIT)

    for result in results:
        qid = result.get('id')

        # Skip known bad IDs
        if qid in REJECT_QIDS:
            continue

        # Get full entity to verify it's a specific composition
        entity = get_wikidata_entity(qid)
        time.sleep(RATE_LIMIT)

        if not entity:
            continue

        # Must be a specific composition (has composer, not a genre)
        if not is_specific_composition(entity):
            continue

        # Found a valid specific work
        return {
            'qid': qid,
            'entity': entity,
            'label': get_label(entity),
        }

    return None


def find_composer_on_wikidata(name):
    """Search Wikidata for a composer."""
    results = search_wikidata(f"{name} composer")
    time.sleep(RATE_LIMIT)

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
    time.sleep(RATE_LIMIT)

    for result in results:
        desc = result.get('description', '').lower()
        if any(x in desc for x in ['composer', 'musician']):
            return {
                'qid': result.get('id'),
                'label': result.get('label'),
            }

    return None


def enrich_composer(person_file):
    """Enrich a composer with Wikidata info."""
    person = load_yaml(person_file)
    if not person:
        return False

    if person.get('wikidata_id'):
        return False

    name = person.get('name', '')
    if not name:
        return False

    result = find_composer_on_wikidata(name)
    if not result:
        return False

    qid = result['qid']
    entity = get_wikidata_entity(qid)
    if not entity:
        return False

    person['wikidata_id'] = qid

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
    print("Normalizing concert works with Wikidata (v2 - specific works only)...")

    if not GEMINI_KEY:
        print("Error: GEMINI_KEY not found in .env")
        return

    composers_cache = load_composers_cache()
    print(f"Loaded {len(composers_cache)} composers")

    # Load concert works that need processing
    concert_works = []
    for f in sorted((DATA_DIR / 'plays').glob('*.yaml')):
        w = load_yaml(f)
        if w and w.get('category') == 'konsert':
            if w.get('wikidata_id'):
                continue  # Already processed
            concert_works.append({
                'id': w['id'],
                'title': w.get('title', ''),
                'composer_id': w.get('composer_id'),
                'file': f,
                'data': w,
            })

    print(f"Found {len(concert_works)} concert works to process")

    batch_size = 10
    stats = {
        'works_processed': 0,
        'wikidata_found': 0,
        'wikipedia_added': 0,
    }

    for i in range(0, len(concert_works), batch_size):
        batch = concert_works[i:i+batch_size]
        batch_num = i//batch_size + 1
        total_batches = (len(concert_works) + batch_size - 1)//batch_size
        print(f"\nBatch {batch_num}/{total_batches}...")

        parsed = parse_works_batch(batch, composers_cache)

        if not parsed:
            print("  Failed to parse batch")
            continue

        parsed_by_id = {p['id']: p for p in parsed if p.get('id')}

        for work in batch:
            work_id = work['id']
            parsed_info = parsed_by_id.get(work_id, {})
            search_query = parsed_info.get('search_query')

            if not search_query:
                continue

            stats['works_processed'] += 1

            result = find_specific_work_on_wikidata(search_query)

            if result:
                entity = result['entity']
                qid = result['qid']

                work_data = work['data']
                work_data['wikidata_id'] = qid

                # Use canonical title
                canonical_title = get_label(entity, 'en')
                if canonical_title:
                    work_data['title'] = canonical_title

                # Get Wikipedia summary
                wiki_title = extract_wikipedia_title_from_wikidata(entity, 'en')
                if not wiki_title:
                    wiki_title = extract_wikipedia_title_from_wikidata(entity, 'no')

                if wiki_title:
                    lang = 'en' if 'enwiki' in entity.get('sitelinks', {}) else 'no'
                    wiki_data = get_wikipedia_summary(wiki_title, lang)
                    if wiki_data:
                        if wiki_data.get('url'):
                            work_data['wikipedia_url'] = wiki_data['url']
                            stats['wikipedia_added'] += 1
                        if wiki_data.get('extract'):
                            sentences = wiki_data['extract'].split('. ')
                            work_data['synopsis'] = '. '.join(sentences[:3]) + '.'

                save_yaml(work['file'], work_data)
                stats['wikidata_found'] += 1
                print(f"  [{work_id}] {work_data['title'][:50]} -> {qid}")

        time.sleep(0.5)

    print(f"\n\nResults:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Enrich composers
    print("\n\nEnriching composers...")
    composer_ids = set()
    for f in (DATA_DIR / 'plays').glob('*.yaml'):
        w = load_yaml(f)
        if w and w.get('composer_id'):
            composer_ids.add(w['composer_id'])

    print(f"Found {len(composer_ids)} composers")

    composers_enriched = 0
    for i, cid in enumerate(sorted(composer_ids)):
        if i % 20 == 0:
            print(f"  Processing {i+1}/{len(composer_ids)}...")

        person_file = DATA_DIR / 'persons' / f'{cid}.yaml'
        if person_file.exists():
            if enrich_composer(person_file):
                composers_enriched += 1

        time.sleep(RATE_LIMIT)

    print(f"\nComposers enriched: {composers_enriched}")


if __name__ == '__main__':
    main()
