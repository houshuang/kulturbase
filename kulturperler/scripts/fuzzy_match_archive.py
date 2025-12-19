#!/usr/bin/env python3
"""
Fuzzy match unmatched Archive.org items to existing episodes.

Extracts play names (excluding dates, episode info) and does fuzzy matching
against existing episode titles in the database.

Usage:
    python fuzzy_match_archive.py [--db-path PATH] [--dry-run]
"""

import argparse
import json
import re
import sqlite3
import unicodedata
from datetime import datetime
from pathlib import Path


def normalize_title(title: str) -> str:
    """Normalize a title for matching - remove dates, episode info, etc."""
    if not title:
        return ""

    # Remove date patterns like "05.11.1985" or "15.01.1995"
    normalized = re.sub(r"\d{1,2}\.\d{1,2}\.\d{4}", "", title)

    # Remove episode patterns like "1:2", "(1:4)", "Del 1", "1/2"
    normalized = re.sub(r"\s*\(?(\d+)\s*[:/]\s*(\d+)\)?", "", normalized)
    normalized = re.sub(r"\s*-?\s*[Dd]el\s+\d+.*", "", normalized)
    normalized = re.sub(r"\s*\(\d+\s*av\s*\d+\)", "", normalized)

    # Remove "Fjernsynsteatret viser:" prefix
    normalized = re.sub(r"^Fjernsynsteatret\s+(viser|viste)?\s*:?\s*", "", normalized, flags=re.IGNORECASE)

    # Remove trailing/leading whitespace and normalize unicode
    normalized = unicodedata.normalize("NFKC", normalized)
    normalized = " ".join(normalized.split()).strip()

    return normalized.lower()


def extract_author_from_description(description: str) -> str | None:
    """Extract author name from description."""
    if not description:
        return None

    # Patterns like "av William Shakespeare", "av Bjørnstjerne Bjørnson"
    match = re.search(r'\bav\s+([A-ZÆØÅ][a-zæøå]+(?:\s+[A-ZÆØÅ][a-zæøå]+)+)', description)
    if match:
        return match.group(1).lower()

    # Pattern like "Manuskript: Erling Pedersen"
    match = re.search(r'[Mm]anuskript(?:forfatter)?:\s*([A-ZÆØÅ][a-zæøå]+(?:\s+[A-ZÆØÅ][a-zæøå]+)*)', description)
    if match:
        return match.group(1).lower()

    return None


def fuzzy_score(s1: str, s2: str) -> float:
    """Calculate similarity score between two strings (0-1)."""
    if not s1 or not s2:
        return 0.0

    s1 = s1.lower().strip()
    s2 = s2.lower().strip()

    if s1 == s2:
        return 1.0

    # Check if one contains the other
    if s1 in s2:
        return len(s1) / len(s2)
    if s2 in s1:
        return len(s2) / len(s1)

    # Word overlap
    words1 = set(s1.split())
    words2 = set(s2.split())

    if not words1 or not words2:
        return 0.0

    common = words1 & words2
    # Weight by longest common match
    return len(common) / max(len(words1), len(words2))


def load_episodes(conn: sqlite3.Connection) -> list[dict]:
    """Load all episodes with their normalized titles."""
    cursor = conn.cursor()
    cursor.execute("SELECT prf_id, title FROM episodes")

    episodes = []
    for row in cursor.fetchall():
        prf_id, title = row
        episodes.append({
            "prf_id": prf_id,
            "title": title,
            "normalized": normalize_title(title),
        })
    return episodes


def find_best_match(item: dict, episodes: list[dict], threshold: float = 0.7) -> dict | None:
    """Find the best matching episode for an archive item."""
    item_title = normalize_title(item.get("title", ""))
    if not item_title:
        return None

    best_match = None
    best_score = 0.0

    for ep in episodes:
        score = fuzzy_score(item_title, ep["normalized"])

        # Boost score if author matches
        author = extract_author_from_description(item.get("description", ""))
        if author and author in ep["title"].lower():
            score = min(1.0, score + 0.2)

        if score > best_score and score >= threshold:
            best_score = score
            best_match = {**ep, "score": score}

    return best_match


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


def main():
    parser = argparse.ArgumentParser(description="Fuzzy match Archive.org items")
    parser.add_argument("--db-path", default="web/static/kulturperler.db")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--threshold", type=float, default=0.7, help="Match threshold (0-1)")
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    script_dir = Path(__file__).parent.parent
    db_path = script_dir / args.db_path
    data_dir = script_dir / args.data_dir

    # Load unmatched items
    unmatched_file = data_dir / "archive_unmatched.json"
    if not unmatched_file.exists():
        print(f"Error: {unmatched_file} not found")
        return

    with open(unmatched_file, "r", encoding="utf-8") as f:
        unmatched_items = json.load(f)

    print("=" * 60)
    print("Fuzzy matching Archive.org items to episodes")
    print(f"Threshold: {args.threshold}")
    if args.dry_run:
        print("(DRY RUN)")
    print("=" * 60)
    print(f"Unmatched items to process: {len(unmatched_items)}")

    conn = sqlite3.connect(db_path)
    episodes = load_episodes(conn)
    print(f"Episodes in database: {len(episodes)}")

    matched = []
    still_unmatched = []

    for item in unmatched_items:
        match = find_best_match(item, episodes, args.threshold)

        if match:
            matched.append({
                "item": item,
                "match": match,
            })
            print(f"  MATCH ({match['score']:.2f}): '{item.get('title', '')[:40]}' -> '{match['title'][:40]}'")

            if not args.dry_run:
                result = add_fallback_link(
                    conn,
                    match["prf_id"],
                    item.get("url"),
                    item.get("title"),
                    item.get("description"),
                )
                if result == -1:
                    print(f"    (already linked)")
        else:
            still_unmatched.append(item)

    if not args.dry_run:
        conn.commit()

    conn.close()

    print(f"\n{'=' * 60}")
    print("Results:")
    print(f"  Fuzzy matched: {len(matched)}")
    print(f"  Still unmatched: {len(still_unmatched)}")
    print(f"{'=' * 60}")

    # Save still unmatched to text file
    if still_unmatched:
        output_file = data_dir / "archive_still_unmatched.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# Archive.org items that could not be matched to existing episodes\n")
            f.write(f"# Total: {len(still_unmatched)} items\n")
            f.write("#" + "=" * 70 + "\n\n")

            for item in still_unmatched:
                title = item.get("title", "Unknown")
                url = item.get("url", "")
                nrk_url = item.get("nrk_url", "")
                desc = (item.get("description") or "")[:200]

                f.write(f"Title: {title}\n")
                f.write(f"Archive.org: {url}\n")
                if nrk_url:
                    f.write(f"NRK: {nrk_url}\n")
                if desc:
                    f.write(f"Description: {desc}...\n")
                f.write("\n" + "-" * 70 + "\n\n")

        print(f"\nStill unmatched saved to: {output_file}")


if __name__ == "__main__":
    main()
