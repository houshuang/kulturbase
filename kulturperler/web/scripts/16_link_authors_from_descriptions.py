#!/usr/bin/env python3
"""
Extract playwright names from performance descriptions and link to plays.
Handles patterns like "Av [Name]." at end of descriptions.
"""

import sqlite3
import re
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "static" / "kulturperler.db"


def extract_author_from_description(description: str) -> str | None:
    """Extract author name from 'Av [Name].' pattern at end of description."""
    if not description:
        return None

    # Pattern: ". Av [Name]." or ". Av [Name]" at end
    match = re.search(r'\. Av ([A-ZÆØÅ][a-zæøåA-ZÆØÅ\-\. ]+?)\.?\s*$', description)
    if match:
        return match.group(1).strip()

    return None


def normalize_name(name: str) -> str:
    """Normalize author name for matching."""
    return name.lower().replace('-', ' ').replace('.', ' ').strip()


def find_or_create_person(cursor, name: str) -> int | None:
    """Find existing person or create new one."""
    normalized = normalize_name(name)

    # Try exact match first
    cursor.execute("SELECT id FROM persons WHERE name = ?", (name,))
    row = cursor.fetchone()
    if row:
        return row[0]

    # Try normalized match
    cursor.execute(
        "SELECT id, name FROM persons WHERE LOWER(REPLACE(REPLACE(name, '-', ' '), '.', ' ')) = ?",
        (normalized,)
    )
    row = cursor.fetchone()
    if row:
        print(f"  Found existing person: {row[1]} (id={row[0]})")
        return row[0]

    # Create new person
    cursor.execute(
        "INSERT INTO persons (name, normalized_name) VALUES (?, ?)",
        (name, normalized)
    )
    new_id = cursor.lastrowid
    print(f"  Created new person: {name} (id={new_id})")
    return new_id


def main():
    print("=" * 60)
    print("Linking authors from performance descriptions")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Find performances with author patterns in description
    cursor.execute("""
        SELECT p.id, p.title, p.description, pl.id as play_id, pl.title as play_title
        FROM performances p
        JOIN plays pl ON p.work_id = pl.id
        WHERE pl.playwright_id IS NULL
          AND p.description LIKE '%. Av %'
    """)

    performances = cursor.fetchall()
    print(f"Found {len(performances)} performances to check\n")

    updated = 0
    for perf_id, perf_title, description, play_id, play_title in performances:
        author = extract_author_from_description(description)
        if not author:
            continue

        print(f"Play: {play_title}")
        print(f"  Author: {author}")

        person_id = find_or_create_person(cursor, author)
        if person_id:
            cursor.execute(
                "UPDATE plays SET playwright_id = ? WHERE id = ?",
                (person_id, play_id)
            )
            updated += 1
            print(f"  Linked play {play_id} to person {person_id}")
        print()

    conn.commit()
    print(f"\nUpdated {updated} plays with playwright links")

    conn.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
