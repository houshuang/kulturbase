#!/usr/bin/env python3
"""
Recreate performances by properly grouping multi-part episodes.

Radio episodes are grouped by their series_id (extracted from nrk_url).
TV episodes are grouped by play_id + year, or individually if no play_id.
"""

import sqlite3
import re
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "static" / "kulturperler.db"


def extract_series_id(nrk_url: str) -> str | None:
    """Extract series ID from NRK radio URL."""
    # https://radio.nrk.no/serie/maaken/mktt54001454 -> maaken
    match = re.search(r'/serie/([^/]+)/', nrk_url)
    if match:
        return match.group(1)
    return None


def migrate(conn: sqlite3.Connection):
    cursor = conn.cursor()

    # Step 1: Drop and recreate performances table
    print("1. Recreating performances table...")
    cursor.execute("DROP TABLE IF EXISTS performance_persons")
    cursor.execute("DROP TABLE IF EXISTS performances")

    cursor.execute("""
        CREATE TABLE performances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_id INTEGER REFERENCES plays(id),
            source TEXT DEFAULT 'nrk',
            year INTEGER,
            title TEXT,
            description TEXT,
            venue TEXT,
            total_duration INTEGER,
            image_url TEXT,
            medium TEXT DEFAULT 'tv',
            series_id TEXT
        )
    """)
    cursor.execute("CREATE INDEX idx_performances_work ON performances(work_id)")
    cursor.execute("CREATE INDEX idx_performances_year ON performances(year)")
    cursor.execute("CREATE INDEX idx_performances_medium ON performances(medium)")
    cursor.execute("CREATE INDEX idx_performances_series ON performances(series_id)")

    # Step 2: Add series_id to episodes if not exists
    print("2. Adding series_id to episodes...")
    try:
        cursor.execute("ALTER TABLE episodes ADD COLUMN series_id TEXT")
    except sqlite3.OperationalError:
        pass  # Already exists

    # Extract and update series_id for radio episodes
    cursor.execute("SELECT prf_id, nrk_url FROM episodes WHERE medium = 'radio'")
    for prf_id, nrk_url in cursor.fetchall():
        series_id = extract_series_id(nrk_url or "")
        if series_id:
            cursor.execute("UPDATE episodes SET series_id = ? WHERE prf_id = ?", (series_id, prf_id))

    conn.commit()
    print("   Updated series_id for radio episodes")

    # Step 3: Create performances for radio (grouped by series_id)
    print("3. Creating radio performances (grouped by series)...")
    cursor.execute("""
        INSERT INTO performances (work_id, source, year, title, description, image_url, total_duration, medium, series_id)
        SELECT
            e.play_id as work_id,
            'nrk' as source,
            MAX(e.year) as year,
            -- Use series title from first episode or clean up series_id
            COALESCE(
                (SELECT e2.title FROM episodes e2 WHERE e2.series_id = e.series_id ORDER BY e2.prf_id LIMIT 1),
                REPLACE(REPLACE(e.series_id, '-', ' '), '_', ' ')
            ) as title,
            (SELECT e2.description FROM episodes e2 WHERE e2.series_id = e.series_id ORDER BY e2.prf_id LIMIT 1) as description,
            (SELECT e2.image_url FROM episodes e2 WHERE e2.series_id = e.series_id AND e2.image_url IS NOT NULL ORDER BY e2.prf_id LIMIT 1) as image_url,
            SUM(e.duration_seconds) as total_duration,
            'radio' as medium,
            e.series_id
        FROM episodes e
        WHERE e.medium = 'radio' AND e.series_id IS NOT NULL
        GROUP BY e.series_id
    """)
    radio_count = cursor.rowcount
    print(f"   Created {radio_count} radio performances")

    # Step 4: Create performances for TV (grouped by play_id + year, or individual)
    print("4. Creating TV performances...")
    # TV with play_id - group by play_id + year
    cursor.execute("""
        INSERT INTO performances (work_id, source, year, title, description, image_url, total_duration, medium)
        SELECT
            e.play_id as work_id,
            'nrk' as source,
            e.year,
            COALESCE(p.title, e.title) as title,
            (SELECT e2.description FROM episodes e2 WHERE e2.play_id = e.play_id AND e2.year = e.year ORDER BY e2.prf_id LIMIT 1) as description,
            (SELECT e2.image_url FROM episodes e2 WHERE e2.play_id = e.play_id AND e2.year = e.year AND e2.image_url IS NOT NULL ORDER BY e2.prf_id LIMIT 1) as image_url,
            SUM(e.duration_seconds) as total_duration,
            'tv' as medium
        FROM episodes e
        LEFT JOIN plays p ON e.play_id = p.id
        WHERE e.medium = 'tv' AND e.play_id IS NOT NULL
        GROUP BY e.play_id, e.year
    """)
    tv_grouped = cursor.rowcount
    print(f"   Created {tv_grouped} TV performances (grouped by play+year)")

    # TV without play_id - individual performances
    cursor.execute("""
        INSERT INTO performances (work_id, source, year, title, description, image_url, total_duration, medium)
        SELECT
            NULL as work_id,
            'nrk' as source,
            e.year,
            e.title,
            e.description,
            e.image_url,
            e.duration_seconds as total_duration,
            'tv' as medium
        FROM episodes e
        WHERE e.medium = 'tv' AND e.play_id IS NULL
    """)
    tv_individual = cursor.rowcount
    print(f"   Created {tv_individual} TV performances (individual)")

    # Step 5: Link episodes to performances
    print("5. Linking episodes to performances...")

    # Reset performance_id
    cursor.execute("UPDATE episodes SET performance_id = NULL")

    # Link radio episodes by series_id
    cursor.execute("""
        UPDATE episodes SET performance_id = (
            SELECT p.id FROM performances p
            WHERE p.series_id = episodes.series_id
            AND p.medium = 'radio'
            LIMIT 1
        )
        WHERE medium = 'radio' AND series_id IS NOT NULL
    """)
    print(f"   Linked {cursor.rowcount} radio episodes")

    # Link TV episodes with play_id
    cursor.execute("""
        UPDATE episodes SET performance_id = (
            SELECT p.id FROM performances p
            WHERE p.work_id = episodes.play_id
            AND p.year = episodes.year
            AND p.medium = 'tv'
            LIMIT 1
        )
        WHERE medium = 'tv' AND play_id IS NOT NULL
    """)
    print(f"   Linked {cursor.rowcount} TV episodes (with play_id)")

    # Link TV episodes without play_id
    cursor.execute("""
        UPDATE episodes SET performance_id = (
            SELECT p.id FROM performances p
            WHERE p.work_id IS NULL
            AND p.title = episodes.title
            AND p.year = episodes.year
            AND p.medium = 'tv'
            LIMIT 1
        )
        WHERE medium = 'tv' AND play_id IS NULL AND performance_id IS NULL
    """)
    print(f"   Linked {cursor.rowcount} TV episodes (without play_id)")

    # Step 6: Create performance_persons
    print("6. Creating performance_persons...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS performance_persons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            performance_id INTEGER NOT NULL REFERENCES performances(id),
            person_id INTEGER NOT NULL REFERENCES persons(id),
            role TEXT,
            character_name TEXT,
            UNIQUE(performance_id, person_id, role, character_name)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_performance_persons_perf ON performance_persons(performance_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_performance_persons_person ON performance_persons(person_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_performance_persons_role ON performance_persons(role)")

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
    """)
    print(f"   Created {cursor.rowcount} performance_persons records")

    conn.commit()

    # Step 7: Summary
    print("\n7. Summary:")
    cursor.execute("SELECT medium, COUNT(*) FROM performances GROUP BY medium")
    for row in cursor.fetchall():
        print(f"   {row[0]}: {row[1]} performances")

    cursor.execute("SELECT COUNT(*) FROM episodes WHERE performance_id IS NULL")
    unlinked = cursor.fetchone()[0]
    if unlinked > 0:
        print(f"   WARNING: {unlinked} episodes not linked")

    # Show some multi-part examples
    print("\n   Multi-part performances:")
    cursor.execute("""
        SELECT p.title, p.medium, COUNT(e.prf_id) as parts
        FROM performances p
        JOIN episodes e ON e.performance_id = p.id
        GROUP BY p.id
        HAVING parts > 1
        ORDER BY parts DESC
        LIMIT 5
    """)
    for row in cursor.fetchall():
        print(f"      {row[0]} ({row[1]}): {row[2]} parts")


def main():
    print("=" * 60)
    print("Grouping performances by series")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    try:
        migrate(conn)
    finally:
        conn.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
