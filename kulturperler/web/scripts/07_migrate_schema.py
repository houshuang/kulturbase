#!/usr/bin/env python3
"""
Migration script: Episodes → Performances + Media schema

This script migrates the database from the old schema:
  plays → episodes → episode_persons

To the new schema:
  works → performances → media + performance_persons

All existing data is preserved.
"""

import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "static" / "kulturperler.db"
BACKUP_PATH = DB_PATH.with_suffix(f".db.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")


def backup_database():
    """Create a backup before migration."""
    print(f"Creating backup: {BACKUP_PATH}")
    shutil.copy(DB_PATH, BACKUP_PATH)
    print("Backup created successfully")


def migrate(conn: sqlite3.Connection):
    """Run the full migration."""
    cursor = conn.cursor()

    # Step 1: Add work_type and synopsis to plays (will become works)
    print("\n1. Adding columns to plays table...")
    try:
        cursor.execute("ALTER TABLE plays ADD COLUMN work_type TEXT DEFAULT 'play'")
        print("   Added work_type column")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("   work_type column already exists")
        else:
            raise

    try:
        cursor.execute("ALTER TABLE plays ADD COLUMN synopsis TEXT")
        print("   Added synopsis column")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("   synopsis column already exists")
        else:
            raise

    # Step 2: Create performances table
    print("\n2. Creating performances table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS performances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_id INTEGER REFERENCES plays(id),
            source TEXT DEFAULT 'nrk',
            year INTEGER,
            title TEXT,
            description TEXT,
            venue TEXT,
            total_duration INTEGER,
            image_url TEXT,
            UNIQUE(work_id, year, source)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_performances_work ON performances(work_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_performances_year ON performances(year)")
    print("   Created performances table")

    # Step 3: Populate performances from episodes
    # Group by (play_id, year) for episodes with play_id
    print("\n3. Populating performances from episodes...")

    # First, episodes with play_id - group by (play_id, year)
    cursor.execute("""
        INSERT OR IGNORE INTO performances (work_id, source, year, title, description, image_url, total_duration)
        SELECT
            e.play_id as work_id,
            'nrk' as source,
            e.year,
            COALESCE(p.title, e.title) as title,
            -- Use first episode's description
            (SELECT e2.description FROM episodes e2
             WHERE e2.play_id = e.play_id AND e2.year = e.year
             ORDER BY e2.part_number ASC NULLS LAST, e2.prf_id LIMIT 1) as description,
            -- Use first episode's image
            (SELECT e2.image_url FROM episodes e2
             WHERE e2.play_id = e.play_id AND e2.year = e.year
             ORDER BY e2.part_number ASC NULLS LAST, e2.prf_id LIMIT 1) as image_url,
            -- Sum of all parts' duration
            SUM(e.duration_seconds) as total_duration
        FROM episodes e
        LEFT JOIN plays p ON e.play_id = p.id
        WHERE e.play_id IS NOT NULL
        GROUP BY e.play_id, e.year
    """)
    with_work = cursor.rowcount
    print(f"   Created {with_work} performances from matched episodes")

    # Then, orphan episodes (no play_id) - each gets its own performance
    cursor.execute("""
        INSERT OR IGNORE INTO performances (work_id, source, year, title, description, image_url, total_duration)
        SELECT
            NULL as work_id,
            'nrk' as source,
            e.year,
            e.title,
            e.description,
            e.image_url,
            e.duration_seconds as total_duration
        FROM episodes e
        WHERE e.play_id IS NULL
    """)
    orphans = cursor.rowcount
    print(f"   Created {orphans} performances from orphan episodes")

    # Step 4: Add performance_id to episodes
    print("\n4. Adding performance_id to episodes...")
    try:
        cursor.execute("ALTER TABLE episodes ADD COLUMN performance_id INTEGER REFERENCES performances(id)")
        print("   Added performance_id column")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("   performance_id column already exists")
        else:
            raise

    # Link episodes with play_id to their performance
    cursor.execute("""
        UPDATE episodes SET performance_id = (
            SELECT p.id FROM performances p
            WHERE p.work_id = episodes.play_id
            AND p.year = episodes.year
            AND p.source = 'nrk'
        )
        WHERE play_id IS NOT NULL
    """)
    print(f"   Linked {cursor.rowcount} episodes with play to performances")

    # Link orphan episodes to their performance (matched by title, year, description)
    cursor.execute("""
        UPDATE episodes SET performance_id = (
            SELECT p.id FROM performances p
            WHERE p.work_id IS NULL
            AND p.title = episodes.title
            AND p.year = episodes.year
            AND p.source = 'nrk'
        )
        WHERE play_id IS NULL
    """)
    print(f"   Linked {cursor.rowcount} orphan episodes to performances")

    # Step 5: Create performance_persons from episode_persons
    print("\n5. Creating performance_persons table...")
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

    # Migrate distinct person-roles per performance
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
    print(f"   Migrated {cursor.rowcount} person-role records to performance_persons")

    # Step 6: Add media_type column to episodes
    print("\n6. Adding media_type to episodes...")
    try:
        cursor.execute("ALTER TABLE episodes ADD COLUMN media_type TEXT DEFAULT 'episode'")
        print("   Added media_type column")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("   media_type column already exists")
        else:
            raise

    # Set media_type based on existing data
    cursor.execute("""
        UPDATE episodes SET media_type = CASE
            WHEN is_introduction = 1 THEN 'intro'
            WHEN part_number IS NOT NULL THEN 'part'
            ELSE 'episode'
        END
    """)
    print(f"   Set media_type for {cursor.rowcount} episodes")

    # Step 7: Verify data integrity
    print("\n7. Verifying data integrity...")

    cursor.execute("SELECT COUNT(*) FROM performances")
    perf_count = cursor.fetchone()[0]
    print(f"   Performances: {perf_count}")

    cursor.execute("SELECT COUNT(*) FROM episodes WHERE performance_id IS NOT NULL")
    linked = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM episodes")
    total = cursor.fetchone()[0]
    print(f"   Episodes linked to performances: {linked}/{total}")

    cursor.execute("SELECT COUNT(*) FROM performance_persons")
    pp_count = cursor.fetchone()[0]
    print(f"   Performance_persons records: {pp_count}")

    # Check for unlinked episodes
    cursor.execute("SELECT COUNT(*) FROM episodes WHERE performance_id IS NULL")
    unlinked = cursor.fetchone()[0]
    if unlinked > 0:
        print(f"   WARNING: {unlinked} episodes not linked to any performance")
        cursor.execute("""
            SELECT prf_id, title, year FROM episodes
            WHERE performance_id IS NULL LIMIT 5
        """)
        for row in cursor.fetchall():
            print(f"      - {row[0]}: {row[1]} ({row[2]})")

    conn.commit()
    print("\nMigration completed successfully!")


def print_summary(conn: sqlite3.Connection):
    """Print a summary of the migrated database."""
    cursor = conn.cursor()

    print("\n" + "="*60)
    print("MIGRATION SUMMARY")
    print("="*60)

    cursor.execute("SELECT COUNT(*) FROM plays")
    print(f"Works (plays): {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM performances")
    print(f"Performances: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM episodes")
    print(f"Media (episodes): {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM persons")
    print(f"Persons: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM performance_persons")
    print(f"Performance-Persons: {cursor.fetchone()[0]}")

    # Show some stats about the migration
    print("\nPerformance distribution:")
    cursor.execute("""
        SELECT
            CASE WHEN work_id IS NOT NULL THEN 'With work' ELSE 'Without work' END as type,
            COUNT(*) as count
        FROM performances
        GROUP BY type
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")

    print("\nMulti-part performances:")
    cursor.execute("""
        SELECT p.id, p.title, p.year, COUNT(e.prf_id) as parts
        FROM performances p
        JOIN episodes e ON e.performance_id = p.id
        GROUP BY p.id
        HAVING parts > 1
        ORDER BY parts DESC
        LIMIT 5
    """)
    for row in cursor.fetchall():
        print(f"  {row[1]} ({row[2]}): {row[3]} parts")


def main():
    print("="*60)
    print("Kulturperler Database Migration")
    print("Episodes → Performances + Media schema")
    print("="*60)

    # Backup first
    backup_database()

    # Run migration
    conn = sqlite3.connect(DB_PATH)
    try:
        migrate(conn)
        print_summary(conn)
    except Exception as e:
        print(f"\nERROR: Migration failed: {e}")
        print(f"Restoring from backup: {BACKUP_PATH}")
        conn.close()
        shutil.copy(BACKUP_PATH, DB_PATH)
        raise
    finally:
        conn.close()

    print(f"\nBackup saved at: {BACKUP_PATH}")
    print("Migration complete!")


if __name__ == "__main__":
    main()
