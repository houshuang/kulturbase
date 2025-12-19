#!/usr/bin/env python3
"""
Enrich plays with playwright information by parsing episode descriptions.

Looks for patterns like "Av [Author Name]" in descriptions and matches
against existing persons in the database.
"""

import sqlite3
import re
from collections import Counter

DB_PATH = '../static/kulturperler.db'

def normalize_name(name):
    """Normalize a name for matching."""
    return name.lower().strip()

def extract_author_from_description(desc):
    """Extract author name from description using various patterns."""
    if not desc:
        return None

    patterns = [
        r'\bAv ([A-ZÆØÅ][a-zæøå]+(?:\s+[A-ZÆØÅ][a-zæøå]+)+)\.?\s*$',  # "Av Name Name." at end
        r'\bAv ([A-ZÆØÅ][a-zæøå]+(?:\s+[A-ZÆØÅ]\.?\s*)?[A-ZÆØÅ]?[a-zæøå]+)\.?\s*$',  # "Av Name N. Name" at end
        r'\bAv ([A-ZÆØÅ][a-zæøå]+(?:\s+[A-ZÆØÅ][a-zæøå]+)+)\.',  # "Av Name Name." anywhere
        r'(?:drama|komedie|stykke|skuespill) av ([A-ZÆØÅ][a-zæøå]+(?:\s+[A-ZÆØÅ][a-zæøå]+)+)',  # "drama av Name"
    ]

    for pattern in patterns:
        match = re.search(pattern, desc)
        if match:
            name = match.group(1).strip()
            # Filter out common false positives
            if name.lower() not in ['den', 'det', 'de', 'en', 'et', 'nrk', 'med']:
                return name

    return None

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Build a lookup of existing persons
    cur.execute("SELECT id, name, normalized_name FROM persons")
    persons = cur.fetchall()
    person_lookup = {}
    for p in persons:
        # Index by normalized name and variations
        norm = normalize_name(p['name'])
        person_lookup[norm] = p['id']
        # Also index by last name + first name initial for partial matches
        parts = p['name'].split()
        if len(parts) >= 2:
            # "Ibsen" -> Henrik Ibsen
            person_lookup[normalize_name(parts[-1])] = p['id']

    # Get all plays without playwright
    cur.execute("""
        SELECT p.id, p.title FROM plays p WHERE p.playwright_id IS NULL
    """)
    plays_without_playwright = cur.fetchall()
    print(f"Found {len(plays_without_playwright)} plays without playwright")

    updated = 0
    not_found = []

    for play in plays_without_playwright:
        play_id = play['id']
        play_title = play['title']

        # Get all descriptions for this play's performances/episodes
        cur.execute("""
            SELECT DISTINCT e.description
            FROM episodes e
            JOIN performances perf ON e.performance_id = perf.id
            WHERE perf.work_id = ?
            AND e.description IS NOT NULL
        """, (play_id,))
        descriptions = [row['description'] for row in cur.fetchall()]

        # Also check performance descriptions
        cur.execute("""
            SELECT DISTINCT description
            FROM performances
            WHERE work_id = ? AND description IS NOT NULL
        """, (play_id,))
        descriptions.extend([row['description'] for row in cur.fetchall()])

        author_candidates = []
        for desc in descriptions:
            author = extract_author_from_description(desc)
            if author:
                author_candidates.append(author)

        if not author_candidates:
            continue

        # Try to match the most common author candidate
        author_counts = Counter(author_candidates)

        for author_name, _ in author_counts.most_common():
            norm_author = normalize_name(author_name)

            # Try exact match first
            if norm_author in person_lookup:
                person_id = person_lookup[norm_author]
                cur.execute("UPDATE plays SET playwright_id = ? WHERE id = ?", (person_id, play_id))
                cur.execute("SELECT name FROM persons WHERE id = ?", (person_id,))
                matched_name = cur.fetchone()['name']
                print(f"  {play_title} -> {matched_name}")
                updated += 1
                break

            # Try partial match (last name only)
            parts = author_name.split()
            if len(parts) >= 2:
                last_name = normalize_name(parts[-1])
                if last_name in person_lookup:
                    person_id = person_lookup[last_name]
                    cur.execute("UPDATE plays SET playwright_id = ? WHERE id = ?", (person_id, play_id))
                    cur.execute("SELECT name FROM persons WHERE id = ?", (person_id,))
                    matched_name = cur.fetchone()['name']
                    print(f"  {play_title} -> {matched_name} (partial match from '{author_name}')")
                    updated += 1
                    break
        else:
            # No match found - might need to create new person
            if author_candidates:
                not_found.append((play_title, author_candidates[0]))

    conn.commit()

    # Report authors that weren't found
    if not_found:
        print(f"\n--- Authors not found in database ({len(not_found)}) ---")
        # Group by author
        by_author = {}
        for title, author in not_found:
            if author not in by_author:
                by_author[author] = []
            by_author[author].append(title)

        for author, titles in sorted(by_author.items(), key=lambda x: -len(x[1])):
            print(f"  {author}: {len(titles)} plays")

    conn.close()
    print(f"\nDone! Updated {updated} plays")

if __name__ == '__main__':
    main()
