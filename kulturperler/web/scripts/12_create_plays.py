#!/usr/bin/env python3
"""
Create plays from performances and link them.

This creates unique plays from performance titles and links performances to them.
"""

import sqlite3
import re
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "static" / "kulturperler.db"


def normalize_title(title: str) -> str:
    """Normalize a title for matching."""
    # Remove year suffixes like "Brand 1999" -> "Brand"
    title = re.sub(r'\s+\d{4}$', '', title)
    # Remove "Radio" suffix
    title = re.sub(r'\s+Radio$', '', title, flags=re.IGNORECASE)
    # Lowercase and strip
    return title.lower().strip()


def create_plays(conn: sqlite3.Connection):
    cursor = conn.cursor()

    print("1. Getting unique performance titles...")
    cursor.execute("""
        SELECT DISTINCT title FROM performances WHERE title IS NOT NULL
    """)
    titles = [row[0] for row in cursor.fetchall()]
    print(f"   Found {len(titles)} unique titles")

    # Group by normalized title
    title_groups = {}
    for title in titles:
        norm = normalize_title(title)
        if norm not in title_groups:
            title_groups[norm] = []
        title_groups[norm].append(title)

    print(f"   Grouped into {len(title_groups)} unique plays")

    print("\n2. Creating plays...")
    plays_created = 0
    for norm_title, variants in title_groups.items():
        # Use the shortest variant as the canonical title (often cleanest)
        canonical = min(variants, key=len)

        cursor.execute("""
            INSERT INTO plays (title, original_title)
            VALUES (?, ?)
        """, (canonical, canonical))
        plays_created += 1

    conn.commit()
    print(f"   Created {plays_created} plays")

    print("\n3. Linking performances to plays...")
    # Link performances to plays by normalized title
    cursor.execute("SELECT id, title FROM plays")
    play_lookup = {}
    for play_id, title in cursor.fetchall():
        norm = normalize_title(title)
        play_lookup[norm] = play_id

    cursor.execute("SELECT id, title FROM performances")
    linked = 0
    for perf_id, title in cursor.fetchall():
        if title:
            norm = normalize_title(title)
            if norm in play_lookup:
                cursor.execute(
                    "UPDATE performances SET work_id = ? WHERE id = ?",
                    (play_lookup[norm], perf_id)
                )
                linked += 1

    conn.commit()
    print(f"   Linked {linked} performances to plays")

    # Also update episodes with play_id
    print("\n4. Updating episodes with play_id...")
    cursor.execute("""
        UPDATE episodes SET play_id = (
            SELECT p.work_id FROM performances p
            WHERE p.id = episodes.performance_id
        )
        WHERE performance_id IS NOT NULL
    """)
    print(f"   Updated {cursor.rowcount} episodes")
    conn.commit()

    # Summary
    print("\n5. Summary:")
    cursor.execute("SELECT COUNT(*) FROM plays")
    print(f"   Plays: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM performances WHERE work_id IS NOT NULL")
    print(f"   Performances linked: {cursor.fetchone()[0]}")

    # Show some examples
    print("\n   Sample plays with multiple performances:")
    cursor.execute("""
        SELECT pl.title, COUNT(p.id) as perf_count
        FROM plays pl
        JOIN performances p ON p.work_id = pl.id
        GROUP BY pl.id
        HAVING perf_count > 1
        ORDER BY perf_count DESC
        LIMIT 5
    """)
    for row in cursor.fetchall():
        print(f"      {row[0]}: {row[1]} performances")


def main():
    print("=" * 60)
    print("Creating plays from performances")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    try:
        create_plays(conn)
    finally:
        conn.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
