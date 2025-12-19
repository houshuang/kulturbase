#!/usr/bin/env python3
"""
Final enrichment pass - exact matches only, no partial matching.
"""

import sqlite3
import re
from collections import Counter

DB_PATH = '../static/kulturperler.db'

def normalize_name(name):
    return name.lower().strip()

def extract_author_from_description(desc):
    if not desc:
        return None

    patterns = [
        r'\bAv ([A-ZÆØÅ][a-zæøå]+(?:\s+[A-ZÆØÅ]\.?\s*)?(?:[A-ZÆØÅ][a-zæøå]+)+)\.?\s*$',
        r'\bAv ([A-ZÆØÅ][a-zæøå]+(?:\s+[A-ZÆØÅ][a-zæøå]+)+)\.',
        r'(?:drama|komedie|stykke|skuespill) av ([A-ZÆØÅ][a-zæøå]+(?:\s+[A-ZÆØÅ][a-zæøå]+)+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, desc)
        if match:
            name = match.group(1).strip()
            if name.lower() not in ['den', 'det', 'de', 'en', 'et', 'nrk', 'med']:
                return name
    return None

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Build lookup - exact matches only
    cur.execute("SELECT id, name FROM persons")
    persons = cur.fetchall()
    person_lookup = {normalize_name(p['name']): p['id'] for p in persons}

    # Get plays without playwright
    cur.execute("SELECT id, title FROM plays WHERE playwright_id IS NULL")
    plays = cur.fetchall()
    print(f"Found {len(plays)} plays without playwright")

    updated = 0
    not_found = {}

    for play in plays:
        play_id, play_title = play['id'], play['title']

        # Get descriptions
        cur.execute("""
            SELECT DISTINCT e.description FROM episodes e
            JOIN performances perf ON e.performance_id = perf.id
            WHERE perf.work_id = ? AND e.description IS NOT NULL
            UNION
            SELECT DISTINCT description FROM performances
            WHERE work_id = ? AND description IS NOT NULL
        """, (play_id, play_id))

        descriptions = [row['description'] for row in cur.fetchall()]

        for desc in descriptions:
            author = extract_author_from_description(desc)
            if author:
                norm = normalize_name(author)
                if norm in person_lookup:
                    cur.execute("UPDATE plays SET playwright_id = ? WHERE id = ?",
                               (person_lookup[norm], play_id))
                    print(f"  {play_title} -> {author}")
                    updated += 1
                    break
                else:
                    not_found[author] = not_found.get(author, 0) + 1

    conn.commit()

    print(f"\nUpdated {updated} plays")
    print(f"\nMissing authors (top 20):")
    for author, count in sorted(not_found.items(), key=lambda x: -x[1])[:20]:
        print(f"  {author}: {count}")

    conn.close()

if __name__ == '__main__':
    main()
