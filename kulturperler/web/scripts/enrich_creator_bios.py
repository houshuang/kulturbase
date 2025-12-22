#!/usr/bin/env python3
"""
Enrich creator bios from Wikipedia using Gemini 3 Flash.

For each creator (composer, playwright, librettist) without a bio:
1. Search Norwegian Wikipedia first, then English
2. Use Gemini 3 Flash to generate a 4-5 sentence bio in Norwegian
3. Extract birth/death years
4. Update YAML files
"""

import yaml
import requests
import json
import time
import os
import re
from pathlib import Path
from urllib.parse import quote
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / 'data'
GEMINI_KEY = os.getenv('GEMINI_KEY')
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={GEMINI_KEY}"


def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_yaml(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def get_creator_ids():
    """Get all person IDs that are creators (playwright, composer, etc.)."""
    creator_ids = set()

    # From works
    for f in (DATA_DIR / 'plays').glob('*.yaml'):
        w = load_yaml(f)
        if w:
            for field in ['playwright_id', 'composer_id', 'librettist_id', 'creator_id']:
                if w.get(field):
                    creator_ids.add(w[field])

    # From nrk_about_programs
    for f in (DATA_DIR / 'nrk_about_programs').glob('*.yaml'):
        p = load_yaml(f)
        if p and p.get('person_id'):
            creator_ids.add(p['person_id'])

    return creator_ids


def get_creators_without_bio():
    """Get all creators that need bios."""
    creator_ids = get_creator_ids()
    creators = []

    for f in (DATA_DIR / 'persons').glob('*.yaml'):
        p = load_yaml(f)
        if not p or p.get('id') not in creator_ids:
            continue
        if p.get('bio'):
            continue  # Already has bio

        name = p.get('name', '')
        # Skip combined entries (will handle separately)
        if ', ' in name or ' and ' in name.lower() or '; ' in name or ' & ' in name:
            continue

        creators.append({
            'id': p['id'],
            'name': name,
            'file': f,
            'birth_year': p.get('birth_year'),
            'death_year': p.get('death_year'),
            'wikipedia_url': p.get('wikipedia_url'),
        })

    return creators


def fetch_wikipedia_content(name, lang='no'):
    """Fetch Wikipedia page summary."""
    # Try exact name first
    encoded_name = quote(name.replace(' ', '_'))
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded_name}"

    headers = {
        'User-Agent': 'Kulturperler/1.0 (https://github.com/kulturperler; contact@example.com)'
    }

    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return {
                'title': data.get('title'),
                'extract': data.get('extract', ''),
                'url': data.get('content_urls', {}).get('desktop', {}).get('page'),
                'lang': lang
            }
    except Exception as e:
        pass

    return None


def call_gemini(prompt):
    """Call Gemini 3 Flash API."""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1}
    }

    try:
        r = requests.post(GEMINI_URL, json=payload, timeout=30)
        if r.status_code == 200:
            data = r.json()
            text = data['candidates'][0]['content']['parts'][0]['text']
            return text
    except Exception as e:
        print(f"  Gemini error: {e}")

    return None


def parse_gemini_response(response):
    """Parse JSON from Gemini response."""
    if not response:
        return None

    # Try to extract JSON from response
    try:
        # Look for JSON block
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        pass

    return None


def is_musician_or_creator(extract, name):
    """Use Gemini to verify if the Wikipedia article is about a musician/composer/creator."""
    prompt = f"""Is this Wikipedia article about a musician, composer, playwright, songwriter, conductor, or performing artist?

Article about "{name}":
"{extract[:1000]}"

Answer with ONLY "yes" or "no"."""

    response = call_gemini(prompt)
    if response:
        return 'yes' in response.lower()
    return False


def try_wikipedia_search(name, lang='no', include_profession=False):
    """Search Wikipedia for a name and return best match."""
    search_url = f"https://{lang}.wikipedia.org/w/api.php"
    headers = {
        'User-Agent': 'Kulturperler/1.0 (https://github.com/kulturperler; contact@example.com)'
    }

    # Nobility particles to skip
    particles = {'von', 'van', 'de', 'du', 'der', 'la', 'le', 'di'}

    # Try multiple search queries - prioritize queries without particles
    search_queries = []
    parts = name.split()

    # First: First + last name without particles (most likely to find the right person)
    if len(parts) > 1:
        non_particle_parts = [p for p in parts if p.lower() not in particles]
        if len(non_particle_parts) >= 2:
            search_queries.append(f"{non_particle_parts[0]} {non_particle_parts[-1]}")

    # Second: Full name as-is
    search_queries.append(name)

    # Third: Last name only (helps with common last names)
    if len(parts) > 1:
        search_queries.append(parts[-1])

    all_results = []
    for query in search_queries:
        params = {
            'action': 'opensearch',
            'search': query,
            'limit': 5,
            'format': 'json'
        }

        try:
            r = requests.get(search_url, headers=headers, params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if len(data) >= 2 and data[1]:
                    # Prioritize results that contain the original name parts
                    for result in data[1]:
                        if result not in all_results:
                            all_results.append(result)
        except Exception:
            pass

    return all_results[:10]


def enrich_creator(creator):
    """Enrich a single creator with bio from Wikipedia."""
    name = creator['name']
    print(f"Processing [{creator['id']}] {name}...")

    wiki = None

    # Try different name variations and languages
    name_variations = [name]

    # Add common spelling variations
    if 'Herrmann' in name:
        name_variations.append(name.replace('Herrmann', 'Hermann'))
    if 'Tsjajkovskij' in name or 'Tchaikovsky' in name:
        name_variations.extend(['Pyotr Ilyich Tchaikovsky', 'Peter Tsjajkovskij'])

    for lang in ['no', 'en']:
        for name_var in name_variations:
            wiki = fetch_wikipedia_content(name_var, lang)
            if wiki and wiki.get('extract'):
                # Verify this is about a musician/creator
                if is_musician_or_creator(wiki['extract'], name):
                    print(f"  Found: {wiki['title']} ({lang})")
                    break
                else:
                    print(f"  Skipping non-creator match: {wiki['title']}")
                    wiki = None
        if wiki:
            break

    # If not found by exact name, try search
    if not wiki:
        for lang in ['no', 'en']:
            results = try_wikipedia_search(name, lang)
            for result_title in results[:3]:
                wiki = fetch_wikipedia_content(result_title, lang)
                if wiki and wiki.get('extract'):
                    if is_musician_or_creator(wiki['extract'], name):
                        print(f"  Found via search: {wiki['title']} ({lang})")
                        break
                    else:
                        wiki = None
            if wiki:
                break

    if not wiki or not wiki.get('extract'):
        print(f"  No Wikipedia found")
        return None

    # Use Gemini to generate bio
    wiki_extract = wiki['extract'][:2000]  # Limit context

    prompt = f"""Based on this Wikipedia article about the composer/musician {name}:

"{wiki_extract}"

Provide the following in JSON format:
1. "bio": A biography in Norwegian (4-5 sentences). If the text is in English, translate it. Focus on their musical/creative work.
2. "birth_year": Birth year as a number (or null if unknown)
3. "death_year": Death year as a number (or null if still alive or unknown)

Return ONLY valid JSON like: {{"bio": "...", "birth_year": 1850, "death_year": 1920}}"""

    response = call_gemini(prompt)
    result = parse_gemini_response(response)

    if not result or not result.get('bio'):
        print(f"  Failed to parse Gemini response")
        return None

    return {
        'bio': result['bio'],
        'birth_year': result.get('birth_year'),
        'death_year': result.get('death_year'),
        'wikipedia_url': wiki.get('url'),
        'lang': wiki.get('lang'),
    }


def update_creator(creator, enrichment):
    """Update creator YAML file with enrichment data."""
    filepath = creator['file']
    data = load_yaml(filepath)

    # Update fields
    if enrichment.get('bio'):
        data['bio'] = enrichment['bio']

    if enrichment.get('birth_year') and not data.get('birth_year'):
        data['birth_year'] = enrichment['birth_year']

    if enrichment.get('death_year') and not data.get('death_year'):
        data['death_year'] = enrichment['death_year']

    if enrichment.get('wikipedia_url') and not data.get('wikipedia_url'):
        data['wikipedia_url'] = enrichment['wikipedia_url']

    save_yaml(filepath, data)
    print(f"  Updated {filepath.name}")


def main():
    print("Enriching creator bios from Wikipedia...")

    if not GEMINI_KEY:
        print("Error: GEMINI_KEY not found in .env")
        return

    creators = get_creators_without_bio()
    print(f"Found {len(creators)} creators without bios")

    # Process in batches to avoid rate limiting
    updated = 0
    failed = 0

    for i, creator in enumerate(creators):
        print(f"\n[{i+1}/{len(creators)}]", end=" ")

        enrichment = enrich_creator(creator)

        if enrichment:
            update_creator(creator, enrichment)
            updated += 1
        else:
            failed += 1

        # Rate limiting
        time.sleep(0.5)

    print(f"\n\nResults:")
    print(f"  Updated: {updated}")
    print(f"  Failed: {failed}")


if __name__ == '__main__':
    main()
