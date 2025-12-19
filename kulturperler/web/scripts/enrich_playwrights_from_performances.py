#!/usr/bin/env python3
"""
Enrich plays with playwright information from performance_persons table.

For each play without a playwright_id, finds performances of that play,
looks up playwright entries in performance_persons, and links the most
common playwright to the play.
"""

import sqlite3
from collections import Counter

DB_PATH = '../static/kulturperler.db'

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get all plays without playwright
    cur.execute("""
        SELECT id, title FROM plays WHERE playwright_id IS NULL
    """)
    plays_without_playwright = cur.fetchall()
    print(f"Found {len(plays_without_playwright)} plays without playwright")

    updated = 0
    skipped = 0

    for play in plays_without_playwright:
        play_id = play['id']
        play_title = play['title']

        # Find performances of this play
        cur.execute("""
            SELECT id FROM performances WHERE work_id = ?
        """, (play_id,))
        performances = cur.fetchall()

        if not performances:
            skipped += 1
            continue

        # Get all playwrights from these performances
        performance_ids = [p['id'] for p in performances]
        placeholders = ','.join('?' * len(performance_ids))

        cur.execute(f"""
            SELECT pp.person_id, p.name
            FROM performance_persons pp
            JOIN persons p ON pp.person_id = p.id
            WHERE pp.performance_id IN ({placeholders})
            AND pp.role = 'playwright'
        """, performance_ids)

        playwrights = cur.fetchall()

        if not playwrights:
            skipped += 1
            continue

        # Find most common playwright
        playwright_counts = Counter(pw['person_id'] for pw in playwrights)
        most_common_id, count = playwright_counts.most_common(1)[0]
        playwright_name = next(pw['name'] for pw in playwrights if pw['person_id'] == most_common_id)

        # Update the play
        cur.execute("""
            UPDATE plays SET playwright_id = ? WHERE id = ?
        """, (most_common_id, play_id))

        print(f"  {play_title} -> {playwright_name}")
        updated += 1

    conn.commit()
    conn.close()

    print(f"\nDone! Updated {updated} plays, skipped {skipped} (no performances or no playwright info)")

if __name__ == '__main__':
    main()
