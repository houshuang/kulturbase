#!/usr/bin/env python3
"""
Add Ibsen-related content from Nationaltheatret to Henrik Ibsen person.

This script finds Ibsen-related videos from Nationaltheatret NTV
and attaches them to the Henrik Ibsen person via person_resources.

Usage:
    python add_ibsen_content.py [--db-path PATH] [--dry-run]
"""

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

HENRIK_IBSEN_ID = 879  # Known person_id for Henrik Ibsen


def load_nationaltheatret_videos(data_dir: Path) -> list[dict]:
    """Load Nationaltheatret NTV videos."""
    videos_file = data_dir / "raw" / "nationaltheatret" / "ntv_videos.json"
    if not videos_file.exists():
        print(f"Error: {videos_file} not found")
        return []

    with open(videos_file, "r", encoding="utf-8") as f:
        return json.load(f)


def is_ibsen_related(video: dict) -> bool:
    """Check if video is related to Ibsen."""
    title = video.get("title", "").lower()
    description = video.get("description", "").lower()

    return "ibsen" in title or "ibsen" in description


def add_person_resource(
    conn: sqlite3.Connection,
    person_id: int,
    url: str,
    title: str,
    description: str | None,
    duration_seconds: int | None,
) -> int:
    """Add resource and link to person. Returns resource_id."""
    cursor = conn.cursor()

    # Build description with duration info
    full_desc = description or ""
    if duration_seconds:
        minutes = duration_seconds // 60
        if full_desc:
            full_desc = f"[{minutes} min] {full_desc}"
        else:
            full_desc = f"[{minutes} min]"

    # Insert into external_resources
    cursor.execute("""
        INSERT INTO external_resources (url, title, type, description, added_date)
        VALUES (?, ?, 'related_video', ?, ?)
    """, (url, title, full_desc[:1000] if full_desc else None, datetime.now().isoformat()))

    resource_id = cursor.lastrowid

    # Link to person via person_resources
    cursor.execute("""
        INSERT OR IGNORE INTO person_resources (person_id, resource_id)
        VALUES (?, ?)
    """, (person_id, resource_id))

    return resource_id


def main():
    parser = argparse.ArgumentParser(description="Add Ibsen content from Nationaltheatret")
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
    print("Adding Ibsen-related content from Nationaltheatret")
    if args.dry_run:
        print("(DRY RUN - no changes will be made)")
    print("=" * 60)

    conn = sqlite3.connect(db_path)

    # Verify Henrik Ibsen exists
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM persons WHERE id = ?", (HENRIK_IBSEN_ID,))
    row = cursor.fetchone()
    if not row:
        print(f"Error: Henrik Ibsen (id={HENRIK_IBSEN_ID}) not found in database")
        return
    print(f"Found person: {row[0]} (id={HENRIK_IBSEN_ID})")

    # Load videos
    videos = load_nationaltheatret_videos(data_dir)
    print(f"Loaded {len(videos)} Nationaltheatret videos")

    # Filter for Ibsen-related
    ibsen_videos = [v for v in videos if is_ibsen_related(v)]
    print(f"Found {len(ibsen_videos)} Ibsen-related videos")

    # Check existing links
    cursor.execute("""
        SELECT r.url
        FROM person_resources pr
        JOIN external_resources r ON pr.resource_id = r.id
        WHERE pr.person_id = ?
    """, (HENRIK_IBSEN_ID,))
    existing_urls = {row[0] for row in cursor.fetchall()}

    # Add videos
    added = 0
    skipped = 0

    for video in ibsen_videos:
        url = video.get("url")
        title = video.get("title", "")
        description = video.get("description")
        duration = video.get("duration_seconds")

        if url in existing_urls:
            print(f"  Skipping (already linked): {title[:50]}...")
            skipped += 1
            continue

        print(f"  Adding: {title[:60]}...")

        if not args.dry_run:
            add_person_resource(conn, HENRIK_IBSEN_ID, url, title, description, duration)

        added += 1

    if not args.dry_run:
        conn.commit()

    conn.close()

    print(f"\n{'=' * 60}")
    print("Results:")
    print(f"  Videos added to Henrik Ibsen: {added}")
    print(f"  Already linked (skipped): {skipped}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
