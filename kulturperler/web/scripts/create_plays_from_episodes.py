#!/usr/bin/env python3
"""
Create play entries for episode series that don't have play_id set.
Identifies series by shared image_url.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'static', 'kulturperler.db')

# Series to create plays for (image_url -> play title)
SERIES_TO_CREATE = {
    'https://gfx.nrk.no/GDrlhznMp56TG4uMQF2XkQdDHXuvlFvDSphpqr9G9Cxw': 'Philip Odell',
    'https://gfx.nrk.no/RRLGBb0EIh1T-hzLxPnL2gN1iGUOIKIT1yxQyoW3fRzw': 'Treholt-saken',
    'https://gfx.nrk.no/LFNYFDTHd0fmpnHQBUkMuw9OdtsPjjX2JbLa4zCqvvHA': 'Drept natt til tirsdag',
    'https://gfx.nrk.no/AVYfrLOj3KOCB5mTNvBnrQntP-zY3b-n7C_6mYrswUhA': 'Furubotn-gruppen',
}

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    for image_url, play_title in SERIES_TO_CREATE.items():
        print(f"\n=== Processing: {play_title} ===")

        # Get episodes for this series
        cur.execute("""
            SELECT prf_id, title, year, description
            FROM episodes
            WHERE image_url = ? AND play_id IS NULL
            ORDER BY prf_id
        """, (image_url,))
        episodes = cur.fetchall()

        if not episodes:
            print(f"  No episodes found (may already have play_id)")
            continue

        print(f"  Found {len(episodes)} episodes")

        # Get playwright from episode_persons
        cur.execute("""
            SELECT DISTINCT p.id, p.name
            FROM episode_persons ep
            JOIN persons p ON ep.person_id = p.id
            WHERE ep.role = 'playwright'
            AND ep.episode_id IN (
                SELECT prf_id FROM episodes WHERE image_url = ?
            )
        """, (image_url,))
        playwrights = cur.fetchall()

        playwright_id = None
        if playwrights:
            playwright_id = playwrights[0]['id']
            print(f"  Playwright: {playwrights[0]['name']} (id={playwright_id})")

        # Get year from first episode
        year = episodes[0]['year']

        # Create the play
        cur.execute("""
            INSERT INTO plays (title, playwright_id, year_written)
            VALUES (?, ?, ?)
        """, (play_title, playwright_id, year))
        play_id = cur.lastrowid
        print(f"  Created play with id={play_id}")

        # Update episodes with play_id
        episode_ids = [ep['prf_id'] for ep in episodes]
        placeholders = ','.join('?' * len(episode_ids))
        cur.execute(f"""
            UPDATE episodes SET play_id = ? WHERE prf_id IN ({placeholders})
        """, [play_id] + episode_ids)
        print(f"  Updated {cur.rowcount} episodes with play_id={play_id}")

        # List episodes
        for ep in episodes:
            print(f"    - {ep['title']}")

    conn.commit()
    conn.close()
    print("\n✓ Done!")

if __name__ == '__main__':
    main()
