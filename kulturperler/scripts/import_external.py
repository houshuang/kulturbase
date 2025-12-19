#!/usr/bin/env python3
"""
Import harvested external theatre content into the database.

Reads harvested data from all sources, attempts to match content to existing plays,
and inserts into the external_performances table.

Usage:
    python import_external.py [--db-path PATH] [--data-dir PATH] [--dry-run]
"""

import argparse
import json
import re
import sqlite3
import unicodedata
from datetime import datetime
from pathlib import Path


def normalize_title(title: str) -> str:
    """Normalize a title for matching."""
    if not title:
        return ""

    # Lowercase
    normalized = title.lower()

    # Remove common prefixes/suffixes
    prefixes = [
        "fjernsynsteatret:", "fjernsynsteatret -",
        "radioteatret:", "radioteatret -",
        "nrk:", "nrk -",
    ]
    for prefix in prefixes:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):].strip()

    # Remove quotes
    normalized = normalized.replace('"', '').replace("'", "").replace("«", "").replace("»", "")

    # Remove parenthetical content like (1962) or (TV)
    normalized = re.sub(r"\([^)]*\)", "", normalized)

    # Remove part indicators
    normalized = re.sub(r"\s*-?\s*del\s+\d+.*", "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\s*-?\s*\d+\s*:\s*\d+.*", "", normalized)

    # Normalize unicode
    normalized = unicodedata.normalize("NFKC", normalized)

    # Remove extra whitespace
    normalized = " ".join(normalized.split())

    return normalized.strip()


def fuzzy_match_score(s1: str, s2: str) -> float:
    """Calculate similarity score between two strings (0-1)."""
    if not s1 or not s2:
        return 0.0

    # Normalize both
    s1 = normalize_title(s1)
    s2 = normalize_title(s2)

    if s1 == s2:
        return 1.0

    # Check if one contains the other
    if s1 in s2 or s2 in s1:
        shorter = min(len(s1), len(s2))
        longer = max(len(s1), len(s2))
        return shorter / longer

    # Simple word overlap
    words1 = set(s1.split())
    words2 = set(s2.split())

    if not words1 or not words2:
        return 0.0

    common = words1 & words2
    return len(common) / max(len(words1), len(words2))


class ExternalImporter:
    def __init__(self, db_path: Path, data_dir: Path, dry_run: bool = False):
        self.db_path = db_path
        self.data_dir = data_dir
        self.dry_run = dry_run
        self.conn = None
        self.plays_cache = {}  # normalized_title -> play_id
        self.existing_episodes = set()  # prf_ids already in episodes table
        self.stats = {
            "total": 0,
            "matched": 0,
            "unmatched": 0,
            "duplicates": 0,
            "skipped_exists_in_nrk": 0,
            "errors": 0,
        }

    def connect(self):
        """Connect to database."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._load_plays_cache()
        self._load_existing_episodes()

    def _load_plays_cache(self):
        """Load plays into cache for matching."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, title, original_title FROM plays")

        for row in cursor.fetchall():
            play_id = row["id"]
            title = row["title"]
            original_title = row["original_title"]

            # Index by normalized title
            norm_title = normalize_title(title)
            if norm_title:
                self.plays_cache[norm_title] = play_id

            if original_title:
                norm_original = normalize_title(original_title)
                if norm_original:
                    self.plays_cache[norm_original] = play_id

        print(f"Loaded {len(self.plays_cache)} play titles for matching")

    def _load_existing_episodes(self):
        """Load existing episode prf_ids to avoid duplicates from Internet Archive."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT prf_id FROM episodes")
        for row in cursor.fetchall():
            self.existing_episodes.add(row["prf_id"].upper())
        print(f"Loaded {len(self.existing_episodes)} existing episode IDs for deduplication")

    def is_duplicate_of_nrk(self, item: dict) -> bool:
        """Check if item is a duplicate of existing NRK content."""
        # Check nrk_prf_id field (from Internet Archive items)
        nrk_prf_id = item.get("nrk_prf_id")
        if nrk_prf_id and nrk_prf_id.upper() in self.existing_episodes:
            return True
        return False

    def match_to_play(self, title: str) -> int | None:
        """Try to match a title to an existing play."""
        norm_title = normalize_title(title)

        # Direct match
        if norm_title in self.plays_cache:
            return self.plays_cache[norm_title]

        # Fuzzy match
        best_match = None
        best_score = 0.0
        threshold = 0.8

        for play_title, play_id in self.plays_cache.items():
            score = fuzzy_match_score(norm_title, play_title)
            if score > best_score and score >= threshold:
                best_score = score
                best_match = play_id

        return best_match

    def url_exists(self, url: str) -> bool:
        """Check if URL already exists in external_performances."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT 1 FROM external_performances WHERE url = ?",
            (url,)
        )
        return cursor.fetchone() is not None

    def import_item(self, item: dict) -> bool:
        """Import a single item into the database."""
        url = item.get("url")
        if not url:
            self.stats["errors"] += 1
            return False

        # Skip if this is a duplicate of existing NRK content
        if self.is_duplicate_of_nrk(item):
            self.stats["skipped_exists_in_nrk"] += 1
            return False

        # Check for duplicates in external_performances
        if self.url_exists(url):
            self.stats["duplicates"] += 1
            return False

        # Try to match to existing play
        play_id = self.match_to_play(item.get("title", ""))
        if play_id:
            self.stats["matched"] += 1
        else:
            self.stats["unmatched"] += 1

        if self.dry_run:
            self.stats["total"] += 1
            return True

        # Insert into database
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO external_performances (
                    play_id, title, url, platform, year, language,
                    description, duration_seconds, venue, content_type,
                    source_id, thumbnail_url, added_date, is_working
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                play_id,
                item.get("title", "")[:500],
                url,
                item.get("platform"),
                item.get("year"),
                item.get("language", "no"),
                item.get("description", "")[:2000] if item.get("description") else None,
                item.get("duration_seconds"),
                item.get("venue"),
                item.get("content_type"),
                item.get("source_id"),
                item.get("thumbnail_url"),
                datetime.now().isoformat(),
            ))
            self.conn.commit()
            self.stats["total"] += 1
            return True
        except sqlite3.Error as e:
            print(f"Error inserting {url}: {e}")
            self.stats["errors"] += 1
            return False

    def load_harvested_data(self) -> list[dict]:
        """Load all harvested data from the raw directories."""
        items = []
        raw_dir = self.data_dir / "raw"

        if not raw_dir.exists():
            print(f"Warning: {raw_dir} does not exist")
            return items

        # Internet Archive
        ia_file = raw_dir / "internet_archive" / "items.json"
        if ia_file.exists():
            with open(ia_file, "r", encoding="utf-8") as f:
                ia_items = json.load(f)
                items.extend(ia_items)
                print(f"Loaded {len(ia_items)} items from Internet Archive")

        # YouTube channels
        yt_file = raw_dir / "youtube_channels" / "all_videos.json"
        if yt_file.exists():
            with open(yt_file, "r", encoding="utf-8") as f:
                yt_items = json.load(f)
                items.extend(yt_items)
                print(f"Loaded {len(yt_items)} items from YouTube channels")

        # Vimeo channels
        vimeo_file = raw_dir / "vimeo_channels" / "all_videos.json"
        if vimeo_file.exists():
            with open(vimeo_file, "r", encoding="utf-8") as f:
                vimeo_items = json.load(f)
                items.extend(vimeo_items)
                print(f"Loaded {len(vimeo_items)} items from Vimeo channels")

        # Nationaltheatret
        nt_file = raw_dir / "nationaltheatret" / "ntv_videos.json"
        if nt_file.exists():
            with open(nt_file, "r", encoding="utf-8") as f:
                nt_items = json.load(f)
                items.extend(nt_items)
                print(f"Loaded {len(nt_items)} items from Nationaltheatret NTV")

        # Det Norske Teatret
        dnt_file = raw_dir / "det_norske_teatret" / "programs.json"
        if dnt_file.exists():
            with open(dnt_file, "r", encoding="utf-8") as f:
                dnt_items = json.load(f)
                items.extend(dnt_items)
                print(f"Loaded {len(dnt_items)} items from Det Norske Teatret")

        # Kilden
        kilden_file = raw_dir / "kilden" / "videos.json"
        if kilden_file.exists():
            with open(kilden_file, "r", encoding="utf-8") as f:
                kilden_items = json.load(f)
                items.extend(kilden_items)
                print(f"Loaded {len(kilden_items)} items from Kilden")

        return items

    def import_all(self):
        """Import all harvested content."""
        items = self.load_harvested_data()

        if not items:
            print("No items to import")
            return

        print(f"\n{'=' * 60}")
        print(f"Importing {len(items)} items...")
        if self.dry_run:
            print("(DRY RUN - no changes will be made)")
        print(f"{'=' * 60}\n")

        for i, item in enumerate(items):
            if (i + 1) % 50 == 0:
                print(f"Progress: {i + 1}/{len(items)} items processed...")
            self.import_item(item)

        print(f"\n{'=' * 60}")
        print("Import complete!")
        print(f"  Total imported: {self.stats['total']}")
        print(f"  Matched to plays: {self.stats['matched']}")
        print(f"  Unmatched (for review): {self.stats['unmatched']}")
        print(f"  Skipped (already in NRK): {self.stats['skipped_exists_in_nrk']}")
        print(f"  Duplicates skipped: {self.stats['duplicates']}")
        print(f"  Errors: {self.stats['errors']}")
        print(f"{'=' * 60}")

    def generate_report(self):
        """Generate a report of unmatched items for manual review."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, title, url, platform, venue, year, content_type
            FROM external_performances
            WHERE play_id IS NULL
            ORDER BY venue, title
        """)

        unmatched = cursor.fetchall()
        if not unmatched:
            print("No unmatched items to review")
            return

        report_file = self.data_dir / "unmatched_items_report.json"

        report = []
        for row in unmatched:
            report.append({
                "id": row["id"],
                "title": row["title"],
                "url": row["url"],
                "platform": row["platform"],
                "venue": row["venue"],
                "year": row["year"],
                "content_type": row["content_type"],
            })

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\nGenerated report: {report_file}")
        print(f"  {len(report)} items need manual review/matching")

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


def ensure_schema(db_path: Path):
    """Ensure the external_performances table has all required columns."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check existing columns
    cursor.execute("PRAGMA table_info(external_performances)")
    existing_cols = {row[1] for row in cursor.fetchall()}

    new_columns = [
        ("duration_seconds", "INTEGER"),
        ("venue", "TEXT"),
        ("content_type", "TEXT"),
        ("source_id", "TEXT"),
        ("thumbnail_url", "TEXT"),
    ]

    for col_name, col_type in new_columns:
        if col_name not in existing_cols:
            print(f"Adding column: {col_name}")
            cursor.execute(f"ALTER TABLE external_performances ADD COLUMN {col_name} {col_type}")

    conn.commit()
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Import external theatre content")
    parser.add_argument(
        "--db-path",
        type=str,
        default="web/static/kulturperler.db",
        help="Path to database (default: web/static/kulturperler.db)",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data",
        help="Data directory (default: data)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually insert data, just report what would happen",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Only generate unmatched items report",
    )

    args = parser.parse_args()

    script_dir = Path(__file__).parent.parent
    db_path = script_dir / args.db_path
    data_dir = script_dir / args.data_dir

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return

    # Ensure schema is up to date
    ensure_schema(db_path)

    importer = ExternalImporter(db_path, data_dir, dry_run=args.dry_run)
    importer.connect()

    try:
        if args.report_only:
            importer.generate_report()
        else:
            importer.import_all()
            importer.generate_report()
    finally:
        importer.close()


if __name__ == "__main__":
    main()
