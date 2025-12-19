#!/usr/bin/env python3
"""
Merge multi-part performances into single performances.

Performances like "Peer Gynt 1:2" and "Peer Gynt 2:2" should be merged
into a single "Peer Gynt" performance with multiple episodes.
"""

import sqlite3
import re
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "static" / "kulturperler.db"

# Pattern to match part numbers like "1:2", "2:3", "Del 1", etc.
PART_PATTERNS = [
    r'\s+(\d+):(\d+)$',           # "Title 1:2"
    r'\s+Del\s+(\d+)$',           # "Title Del 1"
    r',\s+del\s+(\d+)$',          # "Title, del 1"
    r'\s+(\d+)/(\d+)$',           # "Title 1/2"
]


def extract_base_title(title: str) -> tuple[str, bool]:
    """Extract base title without part number. Returns (base_title, had_part)."""
    for pattern in PART_PATTERNS:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            base = re.sub(pattern, '', title, flags=re.IGNORECASE).strip()
            return base, True
    return title, False


def merge_performances(conn: sqlite3.Connection):
    cursor = conn.cursor()

    print("1. Finding performances with part numbers...")
    cursor.execute("SELECT id, title, year, medium, work_id FROM performances")
    performances = cursor.fetchall()

    # Group by (base_title, year, medium)
    groups = {}
    for perf_id, title, year, medium, work_id in performances:
        base_title, had_part = extract_base_title(title)
        if had_part:
            key = (base_title, year, medium)
            if key not in groups:
                groups[key] = []
            groups[key].append((perf_id, title, work_id))

    print(f"   Found {len(groups)} groups to merge")

    print("\n2. Merging performances...")
    merged_count = 0
    for (base_title, year, medium), parts in groups.items():
        if len(parts) < 2:
            continue

        print(f"   Merging: {base_title} ({year}, {medium}) - {len(parts)} parts")

        # Sort by title to get parts in order
        parts.sort(key=lambda x: x[1])

        # Keep the first performance as the main one, update its title
        main_perf_id = parts[0][0]
        work_id = parts[0][2]

        # Update the main performance title to the clean base title
        cursor.execute(
            "UPDATE performances SET title = ? WHERE id = ?",
            (base_title, main_perf_id)
        )

        # Move episodes from other parts to the main performance
        for perf_id, title, _ in parts[1:]:
            cursor.execute(
                "UPDATE episodes SET performance_id = ? WHERE performance_id = ?",
                (main_perf_id, perf_id)
            )

            # Move performance_persons
            cursor.execute(
                "INSERT OR IGNORE INTO performance_persons (performance_id, person_id, role, character_name) "
                "SELECT ?, person_id, role, character_name FROM performance_persons WHERE performance_id = ?",
                (main_perf_id, perf_id)
            )
            cursor.execute("DELETE FROM performance_persons WHERE performance_id = ?", (perf_id,))

            # Delete the now-empty performance
            cursor.execute("DELETE FROM performances WHERE id = ?", (perf_id,))

        # Update total_duration for merged performance
        cursor.execute("""
            UPDATE performances SET total_duration = (
                SELECT SUM(duration_seconds) FROM episodes WHERE performance_id = ?
            ) WHERE id = ?
        """, (main_perf_id, main_perf_id))

        merged_count += 1

    conn.commit()
    print(f"   Merged {merged_count} groups")

    print("\n3. Updating plays with clean titles...")
    # Find plays that have part numbers in their titles and update them
    cursor.execute("SELECT id, title FROM plays")
    plays_to_update = []
    for play_id, title in cursor.fetchall():
        base_title, had_part = extract_base_title(title)
        if had_part:
            plays_to_update.append((base_title, play_id))

    for base_title, play_id in plays_to_update:
        # Check if a play with the base title already exists
        cursor.execute("SELECT id FROM plays WHERE title = ?", (base_title,))
        existing = cursor.fetchone()
        if existing:
            # Merge into existing play
            existing_id = existing[0]
            cursor.execute(
                "UPDATE performances SET work_id = ? WHERE work_id = ?",
                (existing_id, play_id)
            )
            cursor.execute(
                "UPDATE episodes SET play_id = ? WHERE play_id = ?",
                (existing_id, play_id)
            )
            cursor.execute("DELETE FROM plays WHERE id = ?", (play_id,))
            print(f"   Merged play '{plays_to_update}' into existing play")
        else:
            # Just update the title
            cursor.execute("UPDATE plays SET title = ? WHERE id = ?", (base_title, play_id))
            print(f"   Updated play title to '{base_title}'")

    conn.commit()

    # Summary
    print("\n4. Summary:")
    cursor.execute("SELECT COUNT(*) FROM performances")
    print(f"   Performances: {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM plays")
    print(f"   Plays: {cursor.fetchone()[0]}")

    # Verify no more part numbers
    cursor.execute("SELECT title FROM performances WHERE title LIKE '%1:2%' OR title LIKE '%2:2%' OR title LIKE '%1:3%'")
    remaining = cursor.fetchall()
    if remaining:
        print(f"   Warning: Still have {len(remaining)} performances with part numbers")
    else:
        print("   All part numbers cleaned up")


def main():
    print("=" * 60)
    print("Merging multi-part performances")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    try:
        merge_performances(conn)
    finally:
        conn.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
