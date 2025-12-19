#!/usr/bin/env python3
"""
Fetch author bios and images from Norwegian Wikipedia.
"""

import sqlite3
import requests
import time
import re

DB_PATH = 'static/kulturperler.db'

def get_wikipedia_extract(title):
    """Fetch extract and image from Norwegian Wikipedia."""
    # First, get page info with extract and images
    params = {
        'action': 'query',
        'titles': title,
        'prop': 'extracts|pageimages',
        'exintro': True,  # Only intro section
        'explaintext': True,  # Plain text
        'exsentences': 3,  # First 3 sentences
        'piprop': 'thumbnail',
        'pithumbsize': 200,
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

            result = {}

            # Get extract
            if 'extract' in page:
                extract = page['extract']
                # Clean up the extract
                extract = re.sub(r'\s+', ' ', extract).strip()
                result['bio'] = extract

            # Get thumbnail
            if 'thumbnail' in page:
                result['image_url'] = page['thumbnail']['source']

            return result if result else None

    except Exception as e:
        print(f"  Error fetching {title}: {e}")
        return None

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Add bio and image_url columns if they don't exist
    try:
        cursor.execute("ALTER TABLE persons ADD COLUMN bio TEXT")
        print("Added bio column")
    except:
        pass

    try:
        cursor.execute("ALTER TABLE persons ADD COLUMN image_url TEXT")
        print("Added image_url column")
    except:
        pass

    conn.commit()

    # Get playwrights with wikipedia URLs but no bio
    cursor.execute("""
        SELECT id, name, wikipedia_url
        FROM persons
        WHERE wikipedia_url IS NOT NULL
          AND (bio IS NULL OR image_url IS NULL)
        ORDER BY id
    """)
    persons = cursor.fetchall()

    print(f"Found {len(persons)} persons to enrich")

    for person in persons:
        print(f"\nProcessing: {person['name']}")

        # Extract title from Wikipedia URL
        wiki_url = person['wikipedia_url']
        if not wiki_url:
            continue

        # Get the title from the URL
        title = wiki_url.split('/')[-1].replace('_', ' ')
        print(f"  Wikipedia title: {title}")

        data = get_wikipedia_extract(title)

        if not data:
            print("  No data found")
            continue

        updates = []
        params = []

        if 'bio' in data:
            print(f"  Bio: {data['bio'][:80]}...")
            updates.append("bio = ?")
            params.append(data['bio'])

        if 'image_url' in data:
            print(f"  Image: {data['image_url']}")
            updates.append("image_url = ?")
            params.append(data['image_url'])

        if updates:
            params.append(person['id'])
            sql = f"UPDATE persons SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(sql, params)
            conn.commit()

        time.sleep(0.3)  # Be nice to Wikipedia

    # Summary
    cursor.execute("SELECT COUNT(*) FROM persons WHERE bio IS NOT NULL")
    with_bio = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM persons WHERE image_url IS NOT NULL")
    with_image = cursor.fetchone()[0]

    print(f"\n=== Summary ===")
    print(f"Persons with bio: {with_bio}")
    print(f"Persons with image: {with_image}")

    # Show results
    cursor.execute("""
        SELECT name, bio, image_url
        FROM persons
        WHERE bio IS NOT NULL
        LIMIT 5
    """)
    print("\nSample bios:")
    for row in cursor.fetchall():
        bio_preview = row['bio'][:100] + '...' if row['bio'] and len(row['bio']) > 100 else row['bio']
        print(f"  {row['name']}: {bio_preview}")

    conn.close()

if __name__ == '__main__':
    main()
