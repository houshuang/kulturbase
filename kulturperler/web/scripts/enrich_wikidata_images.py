#!/usr/bin/env python3
"""
Fetch person images from Wikidata for authors without Wikipedia images.
"""

import sqlite3
import requests
import time

DB_PATH = 'static/kulturperler.db'
WIKIDATA_SPARQL = 'https://query.wikidata.org/sparql'

def sparql_query(query):
    """Execute a SPARQL query against Wikidata."""
    headers = {
        'User-Agent': 'Kulturperler/1.0 (educational project)',
        'Accept': 'application/json'
    }
    params = {'query': query, 'format': 'json'}
    response = requests.get(WIKIDATA_SPARQL, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    return response.json()

def get_wikidata_image(wikidata_id):
    """Get image URL for a Wikidata entity."""
    query = f"""
    SELECT ?image WHERE {{
      wd:{wikidata_id} wdt:P18 ?image .
    }}
    LIMIT 1
    """
    try:
        results = sparql_query(query)
        if results['results']['bindings']:
            return results['results']['bindings'][0]['image']['value']
    except Exception as e:
        print(f"  Error fetching image for {wikidata_id}: {e}")
    return None

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get persons without images but with wikidata_id
    cursor.execute("""
        SELECT id, name, wikidata_id
        FROM persons
        WHERE image_url IS NULL
        AND wikidata_id IS NOT NULL
        ORDER BY id
    """)
    persons = cursor.fetchall()

    print(f"Found {len(persons)} persons without images but with Wikidata ID")

    updated = 0
    for person in persons:
        print(f"  Checking {person['name']} ({person['wikidata_id']})...")
        image_url = get_wikidata_image(person['wikidata_id'])

        if image_url:
            cursor.execute("UPDATE persons SET image_url = ? WHERE id = ?",
                          (image_url, person['id']))
            conn.commit()
            print(f"    Found image: {image_url[:60]}...")
            updated += 1
        else:
            print(f"    No image found")

        time.sleep(0.3)  # Rate limit

    print(f"\n=== Summary ===")
    print(f"Updated {updated} persons with images")

    # Show persons still missing images
    cursor.execute("""
        SELECT name, wikidata_id FROM persons
        WHERE image_url IS NULL
        AND id IN (SELECT DISTINCT playwright_id FROM plays WHERE playwright_id IS NOT NULL)
        LIMIT 10
    """)
    missing = cursor.fetchall()
    if missing:
        print("\nPlaywrights still missing images:")
        for row in missing:
            print(f"  {row['name']} (wikidata: {row['wikidata_id'] or 'none'})")

    conn.close()

if __name__ == '__main__':
    main()
