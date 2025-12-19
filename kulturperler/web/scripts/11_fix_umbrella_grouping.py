#!/usr/bin/env python3
"""
Fix grouping for umbrella series like 'radioteatret'.

Umbrella series contain standalone productions that shouldn't be grouped together.
Each episode in an umbrella series becomes its own performance.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "static" / "kulturperler.db"

# Umbrella series where each episode is a standalone production
UMBRELLA_SERIES = {'radioteatret'}


def fix_grouping(conn: sqlite3.Connection):
    cursor = conn.cursor()

    # Step 1: Find the umbrella performance(s) that need to be split
    print("1. Finding umbrella performances to split...")
    cursor.execute("""
        SELECT p.id, p.title, p.series_id, COUNT(e.prf_id) as ep_count
        FROM performances p
        JOIN episodes e ON e.performance_id = p.id
        WHERE p.series_id IN ({})
        GROUP BY p.id
    """.format(','.join('?' * len(UMBRELLA_SERIES))), tuple(UMBRELLA_SERIES))

    umbrella_perfs = cursor.fetchall()
    print(f"   Found {len(umbrella_perfs)} umbrella performances to split")

    for perf_id, title, series_id, ep_count in umbrella_perfs:
        print(f"   - {title} ({series_id}): {ep_count} episodes to split")

    # Step 2: For each episode in umbrella series, create individual performance
    print("\n2. Creating individual performances for umbrella episodes...")

    cursor.execute("""
        SELECT e.prf_id, e.title, e.description, e.year, e.duration_seconds,
               e.image_url, e.play_id, e.medium, e.series_id
        FROM episodes e
        WHERE e.series_id IN ({})
    """.format(','.join('?' * len(UMBRELLA_SERIES))), tuple(UMBRELLA_SERIES))

    umbrella_episodes = cursor.fetchall()

    for ep in umbrella_episodes:
        prf_id, title, description, year, duration, image_url, play_id, medium, series_id = ep

        # Create a new performance for this episode
        cursor.execute("""
            INSERT INTO performances (work_id, source, year, title, description,
                                     image_url, total_duration, medium, series_id)
            VALUES (?, 'nrk', ?, ?, ?, ?, ?, ?, ?)
        """, (play_id, year, title, description, image_url, duration, medium, f"{series_id}_{prf_id}"))

        new_perf_id = cursor.lastrowid

        # Update episode to point to new performance
        cursor.execute("UPDATE episodes SET performance_id = ? WHERE prf_id = ?",
                      (new_perf_id, prf_id))

    print(f"   Created {len(umbrella_episodes)} individual performances")

    # Step 3: Delete old umbrella performances (now orphaned)
    print("\n3. Deleting orphaned umbrella performances...")
    cursor.execute("""
        DELETE FROM performance_persons WHERE performance_id IN (
            SELECT p.id FROM performances p
            WHERE NOT EXISTS (SELECT 1 FROM episodes e WHERE e.performance_id = p.id)
        )
    """)

    cursor.execute("""
        DELETE FROM performances WHERE id IN (
            SELECT p.id FROM performances p
            WHERE NOT EXISTS (SELECT 1 FROM episodes e WHERE e.performance_id = p.id)
        )
    """)
    print(f"   Deleted {cursor.rowcount} orphaned performances")

    # Step 4: Recreate performance_persons for new performances
    print("\n4. Recreating performance_persons...")
    cursor.execute("""
        INSERT OR IGNORE INTO performance_persons (performance_id, person_id, role, character_name)
        SELECT DISTINCT
            e.performance_id,
            ep.person_id,
            ep.role,
            ep.character_name
        FROM episode_persons ep
        JOIN episodes e ON ep.episode_id = e.prf_id
        WHERE e.performance_id IS NOT NULL
        AND NOT EXISTS (
            SELECT 1 FROM performance_persons pp
            WHERE pp.performance_id = e.performance_id
            AND pp.person_id = ep.person_id
        )
    """)
    print(f"   Added {cursor.rowcount} performance_persons records")

    conn.commit()

    # Summary
    print("\n5. Summary:")
    cursor.execute("SELECT medium, COUNT(*) FROM performances GROUP BY medium")
    for row in cursor.fetchall():
        print(f"   {row[0]}: {row[1]} performances")


def main():
    print("=" * 60)
    print("Fixing umbrella series grouping")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    try:
        fix_grouping(conn)
    finally:
        conn.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
