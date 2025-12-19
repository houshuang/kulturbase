#!/usr/bin/env python3
"""
Search Bokselskap.no for Norwegian plays and add links to database.
"""

import sqlite3
import requests
from bs4 import BeautifulSoup
import time
import re
from pathlib import Path
from urllib.parse import quote

DB_PATH = Path(__file__).parent.parent / "static" / "kulturperler.db"

# Known Norwegian playwrights
NORWEGIAN_PLAYWRIGHTS = [
    'Henrik Ibsen', 'Ludvig Holberg', 'Bjørnstjerne Bjørnson',
    'Knut Hamsun', 'Alexander Kielland', 'Arne Garborg',
    'Gunnar Heiberg', 'Nordahl Grieg', 'Hans E. Kinck',
    'Oskar Braaten', 'Helge Krog', 'Johan Falkberget',
    'Sigurd Hoel', 'Tarjei Vesaas', 'Johan Borgen',
    'Torborg Nedreaas', 'Jens Bjørneboe', 'Sigurd Christiansen',
    'Nils Kjær', 'Hans Wiers-Jenssen', 'Hulda Garborg',
    'Amalie Skram', 'Jonas Lie', 'Gabriel Scott',
    'Peter Egge', 'Nini Roll Anker', 'Vilhelm Krag',
    'Hans Aanrud', 'Jacob Breda Bull', 'Johan Bojer',
    'Olav Duun', 'Kristofer Uppdal', 'Arnulf Øverland',
    'Odd Eidem', 'Axel Kielland'
]

def search_bokselskap(query):
    """Search Bokselskap.no for a query."""
    url = f"https://www.bokselskap.no/sok?q={quote(query)}"
    try:
        resp = requests.get(url, timeout=15)
        if resp.ok:
            return resp.text
    except Exception as e:
        print(f"  Error searching: {e}")
    return None

def get_bokselskap_page(url):
    """Get a Bokselskap page."""
    try:
        resp = requests.get(url, timeout=15)
        if resp.ok:
            return resp.text
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
    return None

def find_play_on_bokselskap(title, playwright):
    """Search for a specific play on Bokselskap."""
    # Try searching for play title
    html = search_bokselskap(title)
    if not html:
        return None

    soup = BeautifulSoup(html, 'html.parser')

    # Look for results
    results = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        if '/boker/' in href and href.startswith('https://www.bokselskap.no'):
            text = link.get_text(strip=True)
            if text:
                results.append({'url': href, 'text': text})

    # Filter for matches
    title_lower = title.lower()
    playwright_lower = playwright.lower().split()[-1]  # Last name

    for result in results:
        result_text = result['text'].lower()
        result_url = result['url'].lower()

        # Check if title matches
        title_words = [w for w in title_lower.split() if len(w) > 3]
        if any(w in result_text or w in result_url for w in title_words):
            # Verify it's by the right playwright by fetching the page
            page_html = get_bokselskap_page(result['url'])
            if page_html and playwright_lower in page_html.lower():
                return result['url']

    return None

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get Norwegian plays without Bokselskap links
    cursor.execute("""
        SELECT p.id, p.title, pe.name as playwright
        FROM plays p
        JOIN persons pe ON p.playwright_id = pe.id
        WHERE pe.name IN ({})
        AND p.id NOT IN (
            SELECT play_id FROM play_external_links
            WHERE type = 'bokselskap' AND play_id IS NOT NULL
        )
        ORDER BY pe.name, p.title
    """.format(','.join('?' * len(NORWEGIAN_PLAYWRIGHTS))), NORWEGIAN_PLAYWRIGHTS)

    plays = cursor.fetchall()
    print(f"Found {len(plays)} Norwegian plays without Bokselskap links\n")

    found = []
    not_found = []

    for play_id, title, playwright in plays:
        print(f"Searching: {title} ({playwright})")

        url = find_play_on_bokselskap(title, playwright)

        if url:
            print(f"  Found: {url}")
            found.append((play_id, title, playwright, url))
        else:
            print(f"  Not found")
            not_found.append((play_id, title, playwright))

        time.sleep(1)  # Be nice to the server

    print(f"\n\n=== SUMMARY ===")
    print(f"Found: {len(found)}")
    print(f"Not found: {len(not_found)}")

    if found:
        print(f"\n=== FOUND ON BOKSELSKAP ===")
        for play_id, title, playwright, url in found:
            print(f"  {title} ({playwright})")
            print(f"    {url}")

        # Ask to add to database
        print(f"\nAdd {len(found)} links to database? (y/n)")
        response = input().strip().lower()
        if response == 'y':
            for play_id, title, playwright, url in found:
                cursor.execute("""
                    INSERT INTO play_external_links (play_id, url, title, type)
                    VALUES (?, ?, 'Bokselskap.no', 'bokselskap')
                """, (play_id, url))
                print(f"  Added: {title}")
            conn.commit()
            print("Done!")

    if not_found:
        print(f"\n=== NOT FOUND ===")
        for play_id, title, playwright in not_found:
            print(f"  {title} ({playwright})")

    conn.close()

if __name__ == "__main__":
    main()
