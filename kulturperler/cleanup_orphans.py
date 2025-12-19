#!/usr/bin/env python3
"""
Clean up orphaned persons from the database.
"""

import sqlite3

DB_PATH = "/Users/stian/src/nrk/kulturperler/web/static/kulturperler.db"

def cleanup_orphans(conn):
    """Delete orphaned persons."""
    cursor = conn.cursor()

    # Get orphaned persons
    cursor.execute("""
        SELECT id, name
        FROM persons
        WHERE id NOT IN (SELECT DISTINCT person_id FROM episode_persons)
        AND id NOT IN (SELECT DISTINCT playwright_id FROM plays WHERE playwright_id IS NOT NULL)
        ORDER BY name
    """)

    orphans = cursor.fetchall()
    print(f"Found {len(orphans)} orphaned persons\n")

    if len(orphans) == 0:
        print("No orphans to clean up!")
        return

    print("Orphaned persons to be deleted:")
    for person_id, name in orphans:
        print(f"  - {name} (id={person_id})")

    # Delete them
    cursor.execute("""
        DELETE FROM persons
        WHERE id NOT IN (SELECT DISTINCT person_id FROM episode_persons)
        AND id NOT IN (SELECT DISTINCT playwright_id FROM plays WHERE playwright_id IS NOT NULL)
    """)

    deleted_count = cursor.rowcount
    conn.commit()

    print(f"\n✓ Deleted {deleted_count} orphaned persons")

def main():
    print("Kulturperler Database - Cleanup Orphaned Persons")
    print("=" * 50)

    conn = sqlite3.connect(DB_PATH)

    try:
        cleanup_orphans(conn)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
