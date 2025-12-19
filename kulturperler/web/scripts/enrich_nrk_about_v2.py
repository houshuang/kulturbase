#!/usr/bin/env python3
"""
Fetch NRK programs about playwrights - comprehensive version.
Fetches broadly and outputs candidates for manual review.
"""

import sqlite3
import requests
import time
import json
import re
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "static" / "kulturperler.db"
CACHE_PATH = Path(__file__).parent.parent / "static" / "nrk_about_cache.json"

def load_cache():
    if CACHE_PATH.exists():
        with open(CACHE_PATH) as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_PATH, 'w') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

def search_nrk(query, page_size=50):
    """Search NRK for programs matching query."""
    url = f"https://psapi.nrk.no/search?q={requests.utils.quote(query)}&pageSize={page_size}"
    try:
        resp = requests.get(url, timeout=30)
        if resp.ok:
            return resp.json()
    except Exception as e:
        print(f"  Error searching for '{query}': {e}")
    return None

def get_program_details(program_id):
    """Get details for a single program."""
    url = f"https://psapi.nrk.no/programs/{program_id}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.ok:
            return resp.json()
    except:
        pass
    return None

def get_series_details(series_id):
    """Get details for a series."""
    url = f"https://psapi.nrk.no/tv/catalog/series/{series_id}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.ok:
            return resp.json()
    except:
        pass
    return None

def extract_duration(data):
    """Extract duration in seconds from API response."""
    duration_str = data.get('duration', '') or data.get('actualDuration', '')
    if not duration_str:
        return 0

    # Parse ISO 8601 duration (e.g., PT1H30M45S)
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?', duration_str)
    if match:
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = float(match.group(3) or 0)
        return int(hours * 3600 + minutes * 60 + seconds)
    return 0

def extract_year(data):
    """Extract year from API response."""
    for field in ['firstAired', 'usageRights.availableFrom', 'productionYear']:
        val = data.get(field, '')
        if val:
            match = re.search(r'(\d{4})', str(val))
            if match:
                return int(match.group(1))
    return None

def extract_image(data):
    """Extract image URL from API response."""
    images = data.get('webImages', []) or data.get('image', {}).get('webImages', [])
    if images:
        # Get largest image
        for img in sorted(images, key=lambda x: x.get('width', 0), reverse=True):
            if 'url' in img:
                return img['url']
            if 'uri' in img:
                return img['uri']
    return None

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all playwrights
    cursor.execute("""
        SELECT DISTINCT p.id, p.name
        FROM persons p
        JOIN plays pl ON p.id = pl.playwright_id
        ORDER BY p.name
    """)
    playwrights = cursor.fetchall()

    print(f"Found {len(playwrights)} playwrights with plays")

    # Get existing programs to avoid duplicates
    cursor.execute("SELECT id FROM nrk_about_programs")
    existing_ids = set(row[0] for row in cursor.fetchall())

    # Get existing episodes to avoid duplicates with actual plays
    cursor.execute("SELECT prf_id FROM episodes")
    episode_ids = set(row[0] for row in cursor.fetchall())

    cache = load_cache()
    all_candidates = []

    for person_id, name in playwrights:
        print(f"\n=== {name} ===")

        # Generate search queries
        queries = [name]

        # Add last name only for common names
        name_parts = name.split()
        if len(name_parts) > 1:
            queries.append(name_parts[-1])  # Last name

        seen_ids = set()
        candidates = []

        for query in queries:
            cache_key = f"search:{query}"
            if cache_key in cache:
                results = cache[cache_key]
            else:
                print(f"  Searching: {query}")
                results = search_nrk(query)
                cache[cache_key] = results
                time.sleep(0.5)

            if not results:
                continue

            hits = results.get('hits', [])
            print(f"    Found {len(hits)} results")

            for hit_wrapper in hits:
                hit = hit_wrapper.get('hit', hit_wrapper)

                prog_id = hit.get('id', '')
                prog_type = hit.get('type', '')
                title = hit.get('title', '')

                if not prog_id or prog_id in seen_ids:
                    continue
                seen_ids.add(prog_id)

                # Skip if already in our database
                if prog_id in existing_ids or prog_id in episode_ids:
                    continue

                # Skip news and radio
                category = hit.get('category', {}).get('displayValue', '').lower()
                if any(x in category for x in ['nyheter', 'radio', 'nrk1', 'nrk2']):
                    continue

                # Get details
                if prog_type == 'serie':
                    details = get_series_details(prog_id)
                    if details:
                        duration = 0
                        # Sum up episode durations
                        for season in details.get('seasons', []):
                            for ep in season.get('episodes', []):
                                duration += extract_duration(ep)

                        desc = details.get('description', '') or details.get('subtitle', '')
                        year = extract_year(details)
                        image = extract_image(details)

                        candidates.append({
                            'id': prog_id,
                            'person_id': person_id,
                            'person_name': name,
                            'title': title,
                            'description': desc,
                            'duration': duration,
                            'year': year,
                            'image_url': image,
                            'program_type': 'serie',
                            'nrk_url': f"https://tv.nrk.no/serie/{prog_id}"
                        })
                else:
                    details = get_program_details(prog_id)
                    if details:
                        desc = details.get('description', '') or details.get('titles', {}).get('subtitle', '')
                        duration = extract_duration(details)
                        year = extract_year(details)
                        image = extract_image(details)

                        # Skip very short programs (< 5 min)
                        if duration > 0 and duration < 300:
                            continue

                        candidates.append({
                            'id': prog_id,
                            'person_id': person_id,
                            'person_name': name,
                            'title': title,
                            'description': desc,
                            'duration': duration,
                            'year': year,
                            'image_url': image,
                            'program_type': 'program',
                            'nrk_url': f"https://tv.nrk.no/program/{prog_id}"
                        })

                time.sleep(0.3)

        # Show candidates for this playwright
        if candidates:
            print(f"\n  Candidates for {name}:")
            for c in candidates:
                dur_str = f"{c['duration']//60}m" if c['duration'] else "?"
                print(f"    [{c['program_type']}] {c['title']} ({dur_str})")
                if c['description']:
                    print(f"      {c['description'][:100]}...")

        all_candidates.extend(candidates)

    save_cache(cache)

    # Save candidates for review
    candidates_path = Path(__file__).parent.parent / "static" / "nrk_candidates.json"
    with open(candidates_path, 'w') as f:
        json.dump(all_candidates, f, indent=2, ensure_ascii=False)

    print(f"\n\n=== SUMMARY ===")
    print(f"Total candidates: {len(all_candidates)}")
    print(f"Saved to: {candidates_path}")
    print("\nReview the candidates and run with --import to add selected ones")

    # Group by playwright for easier review
    by_playwright = {}
    for c in all_candidates:
        name = c['person_name']
        if name not in by_playwright:
            by_playwright[name] = []
        by_playwright[name].append(c)

    print("\n=== CANDIDATES BY PLAYWRIGHT ===")
    for name, cands in sorted(by_playwright.items()):
        print(f"\n{name}:")
        for c in cands:
            dur_str = f"{c['duration']//60}m" if c['duration'] else "?"
            desc_preview = c['description'][:80] + "..." if c['description'] and len(c['description']) > 80 else c['description']
            print(f"  - {c['title']} ({dur_str}) [{c['program_type']}]")
            print(f"    {desc_preview}")
            print(f"    URL: {c['nrk_url']}")

    conn.close()

if __name__ == "__main__":
    main()
