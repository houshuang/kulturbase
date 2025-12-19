#!/usr/bin/env python3
"""
Fix duplicate persons and merge them.
"""

import sqlite3

DB_PATH = "/Users/stian/src/nrk/kulturperler/web/static/kulturperler.db"

def merge_persons(conn, keep_id, remove_id, name):
    """Merge two person records into one."""
    cursor = conn.cursor()

    print(f"\nMerging {name}:")
    print(f"  Keeping: id={keep_id}")
    print(f"  Removing: id={remove_id}")

    # Update all episode_persons references
    cursor.execute("""
        UPDATE episode_persons
        SET person_id = ?
        WHERE person_id = ?
    """, (keep_id, remove_id))
    updated_episodes = cursor.rowcount
    print(f"  Updated {updated_episodes} episode_persons records")

    # Update all plays references
    cursor.execute("""
        UPDATE plays
        SET playwright_id = ?
        WHERE playwright_id = ?
    """, (keep_id, remove_id))
    updated_plays = cursor.rowcount
    print(f"  Updated {updated_plays} plays records")

    # Delete the duplicate person
    cursor.execute("DELETE FROM persons WHERE id = ?", (remove_id,))
    print(f"  Deleted person id={remove_id}")

    conn.commit()
    print(f"  ✓ Merge complete")

def delete_orphaned_person(conn, person_id, name):
    """Delete an orphaned person."""
    cursor = conn.cursor()

    print(f"Deleting orphaned person: {name} (id={person_id})")
    cursor.execute("DELETE FROM persons WHERE id = ?", (person_id,))
    conn.commit()
    print(f"  ✓ Deleted")

def main():
    print("Kulturperler Database - Fix Duplicates")
    print("=" * 50)

    conn = sqlite3.connect(DB_PATH)

    try:
        # Merge Bertolt Brecht: keep 3094 (5 plays), remove 3210 (1 play)
        merge_persons(conn, 3094, 3210, "Bertolt Brecht")

        # Merge Åsmund Feidje: keep 775 (76 episodes), remove 2703 (4 episodes)
        merge_persons(conn, 775, 2703, "Åsmund Feidje")

        # Delete orphaned Lars Norén duplicates (both have no episodes or plays)
        # Keep 3117 as it was first, delete 3134
        delete_orphaned_person(conn, 3134, "Lars Norén (duplicate)")

        print("\n" + "=" * 50)
        print("✓ All duplicates fixed!")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
