#!/usr/bin/env python3
"""
Match episodes to Sceneweb artworks (original plays).

This script searches Sceneweb for each episode title and attempts to match
it to an original artwork (play). When matched, it fetches playwright info.

Usage:
    python 02_match_sceneweb.py [--db DB_PATH] [--delay SECONDS]
"""

import argparse
import json
import sqlite3
import time
from pathlib import Path
from datetime import datetime

from utils.sceneweb_scraper import (
    search_artworks,
    fetch_artwork_details,
    fetch_person_details,
)


def normalize_title(title: str) -> str:
    """Normalize a title for matching."""
    import re
    # Remove episode numbers like "1:2", "2:2", "1/3"
    title = re.sub(r'\s*\d+[:/]\d+\s*$', '', title)
    # Remove parenthetical notes
    title = re.sub(r'\s*\([^)]*\)\s*', ' ', title)
    # Remove "Fjernsynsteatret viste:" prefix
    title = re.sub(r'^Fjernsynsteatret viste?:?\s*', '', title, flags=re.IGNORECASE)
    # Remove " - Introduksjon" suffix
    title = re.sub(r'\s*-\s*[Ii]ntroduksjon\s*$', '', title)
    # Clean up whitespace
    title = ' '.join(title.split())
    return title.strip()


def get_or_create_person(conn: sqlite3.Connection, name: str, sceneweb_id: int = None,
                         sceneweb_url: str = None, birth_year: int = None,
                         death_year: int = None) -> int:
    """Get or create a person, return their ID."""
    cursor = conn.cursor()
    normalized = ' '.join(name.lower().split())

    # Check if exists by sceneweb_id first
    if sceneweb_id:
        cursor.execute("SELECT id FROM persons WHERE sceneweb_id = ?", (sceneweb_id,))
        row = cursor.fetchone()
        if row:
            # Update with any new info
            cursor.execute("""
                UPDATE persons SET
                    sceneweb_url = COALESCE(sceneweb_url, ?),
                    birth_year = COALESCE(birth_year, ?),
                    death_year = COALESCE(death_year, ?)
                WHERE id = ?
            """, (sceneweb_url, birth_year, death_year, row[0]))
            conn.commit()
            return row[0]

    # Check by normalized name
    cursor.execute("SELECT id FROM persons WHERE normalized_name = ?", (normalized,))
    row = cursor.fetchone()
    if row:
        # Update with sceneweb info if we have it
        if sceneweb_id:
            cursor.execute("""
                UPDATE persons SET
                    sceneweb_id = ?,
                    sceneweb_url = ?,
                    birth_year = COALESCE(birth_year, ?),
                    death_year = COALESCE(death_year, ?)
                WHERE id = ?
            """, (sceneweb_id, sceneweb_url, birth_year, death_year, row[0]))
            conn.commit()
        return row[0]

    # Create new
    cursor.execute("""
        INSERT INTO persons (name, normalized_name, sceneweb_id, sceneweb_url, birth_year, death_year)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, normalized, sceneweb_id, sceneweb_url, birth_year, death_year))
    conn.commit()
    return cursor.lastrowid


def get_or_create_play(conn: sqlite3.Connection, title: str, playwright_id: int = None,
                       sceneweb_id: int = None, sceneweb_url: str = None,
                       year_written: int = None) -> int:
    """Get or create a play, return its ID."""
    cursor = conn.cursor()

    # Check if exists by sceneweb_id first
    if sceneweb_id:
        cursor.execute("SELECT id FROM plays WHERE sceneweb_id = ?", (sceneweb_id,))
        row = cursor.fetchone()
        if row:
            return row[0]

    # Check by title
    cursor.execute("SELECT id FROM plays WHERE title = ?", (title,))
    row = cursor.fetchone()
    if row:
        # Update with sceneweb info if we have it
        if sceneweb_id:
            cursor.execute("""
                UPDATE plays SET
                    sceneweb_id = ?,
                    sceneweb_url = ?,
                    playwright_id = COALESCE(playwright_id, ?),
                    year_written = COALESCE(year_written, ?)
                WHERE id = ?
            """, (sceneweb_id, sceneweb_url, playwright_id, year_written, row[0]))
            conn.commit()
        return row[0]

    # Create new
    cursor.execute("""
        INSERT INTO plays (title, playwright_id, sceneweb_id, sceneweb_url, year_written)
        VALUES (?, ?, ?, ?, ?)
    """, (title, playwright_id, sceneweb_id, sceneweb_url, year_written))
    conn.commit()
    return cursor.lastrowid


def load_progress(progress_file: Path) -> dict:
    """Load matching progress from file."""
    if progress_file.exists():
        with open(progress_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"matched": {}, "no_match": [], "errors": []}


def save_progress(progress_file: Path, progress: dict):
    """Save matching progress to file."""
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def match_episodes(db_path: Path, delay: float = 2.0):
    """Match episodes to Sceneweb artworks."""
    print(f"\n{'='*60}")
    print(f"Matching episodes to Sceneweb")
    print(f"Database: {db_path}")
    print(f"Delay: {delay}s")
    print(f"{'='*60}\n")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Load progress
    progress_file = db_path.parent / "sceneweb_progress.json"
    progress = load_progress(progress_file)

    # Get all episodes without a play_id
    cursor.execute("""
        SELECT prf_id, title FROM episodes
        WHERE play_id IS NULL
        ORDER BY year DESC
    """)
    episodes = cursor.fetchall()

    print(f"Found {len(episodes)} episodes without play association")
    print(f"Already matched: {len(progress['matched'])}")
    print(f"Known no-match: {len(progress['no_match'])}")
    print()

    matched_count = 0
    no_match_count = 0
    error_count = 0

    for i, ep in enumerate(episodes):
        prf_id = ep['prf_id']
        title = ep['title']

        # Skip if already processed
        if prf_id in progress['matched'] or prf_id in progress['no_match']:
            continue

        normalized = normalize_title(title)
        if not normalized or len(normalized) < 3:
            progress['no_match'].append(prf_id)
            continue

        print(f"[{i+1}/{len(episodes)}] Searching: {normalized[:50]}")

        try:
            # Search Sceneweb
            results = search_artworks(normalized, delay=delay)

            if not results:
                print(f"  -> No results")
                progress['no_match'].append(prf_id)
                no_match_count += 1
                save_progress(progress_file, progress)
                continue

            # Try to find best match
            best_match = None
            for result in results:
                result_title = result['title'].lower().strip()
                search_title = normalized.lower().strip()

                # Exact match or close match
                if result_title == search_title or search_title in result_title:
                    best_match = result
                    break

            if not best_match:
                # Use first result if it looks reasonable
                if len(results) == 1:
                    best_match = results[0]
                else:
                    print(f"  -> No good match in {len(results)} results")
                    progress['no_match'].append(prf_id)
                    no_match_count += 1
                    save_progress(progress_file, progress)
                    continue

            # Fetch artwork details
            print(f"  -> Found: {best_match['title']} (ID: {best_match['sceneweb_id']})")
            artwork = fetch_artwork_details(best_match['sceneweb_id'], delay=delay)

            if not artwork:
                print(f"  -> Failed to fetch details")
                progress['errors'].append({"prf_id": prf_id, "error": "Failed to fetch artwork"})
                error_count += 1
                save_progress(progress_file, progress)
                continue

            # Get or create playwright
            playwright_id = None
            if artwork.playwright_name and artwork.playwright_sceneweb_id:
                print(f"  -> Playwright: {artwork.playwright_name}")

                # Fetch playwright details
                playwright = fetch_person_details(
                    artwork.playwright_sceneweb_id,
                    delay=delay
                )

                playwright_id = get_or_create_person(
                    conn,
                    artwork.playwright_name,
                    sceneweb_id=artwork.playwright_sceneweb_id,
                    sceneweb_url=playwright.url if playwright else None,
                    birth_year=playwright.birth_year if playwright else None,
                    death_year=playwright.death_year if playwright else None,
                )

            # Get or create play
            play_id = get_or_create_play(
                conn,
                artwork.title,
                playwright_id=playwright_id,
                sceneweb_id=artwork.sceneweb_id,
                sceneweb_url=artwork.url,
                year_written=artwork.year_written,
            )

            # Update episode
            cursor.execute(
                "UPDATE episodes SET play_id = ? WHERE prf_id = ?",
                (play_id, prf_id)
            )
            conn.commit()

            progress['matched'][prf_id] = {
                "play_id": play_id,
                "sceneweb_id": artwork.sceneweb_id,
                "title": artwork.title,
            }
            matched_count += 1
            print(f"  -> Matched! (play_id: {play_id})")

        except Exception as e:
            print(f"  -> Error: {e}")
            progress['errors'].append({"prf_id": prf_id, "error": str(e)})
            error_count += 1

        save_progress(progress_file, progress)

    conn.close()

    print(f"\n{'='*60}")
    print(f"Matching complete!")
    print(f"  New matches: {matched_count}")
    print(f"  No match: {no_match_count}")
    print(f"  Errors: {error_count}")
    print(f"  Total matched: {len(progress['matched'])}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Match episodes to Sceneweb")
    parser.add_argument(
        "--db",
        default="data/kulturperler.db",
        help="Database path (default: data/kulturperler.db)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay between requests in seconds (default: 2.0)",
    )

    args = parser.parse_args()

    script_dir = Path(__file__).parent.parent
    db_path = script_dir / args.db

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return

    match_episodes(db_path, args.delay)


if __name__ == "__main__":
    main()
