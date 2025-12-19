#!/usr/bin/env python3
"""
Add Archive.org URLs as fallback links to existing NRK episodes.

This script matches Archive.org items to existing episodes by NRK program ID
and adds them as fallback resources via the episode_resources table.

Usage:
    python add_archive_fallbacks.py [--db-path PATH] [--dry-run]
"""

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path


def load_existing_episodes(conn: sqlite3.Connection) -> dict[str, str]:
    """Load existing episodes from database. Returns prf_id -> title mapping."""
    cursor = conn.cursor()
    cursor.execute("SELECT prf_id, title FROM episodes")
    return {row[0].upper(): row[1] for row in cursor.fetchall()}


def load_archive_items(data_dir: Path) -> list[dict]:
    """Load harvested Archive.org items."""
    items_file = data_dir / "raw" / "internet_archive" / "items.json"
    if not items_file.exists():
        print(f"Error: {items_file} not found")
        return []

    with open(items_file, "r", encoding="utf-8") as f:
        return json.load(f)


def add_fallback_link(
    conn: sqlite3.Connection,
    episode_prf_id: str,
    archive_url: str,
    title: str,
    description: str | None,
) -> int:
    """Add Archive.org as fallback link for an episode. Returns resource_id."""
    cursor = conn.cursor()

    # Insert into external_resources
    cursor.execute("""
        INSERT INTO external_resources (url, title, type, description, added_date)
        VALUES (?, ?, 'archive_fallback', ?, ?)
    """, (archive_url, title, description, datetime.now().isoformat()))

    resource_id = cursor.lastrowid

    # Link to episode via episode_resources
    cursor.execute("""
        INSERT OR IGNORE INTO episode_resources (episode_id, resource_id)
        VALUES (?, ?)
    """, (episode_prf_id, resource_id))

    return resource_id


def main():
    parser = argparse.ArgumentParser(description="Add Archive.org fallback links")
    parser.add_argument(
        "--db-path",
        type=str,
        default="web/static/kulturperler.db",
        help="Path to database",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data",
        help="Data directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually modify database",
    )

    args = parser.parse_args()

    script_dir = Path(__file__).parent.parent
    db_path = script_dir / args.db_path
    data_dir = script_dir / args.data_dir

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return

    print("=" * 60)
    print("Adding Archive.org fallback links")
    if args.dry_run:
        print("(DRY RUN - no changes will be made)")
    print("=" * 60)

    conn = sqlite3.connect(db_path)

    # Load existing episodes
    existing_episodes = load_existing_episodes(conn)
    print(f"Loaded {len(existing_episodes)} existing episodes")

    # Load Archive.org items
    archive_items = load_archive_items(data_dir)
    print(f"Loaded {len(archive_items)} Archive.org items")

    # Match and add fallbacks
    matched = 0
    unmatched = []
    already_has_link = 0

    # Check existing fallback links
    cursor = conn.cursor()
    cursor.execute("""
        SELECT er.episode_id, r.url
        FROM episode_resources er
        JOIN external_resources r ON er.resource_id = r.id
        WHERE r.type = 'archive_fallback'
    """)
    existing_links = {(row[0], row[1]) for row in cursor.fetchall()}

    for item in archive_items:
        nrk_prf_id = item.get("nrk_prf_id")
        archive_url = item.get("url")
        title = item.get("title", "")
        description = item.get("description")

        if not nrk_prf_id:
            unmatched.append(item)
            continue

        # Check if episode exists (case-insensitive match)
        prf_id_upper = nrk_prf_id.upper()
        matched_prf_id = None

        if prf_id_upper in existing_episodes:
            matched_prf_id = prf_id_upper
        else:
            # Try to find case-insensitive match
            for ep_id in existing_episodes:
                if ep_id.upper() == prf_id_upper:
                    matched_prf_id = ep_id
                    break

        if not matched_prf_id:
            unmatched.append(item)
            continue

        # Check if link already exists
        if (matched_prf_id, archive_url) in existing_links:
            already_has_link += 1
            continue

        # Add fallback link
        if not args.dry_run:
            add_fallback_link(conn, matched_prf_id, archive_url, title, description)

        matched += 1

    if not args.dry_run:
        conn.commit()

    conn.close()

    print(f"\n{'=' * 60}")
    print("Results:")
    print(f"  Fallback links added: {matched}")
    print(f"  Already had link: {already_has_link}")
    print(f"  Unmatched (no episode): {len(unmatched)}")
    print(f"{'=' * 60}")

    # Save unmatched for review
    if unmatched:
        unmatched_file = data_dir / "archive_unmatched.json"
        with open(unmatched_file, "w", encoding="utf-8") as f:
            json.dump(unmatched, f, ensure_ascii=False, indent=2)
        print(f"\nUnmatched items saved to: {unmatched_file}")


if __name__ == "__main__":
    main()
