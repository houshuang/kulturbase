#!/usr/bin/env python3
"""
Fetch short bios from Norwegian Wikipedia for playwrights.
"""

import sqlite3
import subprocess
import json
import time
import urllib.parse
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "static" / "kulturperler.db"

def fetch_wikipedia_extract(title: str) -> tuple[str | None, str | None]:
    """Fetch extract and URL from Norwegian Wikipedia using curl."""
    encoded_title = urllib.parse.quote(title.replace(" ", "_"))

    api_url = f"https://no.wikipedia.org/api/rest_v1/page/summary/{encoded_title}"

    try:
        result = subprocess.run(
            ['curl', '-s', '-L', '-H', 'User-Agent: Kulturperler/1.0', api_url],
            capture_output=True,
            text=True,
            timeout=15
        )

        if result.returncode != 0:
            return None, None

        data = json.loads(result.stdout)

        if 'title' in data and data.get('type') == 'https://mediawiki.org/wiki/HyperSwitch/errors/not_found':
            return None, None

        extract = data.get('extract', '')
        page_url = data.get('content_urls', {}).get('desktop', {}).get('page', '')

        # Limit to first 2-3 sentences (roughly 350 chars)
        if extract and len(extract) > 350:
            sentences = extract.split('. ')
            short_extract = ''
            for sentence in sentences:
                if len(short_extract) + len(sentence) < 350:
                    short_extract += sentence + '. '
                else:
                    break
            extract = short_extract.strip()

        return extract if extract else None, page_url if page_url else None

    except subprocess.TimeoutExpired:
        print(f"  Timeout for {title}")
        return None, None
    except json.JSONDecodeError:
        return None, None
    except Exception as e:
        print(f"  Error: {e}")
        return None, None


def fetch_bios(conn: sqlite3.Connection):
    cursor = conn.cursor()

    # Get all playwrights without bios
    cursor.execute("""
        SELECT DISTINCT p.id, p.name, p.wikipedia_url, p.bio
        FROM persons p
        JOIN plays pl ON p.id = pl.playwright_id
        WHERE p.bio IS NULL OR p.bio = ''
        ORDER BY p.name
    """)

    playwrights = cursor.fetchall()
    print(f"Found {len(playwrights)} playwrights without bios")

    updated = 0
    for person_id, name, existing_url, existing_bio in playwrights:
        print(f"Fetching bio for: {name}...", end=" ", flush=True)

        bio, wiki_url = fetch_wikipedia_extract(name)

        if bio:
            cursor.execute(
                "UPDATE persons SET bio = ?, wikipedia_url = COALESCE(wikipedia_url, ?) WHERE id = ?",
                (bio, wiki_url, person_id)
            )
            updated += 1
            print(f"OK ({len(bio)} chars)")
        else:
            print("Not found")

        time.sleep(0.2)  # Rate limit

    conn.commit()
    print(f"\nUpdated {updated} of {len(playwrights)} playwrights with bios")


def main():
    print("=" * 60)
    print("Fetching Wikipedia bios for playwrights")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    try:
        fetch_bios(conn)
    finally:
        conn.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
