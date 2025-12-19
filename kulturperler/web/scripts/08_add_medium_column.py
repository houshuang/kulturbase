#!/usr/bin/env python3
"""
Migration script: Add medium column to episodes and performances tables.

This adds support for distinguishing between TV and radio recordings.
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
    """Add medium column to episodes and performances."""
    cursor = conn.cursor()

    # Step 1: Add medium column to episodes
    print("\n1. Adding medium column to episodes table...")
    try:
        cursor.execute("ALTER TABLE episodes ADD COLUMN medium TEXT DEFAULT 'tv'")
        print("   Added medium column to episodes")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("   medium column already exists in episodes")
        else:
            raise

    # Step 2: Add medium column to performances
    print("\n2. Adding medium column to performances table...")
    try:
        cursor.execute("ALTER TABLE performances ADD COLUMN medium TEXT DEFAULT 'tv'")
        print("   Added medium column to performances")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("   medium column already exists in performances")
        else:
            raise

    # Step 3: Create indexes for medium filtering
    print("\n3. Creating indexes...")
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_episodes_medium ON episodes(medium)")
        print("   Created index on episodes.medium")
    except sqlite3.OperationalError:
        print("   Index already exists")

    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_performances_medium ON performances(medium)")
        print("   Created index on performances.medium")
    except sqlite3.OperationalError:
        print("   Index already exists")

    # Step 4: Set medium based on prf_id prefix or nrk_url
    print("\n4. Detecting medium for existing episodes...")
    cursor.execute("""
        UPDATE episodes SET medium = 'radio'
        WHERE medium = 'tv' AND (
            nrk_url LIKE '%radio.nrk.no%'
            OR prf_id LIKE 'MKRT%'
        )
    """)
    radio_eps = cursor.rowcount
    print(f"   Marked {radio_eps} episodes as radio")

    # Step 5: Update performances medium based on their episodes
    print("\n5. Setting medium for performances based on episodes...")
    cursor.execute("""
        UPDATE performances SET medium = 'radio'
        WHERE medium = 'tv' AND id IN (
            SELECT DISTINCT performance_id FROM episodes
            WHERE medium = 'radio' AND performance_id IS NOT NULL
        )
    """)
    radio_perfs = cursor.rowcount
    print(f"   Marked {radio_perfs} performances as radio")

    conn.commit()

    # Print summary
    print("\n" + "="*60)
    print("MIGRATION SUMMARY")
    print("="*60)

    cursor.execute("SELECT medium, COUNT(*) FROM episodes GROUP BY medium")
    for row in cursor.fetchall():
        print(f"Episodes ({row[0]}): {row[1]}")

    cursor.execute("SELECT medium, COUNT(*) FROM performances GROUP BY medium")
    for row in cursor.fetchall():
        print(f"Performances ({row[0]}): {row[1]}")

    print("\nMigration completed successfully!")


def main():
    print("="*60)
    print("Kulturperler Database Migration")
    print("Adding medium column (tv/radio)")
    print("="*60)

    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

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
