#!/usr/bin/env python3
"""
Create performances from episodes with proper medium support.

This script creates the performances table from episodes and properly
sets the medium (tv/radio) based on the episode data.
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
    """Run the migration."""
    cursor = conn.cursor()

    # Step 1: Create performances table with medium column
    print("\n1. Creating performances table...")
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
            medium TEXT DEFAULT 'tv'
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_performances_work ON performances(work_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_performances_year ON performances(year)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_performances_medium ON performances(medium)")
    print("   Created performances table")

    # Step 2: Populate performances from episodes
    # Create one performance per episode since we don't have part grouping
    print("\n2. Populating performances from episodes...")

    cursor.execute("""
        INSERT INTO performances (work_id, source, year, title, description, image_url, total_duration, medium)
        SELECT
            e.play_id as work_id,
            'nrk' as source,
            e.year,
            e.title,
            e.description,
            e.image_url,
            e.duration_seconds as total_duration,
            e.medium
        FROM episodes e
    """)
    count = cursor.rowcount
    print(f"   Created {count} performances from episodes")

    # Step 3: Add performance_id to episodes
    print("\n3. Adding performance_id to episodes...")
    try:
        cursor.execute("ALTER TABLE episodes ADD COLUMN performance_id INTEGER REFERENCES performances(id)")
        print("   Added performance_id column")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("   performance_id column already exists")
        else:
            raise

    # Link episodes to performances - match by prf_id through title/year/description
    cursor.execute("""
        UPDATE episodes SET performance_id = (
            SELECT p.id FROM performances p
            WHERE p.title = episodes.title
            AND (p.year = episodes.year OR (p.year IS NULL AND episodes.year IS NULL))
            AND p.medium = episodes.medium
            LIMIT 1
        )
    """)
    print(f"   Linked {cursor.rowcount} episodes to performances")

    # Step 4: Create performance_persons from episode_persons
    print("\n4. Creating performance_persons table...")
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

    # Step 5: Verify data integrity
    print("\n5. Verifying data integrity...")

    cursor.execute("SELECT medium, COUNT(*) FROM performances GROUP BY medium")
    for row in cursor.fetchall():
        print(f"   {row[0]}: {row[1]} performances")

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

    conn.commit()
    print("\nMigration completed successfully!")


def main():
    print("="*60)
    print("Kulturperler - Create Performances with Medium Support")
    print("="*60)

    # Backup first
    backup_database()

    # Run migration
    conn = sqlite3.connect(DB_PATH)
    try:
        migrate(conn)
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
