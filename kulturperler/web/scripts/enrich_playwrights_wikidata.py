#!/usr/bin/env python3
"""
Enrich plays with playwright information from Wikidata.

Uses SPARQL queries to find plays by title and get their authors.
"""

import sqlite3
import requests
import time
import re
import json
from urllib.parse import quote

DB_PATH = '../static/kulturperler.db'
WIKIDATA_SPARQL = 'https://query.wikidata.org/sparql'

def normalize_title(title):
    """Normalize title for matching."""
    # Remove common suffixes and clean up
    title = re.sub(r'\s*\(\d{4}\)\s*$', '', title)  # Remove year
    title = re.sub(r'\s*-\s*radioteater\s*$', '', title, flags=re.I)
    title = title.strip()
    return title

def search_wikidata_play(title):
    """Search Wikidata for a play by title and return author info."""

    # Try exact Norwegian title first
    query = '''
    SELECT ?work ?workLabel ?author ?authorLabel ?authorBirth ?authorDeath WHERE {
      ?work wdt:P31/wdt:P279* wd:Q25379.  # instance of play or subclass
      ?work rdfs:label "%s"@nb.
      OPTIONAL { ?work wdt:P50 ?author. }
      OPTIONAL { ?author wdt:P569 ?authorBirth. }
      OPTIONAL { ?author wdt:P570 ?authorDeath. }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "nb,no,en". }
    }
    LIMIT 5
    ''' % title.replace('"', '\\"')

    try:
        response = requests.get(WIKIDATA_SPARQL,
                               params={'query': query, 'format': 'json'},
                               headers={'User-Agent': 'KulturperlerEnrichment/1.0'},
                               timeout=30)
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', {}).get('bindings', [])
            if results:
                return results
    except Exception as e:
        print(f"    Error querying Wikidata: {e}")

    # Try English title
    query_en = '''
    SELECT ?work ?workLabel ?author ?authorLabel ?authorBirth ?authorDeath WHERE {
      ?work wdt:P31/wdt:P279* wd:Q25379.
      ?work rdfs:label "%s"@en.
      OPTIONAL { ?work wdt:P50 ?author. }
      OPTIONAL { ?author wdt:P569 ?authorBirth. }
      OPTIONAL { ?author wdt:P570 ?authorDeath. }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "nb,no,en". }
    }
    LIMIT 5
    ''' % title.replace('"', '\\"')

    try:
        response = requests.get(WIKIDATA_SPARQL,
                               params={'query': query_en, 'format': 'json'},
                               headers={'User-Agent': 'KulturperlerEnrichment/1.0'},
                               timeout=30)
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', {}).get('bindings', [])
            if results:
                return results
    except Exception as e:
        print(f"    Error querying Wikidata (EN): {e}")

    return None

def search_wikidata_fuzzy(title):
    """Fuzzy search using Wikidata search API."""
    try:
        url = f"https://www.wikidata.org/w/api.php"
        params = {
            'action': 'wbsearchentities',
            'search': title,
            'language': 'nb',
            'uselang': 'nb',
            'type': 'item',
            'limit': 5,
            'format': 'json'
        }
        response = requests.get(url, params=params,
                               headers={'User-Agent': 'KulturperlerEnrichment/1.0'},
                               timeout=30)
        if response.status_code == 200:
            data = response.json()
            for result in data.get('search', []):
                qid = result.get('id')
                # Check if this is a play and get author
                query = '''
                SELECT ?author ?authorLabel ?authorBirth ?authorDeath WHERE {
                  wd:%s wdt:P31/wdt:P279* wd:Q25379.
                  wd:%s wdt:P50 ?author.
                  OPTIONAL { ?author wdt:P569 ?authorBirth. }
                  OPTIONAL { ?author wdt:P570 ?authorDeath. }
                  SERVICE wikibase:label { bd:serviceParam wikibase:language "nb,no,en". }
                }
                ''' % (qid, qid)

                resp = requests.get(WIKIDATA_SPARQL,
                                   params={'query': query, 'format': 'json'},
                                   headers={'User-Agent': 'KulturperlerEnrichment/1.0'},
                                   timeout=30)
                if resp.status_code == 200:
                    results = resp.json().get('results', {}).get('bindings', [])
                    if results:
                        return results
    except Exception as e:
        print(f"    Error in fuzzy search: {e}")

    return None

def get_or_create_person(cur, name, birth_year=None, death_year=None):
    """Get existing person or create new one."""
    normalized = name.lower().strip()

    cur.execute("SELECT id FROM persons WHERE normalized_name = ?", (normalized,))
    row = cur.fetchone()
    if row:
        return row['id']

    # Create new person
    cur.execute("""
        INSERT INTO persons (name, normalized_name, birth_year, death_year)
        VALUES (?, ?, ?, ?)
    """, (name, normalized, birth_year, death_year))
    return cur.lastrowid

def extract_year(date_str):
    """Extract year from Wikidata date string."""
    if not date_str:
        return None
    match = re.search(r'(\d{4})', date_str)
    if match:
        year = int(match.group(1))
        # Handle BCE dates
        if date_str.startswith('-'):
            year = -year
        return year
    return None

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get plays without playwright
    cur.execute("""
        SELECT p.id, p.title
        FROM plays p
        WHERE p.playwright_id IS NULL
        ORDER BY p.title
    """)
    plays = cur.fetchall()
    print(f"Found {len(plays)} plays without playwright\n")

    updated = 0
    not_found = []

    for i, play in enumerate(plays):
        play_id = play['id']
        title = play['title']
        norm_title = normalize_title(title)

        print(f"[{i+1}/{len(plays)}] {title}...", end=' ', flush=True)

        # Try exact search first
        results = search_wikidata_play(norm_title)

        # Try fuzzy search if no results
        if not results:
            results = search_wikidata_fuzzy(norm_title)

        if results:
            # Get author from first result with author
            for r in results:
                if 'authorLabel' in r:
                    author_name = r['authorLabel']['value']
                    birth = extract_year(r.get('authorBirth', {}).get('value'))
                    death = extract_year(r.get('authorDeath', {}).get('value'))

                    person_id = get_or_create_person(cur, author_name, birth, death)
                    cur.execute("UPDATE plays SET playwright_id = ? WHERE id = ?",
                               (person_id, play_id))
                    print(f"-> {author_name}")
                    updated += 1
                    break
            else:
                print("no author found")
                not_found.append(title)
        else:
            print("not found")
            not_found.append(title)

        # Rate limiting
        time.sleep(0.5)

        # Commit periodically
        if updated % 10 == 0:
            conn.commit()

    conn.commit()
    conn.close()

    print(f"\n=== Summary ===")
    print(f"Updated: {updated}")
    print(f"Not found: {len(not_found)}")

if __name__ == '__main__':
    main()
