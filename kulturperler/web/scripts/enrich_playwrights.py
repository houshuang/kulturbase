#!/usr/bin/env python3
"""
Enrich plays and playwrights with data from Sceneweb.
Fetches playwright info, year written, original title, etc.
Caches fetched data to avoid repeated requests.
"""

import sqlite3
import requests
from bs4 import BeautifulSoup
import time
import re
import json
import os

DB_PATH = 'static/kulturperler.db'
CACHE_FILE = 'static/sceneweb_cache.json'

def load_cache():
    """Load cached Sceneweb data."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_cache(cache):
    """Save cache to file."""
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

def get_sceneweb_artwork(url, cache):
    """Fetch artwork data from Sceneweb (with caching)."""
    # Check cache first
    if url in cache:
        return cache[url]

    try:
        headers = {'User-Agent': 'Kulturperler/1.0 (educational project)'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        data = {}

        # Get playwright/author
        author_link = soup.select_one('a[href*="/nb/person/"]')
        if author_link:
            data['playwright_name'] = author_link.get_text(strip=True)
            data['playwright_sceneweb_url'] = 'https://sceneweb.no' + author_link['href'] if author_link['href'].startswith('/') else author_link['href']
            # Extract sceneweb ID from URL
            match = re.search(r'/person/(\d+)/', data['playwright_sceneweb_url'])
            if match:
                data['playwright_sceneweb_id'] = int(match.group(1))

        # Look for original title
        text = soup.get_text()
        # Pattern: "Originaltittel" followed by title in quotes
        orig_match = re.search(r'[Oo]riginaltittel[:\s]+["\']?([^"\'\n]+)["\']?', text)
        if orig_match:
            data['original_title'] = orig_match.group(1).strip()

        # Look for quoted foreign titles (French, German, etc.)
        if 'original_title' not in data:
            for pattern in [r'"(L\'[^"]+)"', r'"(Le [^"]+)"', r'"(La [^"]+)"', r'"(Der [^"]+)"', r'"(Die [^"]+)"', r'"(The [^"]+)"']:
                match = re.search(pattern, text)
                if match:
                    data['original_title'] = match.group(1)
                    break

        # Look for year written in the info table
        for row in soup.select('dl'):
            dts = row.select('dt')
            dds = row.select('dd')
            for dt, dd in zip(dts, dds):
                label = dt.get_text(strip=True).lower()
                value = dd.get_text(strip=True)
                if 'skrevet' in label or 'år' in label or 'premiered' in label:
                    year_match = re.search(r'(\d{4})', value)
                    if year_match:
                        data['year_written'] = int(year_match.group(1))

        # Try alternate structure for year
        for line in text.split('\n'):
            if 'Skrevet' in line or 'Uroppført' in line:
                year_match = re.search(r'(\d{4})', line)
                if year_match and 'year_written' not in data:
                    data['year_written'] = int(year_match.group(1))

        # Cache the result
        cache[url] = data
        return data
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        cache[url] = {}  # Cache empty result to avoid retrying
        return {}

def get_sceneweb_person(url):
    """Fetch person data from Sceneweb."""
    try:
        headers = {'User-Agent': 'Kulturperler/1.0 (educational project)'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        data = {}

        # Get birth/death years from text
        text = soup.get_text()

        # Look for patterns like "1684-1754" or "(1684-1754)" or "f. 1684, d. 1754"
        year_pattern = re.search(r'\(?\s*(\d{4})\s*[-–]\s*(\d{4})\s*\)?', text)
        if year_pattern:
            data['birth_year'] = int(year_pattern.group(1))
            data['death_year'] = int(year_pattern.group(2))

        # Look for Wikipedia link
        wiki_link = soup.select_one('a[href*="wikipedia.org"]')
        if wiki_link:
            data['wikipedia_url'] = wiki_link['href']

        return data
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        return {}

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Load cache
    cache = load_cache()
    print(f"Loaded cache with {len(cache)} entries")

    # Get plays with sceneweb URLs but missing data
    cursor.execute("""
        SELECT id, title, sceneweb_url, playwright_id, year_written, original_title
        FROM plays
        WHERE sceneweb_url IS NOT NULL
          AND (playwright_id IS NULL OR year_written IS NULL OR original_title IS NULL)
        ORDER BY id
    """)
    plays = cursor.fetchall()

    print(f"Found {len(plays)} plays to enrich")

    playwright_cache = {}  # name -> person_id

    for play in plays:
        print(f"\nProcessing: {play['title']}")
        print(f"  URL: {play['sceneweb_url']}")

        data = get_sceneweb_artwork(play['sceneweb_url'], cache)

        if not data:
            print("  No data found")
            continue

        updates = []
        params = []

        # Handle playwright
        if 'playwright_name' in data and not play['playwright_id']:
            playwright_name = data['playwright_name']
            print(f"  Playwright: {playwright_name}")

            if playwright_name in playwright_cache:
                person_id = playwright_cache[playwright_name]
            else:
                # Check if person exists
                cursor.execute("SELECT id FROM persons WHERE name = ?", (playwright_name,))
                existing = cursor.fetchone()

                if existing:
                    person_id = existing['id']
                else:
                    # Create new person
                    sceneweb_url = data.get('playwright_sceneweb_url')
                    sceneweb_id = data.get('playwright_sceneweb_id')

                    # Get more person data from sceneweb
                    person_data = {}
                    if sceneweb_url:
                        print(f"  Fetching playwright info from {sceneweb_url}")
                        person_data = get_sceneweb_person(sceneweb_url)
                        time.sleep(0.5)

                    cursor.execute("""
                        INSERT INTO persons (name, normalized_name, birth_year, death_year, sceneweb_id, sceneweb_url, wikipedia_url)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        playwright_name,
                        playwright_name.lower(),
                        person_data.get('birth_year'),
                        person_data.get('death_year'),
                        sceneweb_id,
                        sceneweb_url,
                        person_data.get('wikipedia_url')
                    ))
                    person_id = cursor.lastrowid
                    print(f"  Created new person with ID {person_id}")
                    if person_data.get('birth_year'):
                        print(f"    Birth: {person_data.get('birth_year')}, Death: {person_data.get('death_year')}")

                playwright_cache[playwright_name] = person_id

            updates.append("playwright_id = ?")
            params.append(person_id)

        # Handle year written
        if 'year_written' in data and not play['year_written']:
            print(f"  Year written: {data['year_written']}")
            updates.append("year_written = ?")
            params.append(data['year_written'])

        # Handle original title
        if 'original_title' in data and not play['original_title']:
            print(f"  Original title: {data['original_title']}")
            updates.append("original_title = ?")
            params.append(data['original_title'])

        if updates:
            params.append(play['id'])
            sql = f"UPDATE plays SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(sql, params)
            print(f"  Updated play")

        conn.commit()

        # Save cache periodically
        if len(cache) % 10 == 0:
            save_cache(cache)

        time.sleep(0.5)  # Be nice to the server

    # Save final cache
    save_cache(cache)
    print(f"\nSaved cache with {len(cache)} entries")

    # Summary
    cursor.execute("SELECT COUNT(*) FROM plays WHERE playwright_id IS NOT NULL")
    with_playwright = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM plays WHERE year_written IS NOT NULL")
    with_year = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM plays WHERE original_title IS NOT NULL")
    with_original = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM plays")
    total = cursor.fetchone()[0]

    print(f"\n=== Summary ===")
    print(f"Plays with playwright: {with_playwright}/{total}")
    print(f"Plays with year written: {with_year}/{total}")
    print(f"Plays with original title: {with_original}/{total}")

    conn.close()

if __name__ == '__main__':
    main()
