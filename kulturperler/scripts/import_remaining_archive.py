#!/usr/bin/env python3
"""
Import remaining unmatched Archive.org items:
1. Multi-part recordings → add as fallbacks to existing episodes
2. Tramteatret content → import as new episodes

Usage:
    python import_remaining_archive.py [--db-path PATH] [--dry-run]
"""

import argparse
import re
import sqlite3
from datetime import datetime
from pathlib import Path


def normalize_prf_id_for_parts(prf_id: str) -> str | None:
    """
    Normalize a multi-part prf_id to the base episode id.
    FTEA00015883 (part 1) → FTEA00005883
    FTEA00025883 (part 2) → FTEA00005883
    FUHA03010086 (part 1) → FUHA03000086
    """
    if not prf_id:
        return None

    # Pattern: FTEA000XNNNN where X is part number (1,2,3)
    # Convert to FTEA0000NNNN
    match = re.match(r'^(FTEA)000([123])(\d{4})$', prf_id)
    if match:
        return f"{match.group(1)}0000{match.group(3)}"

    # Pattern: FUHA030X0086 where X is part number
    match = re.match(r'^(FUHA)030([123])(\d{4})$', prf_id)
    if match:
        return f"{match.group(1)}0300{match.group(3)}"

    # Pattern: FTEA6X0YYYYY (older format with part in different position)
    match = re.match(r'^(FTEA)6([56])0([12])(\d{4})$', prf_id)
    if match:
        # FTEA65011265 → FTEA65001265 or similar
        return f"{match.group(1)}6{match.group(2)}00{match.group(4)}"

    # Pattern: FTEA63011463 → FTEA63001463
    match = re.match(r'^(FTEA)(\d{2})0([12])(\d{4})$', prf_id)
    if match:
        return f"{match.group(1)}{match.group(2)}00{match.group(4)}"

    return None


def add_fallback_link(
    conn: sqlite3.Connection,
    episode_prf_id: str,
    archive_url: str,
    title: str,
    description: str | None,
) -> int:
    """Add Archive.org as fallback link for an episode."""
    cursor = conn.cursor()

    # Check if link already exists
    cursor.execute("""
        SELECT 1 FROM episode_resources er
        JOIN external_resources r ON er.resource_id = r.id
        WHERE er.episode_id = ? AND r.url = ?
    """, (episode_prf_id, archive_url))
    if cursor.fetchone():
        return -1  # Already exists

    # Insert into external_resources
    cursor.execute("""
        INSERT INTO external_resources (url, title, type, description, added_date)
        VALUES (?, ?, 'archive_fallback', ?, ?)
    """, (archive_url, title, description, datetime.now().isoformat()))

    resource_id = cursor.lastrowid

    # Link to episode
    cursor.execute("""
        INSERT OR IGNORE INTO episode_resources (episode_id, resource_id)
        VALUES (?, ?)
    """, (episode_prf_id, resource_id))

    return resource_id


def import_tramteatret_episode(
    conn: sqlite3.Connection,
    title: str,
    archive_url: str,
    description: str | None,
) -> str | None:
    """Import Tramteatret content as a new episode."""
    cursor = conn.cursor()

    # Generate a unique prf_id for Archive.org content
    # Extract identifier from URL
    match = re.search(r'archive\.org/details/([^/]+)', archive_url)
    if not match:
        return None

    archive_id = match.group(1)
    prf_id = f"ARCH_{archive_id[:20]}"  # Truncate if too long

    # Check if already exists
    cursor.execute("SELECT 1 FROM episodes WHERE prf_id = ?", (prf_id,))
    if cursor.fetchone():
        return None  # Already exists

    # Extract series info from title
    series_title = None
    episode_num = None

    if "Randi og Ronnys restaurant" in title:
        series_title = "Randi og Ronnys restaurant"
        match = re.search(r'(\d+):(\d+)', title)
        if match:
            episode_num = int(match.group(1))
    elif "Serum Serum" in title:
        series_title = "Serum Serum"
        match = re.search(r'(\d+):(\d+)', title)
        if match:
            episode_num = int(match.group(1))
    elif "Pelle Parafins" in title:
        series_title = "Pelle Parafins bøljeband og automatspøkelsene"
        match = re.search(r'(\d+):(\d+)', title)
        if match:
            episode_num = int(match.group(1))

    # Insert episode
    cursor.execute("""
        INSERT INTO episodes (prf_id, title, description, series_id, medium)
        VALUES (?, ?, ?, ?, 'tv')
    """, (prf_id, title, description, series_title))

    # Add Archive.org as primary source (not fallback, since it's the only source)
    cursor.execute("""
        INSERT INTO external_resources (url, title, type, description, added_date)
        VALUES (?, ?, 'archive_primary', ?, ?)
    """, (archive_url, title, description, datetime.now().isoformat()))

    resource_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO episode_resources (episode_id, resource_id)
        VALUES (?, ?)
    """, (prf_id, resource_id))

    return prf_id


def parse_unmatched_file(file_path: Path) -> list[dict]:
    """Parse the archive_still_unmatched.txt file."""
    items = []
    current_item = {}

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if line.startswith("Title: "):
                if current_item:
                    items.append(current_item)
                current_item = {"title": line[7:]}
            elif line.startswith("Archive.org: "):
                current_item["archive_url"] = line[13:]
            elif line.startswith("NRK: "):
                current_item["nrk_url"] = line[5:]
                # Extract prf_id from NRK URL
                match = re.search(r'[?&]v=([A-Z0-9]+)', line)
                if match:
                    current_item["nrk_prf_id"] = match.group(1)
            elif line.startswith("Description: "):
                current_item["description"] = line[13:]

    if current_item:
        items.append(current_item)

    return items


def main():
    parser = argparse.ArgumentParser(description="Import remaining Archive.org items")
    parser.add_argument("--db-path", default="web/static/kulturperler.db")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    script_dir = Path(__file__).parent.parent
    db_path = script_dir / args.db_path
    data_dir = script_dir / args.data_dir

    unmatched_file = data_dir / "archive_still_unmatched.txt"
    if not unmatched_file.exists():
        print(f"Error: {unmatched_file} not found")
        return

    print("=" * 60)
    print("Importing remaining Archive.org items")
    if args.dry_run:
        print("(DRY RUN)")
    print("=" * 60)

    items = parse_unmatched_file(unmatched_file)
    print(f"Loaded {len(items)} unmatched items")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Load existing episodes for multi-part matching
    cursor.execute("SELECT prf_id, title FROM episodes")
    existing_episodes = {row[0]: row[1] for row in cursor.fetchall()}
    print(f"Existing episodes in database: {len(existing_episodes)}")

    multipart_matched = 0
    tramteatret_imported = 0
    skipped = 0
    still_unmatched = []

    for item in items:
        title = item.get("title", "")
        archive_url = item.get("archive_url", "")
        nrk_prf_id = item.get("nrk_prf_id")
        description = item.get("description")

        # Check if Tramteatret content
        is_tramteatret = any(x in title for x in [
            "Randi og Ronny",
            "Serum Serum",
            "Pelle Parafin",
        ])

        if is_tramteatret:
            print(f"  TRAMTEATRET: {title[:50]}...")
            if not args.dry_run:
                result = import_tramteatret_episode(conn, title, archive_url, description)
                if result:
                    tramteatret_imported += 1
                else:
                    skipped += 1
            else:
                tramteatret_imported += 1
            continue

        # Try multi-part matching
        if nrk_prf_id:
            base_prf_id = normalize_prf_id_for_parts(nrk_prf_id)

            if base_prf_id and base_prf_id in existing_episodes:
                print(f"  MULTIPART: '{title[:40]}' -> '{existing_episodes[base_prf_id][:40]}' ({nrk_prf_id} -> {base_prf_id})")
                if not args.dry_run:
                    result = add_fallback_link(conn, base_prf_id, archive_url, title, description)
                    if result == -1:
                        print(f"    (already linked)")
                        skipped += 1
                    else:
                        multipart_matched += 1
                else:
                    multipart_matched += 1
                continue

        # Still unmatched
        still_unmatched.append(item)

    if not args.dry_run:
        conn.commit()

    conn.close()

    print(f"\n{'=' * 60}")
    print("Results:")
    print(f"  Multi-part fallbacks added: {multipart_matched}")
    print(f"  Tramteatret episodes imported: {tramteatret_imported}")
    print(f"  Skipped (already exists): {skipped}")
    print(f"  Still unmatched: {len(still_unmatched)}")
    print(f"{'=' * 60}")

    # Save remaining unmatched
    if still_unmatched:
        output_file = data_dir / "archive_final_unmatched.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# Archive.org items that could not be matched or imported\n")
            f.write(f"# Total: {len(still_unmatched)} items\n")
            f.write("#" + "=" * 70 + "\n\n")

            for item in still_unmatched:
                f.write(f"Title: {item.get('title', 'Unknown')}\n")
                f.write(f"Archive.org: {item.get('archive_url', '')}\n")
                if item.get('nrk_url'):
                    f.write(f"NRK: {item.get('nrk_url')}\n")
                if item.get('description'):
                    f.write(f"Description: {item.get('description')}\n")
                f.write("\n" + "-" * 70 + "\n\n")

        print(f"\nRemaining unmatched saved to: {output_file}")


if __name__ == "__main__":
    main()
