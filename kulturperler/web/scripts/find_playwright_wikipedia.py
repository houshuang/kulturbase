#!/usr/bin/env python3
"""
Find Wikipedia URLs for playwrights by searching Norwegian Wikipedia.
"""

import sqlite3
import requests
import time
import re

DB_PATH = 'static/kulturperler.db'

def search_wikipedia(query):
    """Search Norwegian Wikipedia and return results."""
    params = {
        'action': 'query',
        'list': 'search',
        'srsearch': query,
        'srlimit': 3,
        'format': 'json'
    }

    headers = {'User-Agent': 'Kulturperler/1.0 (educational project)'}

    try:
        response = requests.get(
            'https://no.wikipedia.org/w/api.php',
            params=params,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data.get('query', {}).get('search', [])
    except:
        return []

def get_page_info(title):
    """Get page extract and categories to verify it's about a person."""
    params = {
        'action': 'query',
        'titles': title,
        'prop': 'extracts|categories|pageimages',
        'exintro': True,
        'explaintext': True,
        'exsentences': 3,
        'cllimit': 10,
        'piprop': 'thumbnail',
        'pithumbsize': 250,
        'format': 'json',
        'redirects': 1
    }

    headers = {'User-Agent': 'Kulturperler/1.0 (educational project)'}

    try:
        response = requests.get(
            'https://no.wikipedia.org/w/api.php',
            params=params,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        pages = data.get('query', {}).get('pages', {})
        for page_id, page in pages.items():
            if page_id == '-1':
                return None

            result = {
                'title': page.get('title'),
                'extract': page.get('extract', ''),
                'categories': [c['title'] for c in page.get('categories', [])],
                'image_url': page.get('thumbnail', {}).get('source')
            }
            return result
    except:
        pass

    return None

def is_person_page(info):
    """Check if the page is about a person (writer/dramatist)."""
    if not info:
        return False

    extract = info['extract'].lower()
    categories = ' '.join(info['categories']).lower()

    # Check for person indicators
    person_keywords = ['født', 'var en', 'er en', 'forfatter', 'dramatiker',
                       'skuespiller', 'regissør', 'komponist', 'dikter']

    if any(kw in extract for kw in person_keywords):
        return True

    if 'fødsler' in categories or 'dødsfall' in categories:
        return True

    return False

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get playwrights without Wikipedia URL
    cursor.execute("""
        SELECT p.id, p.name, p.birth_year, p.death_year
        FROM persons p
        WHERE p.id IN (SELECT DISTINCT playwright_id FROM plays WHERE playwright_id IS NOT NULL)
        AND p.wikipedia_url IS NULL
        ORDER BY p.name
    """)
    playwrights = cursor.fetchall()

    print(f"Searching Wikipedia for {len(playwrights)} playwrights...\n")

    found = 0
    for pw in playwrights:
        name = pw['name']
        birth = pw['birth_year']
        death = pw['death_year']

        # Search Wikipedia
        results = search_wikipedia(f"{name} forfatter dramatiker")
        if not results:
            results = search_wikipedia(name)

        for result in results:
            wiki_title = result['title']

            # Skip disambiguation pages
            if '(andre betydninger)' in wiki_title.lower():
                continue

            info = get_page_info(wiki_title)

            if not is_person_page(info):
                continue

            # Verify it's about the right person using dates if available
            extract = info['extract'].lower()

            # Check if dates match (if we have them)
            if birth and str(birth) not in extract:
                if death and str(death) not in extract:
                    # Neither date found, might be wrong person
                    continue

            # Update database
            wiki_url = f"https://no.wikipedia.org/wiki/{wiki_title.replace(' ', '_')}"

            updates = ["wikipedia_url = ?"]
            params = [wiki_url]

            if info['extract']:
                bio = re.sub(r'\s+', ' ', info['extract']).strip()
                updates.append("bio = ?")
                params.append(bio)

            if info['image_url']:
                updates.append("image_url = ?")
                params.append(info['image_url'])

            params.append(pw['id'])
            cursor.execute(f"UPDATE persons SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()

            print(f"  + {name}: {wiki_url}")
            found += 1
            break

        time.sleep(0.3)

    print(f"\nFound {found} Wikipedia pages")

    # Summary
    cursor.execute("""
        SELECT COUNT(*) FROM persons
        WHERE id IN (SELECT DISTINCT playwright_id FROM plays WHERE playwright_id IS NOT NULL)
    """)
    total = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM persons
        WHERE id IN (SELECT DISTINCT playwright_id FROM plays WHERE playwright_id IS NOT NULL)
        AND wikipedia_url IS NOT NULL
    """)
    with_wiki = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM persons
        WHERE id IN (SELECT DISTINCT playwright_id FROM plays WHERE playwright_id IS NOT NULL)
        AND bio IS NOT NULL
    """)
    with_bio = cursor.fetchone()[0]

    print(f"\nPlaywrights with Wikipedia: {with_wiki}/{total}")
    print(f"Playwrights with bio: {with_bio}/{total}")

    conn.close()

if __name__ == '__main__':
    main()
