#!/usr/bin/env python3
"""
Remove about_person_id from episodes whose performance already has about_person_id.
This avoids showing 70+ individual episodes on an author's page when the performance
itself represents the collective work.
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "static" / "kulturperler.db"
EPISODES_DIR = BASE_DIR / "data" / "episodes"


def main():
    conn = sqlite3.connect(DB_PATH)

    # Find episodes that belong to performances with about_person_id
    query = """
        SELECT e.prf_id, p.title as perf_title
        FROM episodes e
        JOIN performances p ON e.performance_id = p.id
        WHERE p.about_person_id IS NOT NULL
        AND e.about_person_id IS NOT NULL
    """

    episodes = conn.execute(query).fetchall()
    conn.close()

    print(f"Found {len(episodes)} episodes with redundant about_person_id")

    removed = 0
    for prf_id, perf_title in episodes:
        yaml_path = EPISODES_DIR / f"{prf_id}.yaml"
        if not yaml_path.exists():
            continue

        content = yaml_path.read_text(encoding='utf-8')

        # Remove about_person_id line
        lines = content.split('\n')
        new_lines = [line for line in lines if not line.startswith('about_person_id:')]

        if len(new_lines) < len(lines):
            yaml_path.write_text('\n'.join(new_lines), encoding='utf-8')
            removed += 1

    print(f"Removed about_person_id from {removed} episode files")
    print(f"\nThese episodes now inherit their author from the performance level:")

    # Show which performances this affects
    conn = sqlite3.connect(DB_PATH)
    perfs = conn.execute("""
        SELECT p.title, per.name, COUNT(*) as ep_count
        FROM performances p
        JOIN persons per ON p.about_person_id = per.id
        JOIN episodes e ON e.performance_id = p.id
        WHERE p.about_person_id IS NOT NULL
        GROUP BY p.id
    """).fetchall()
    conn.close()

    for title, author, count in perfs:
        print(f"  - {title} ({author}): {count} episodes")


if __name__ == "__main__":
    main()
