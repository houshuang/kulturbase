#!/usr/bin/env python3
"""
Enrich plays and persons with Wikidata information.

This script searches Wikidata for plays and persons, adding:
- Wikidata IDs
- Wikipedia URLs
- Birth/death years for persons
- Original titles and year written for plays

Usage:
    python 03_enrich_wikidata.py [--db DB_PATH] [--delay SECONDS]
"""

import argparse
import json
import sqlite3
import time
from pathlib import Path
from datetime import datetime

from utils.wikidata_api import (
    search_plays,
    fetch_play_info,
    fetch_person_info,
    search_and_match_play,
)


def load_progress(progress_file: Path) -> dict:
    """Load enrichment progress from file."""
    if progress_file.exists():
        with open(progress_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "plays_enriched": [],
        "plays_no_match": [],
        "persons_enriched": [],
        "persons_no_match": [],
        "errors": []
    }


def save_progress(progress_file: Path, progress: dict):
    """Save enrichment progress to file."""
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def search_person_wikidata(name: str, birth_year: int = None) -> dict | None:
    """Search Wikidata for a person."""
    import requests

    params = {
        "action": "wbsearchentities",
        "search": name,
        "language": "no",
        "format": "json",
        "limit": 10,
    }

    resp = requests.get("https://www.wikidata.org/w/api.php", params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    results = data.get("search", [])
    if not results:
        # Try English
        params["language"] = "en"
        resp = requests.get("https://www.wikidata.org/w/api.php", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("search", [])

    if not results:
        return None

    # Look for person-like descriptions
    person_keywords = ["playwright", "dramatiker", "writer", "forfatter", "author",
                       "actor", "skuespiller", "director", "regissør", "composer",
                       "komponist", "born", "født", "died"]

    for result in results:
        desc = result.get("description", "").lower()
        if any(kw in desc for kw in person_keywords):
            return {
                "wikidata_id": result["id"],
                "label": result.get("label", ""),
                "description": result.get("description", ""),
            }

    # Return first result if no obvious match
    return {
        "wikidata_id": results[0]["id"],
        "label": results[0].get("label", ""),
        "description": results[0].get("description", ""),
    }


def enrich_plays(conn: sqlite3.Connection, progress: dict, progress_file: Path, delay: float):
    """Enrich plays with Wikidata information."""
    cursor = conn.cursor()

    # Get plays without wikidata_id
    cursor.execute("""
        SELECT id, title, original_title, year_written
        FROM plays
        WHERE wikidata_id IS NULL
        ORDER BY id
    """)
    plays = cursor.fetchall()

    print(f"\nEnriching {len(plays)} plays...")
    enriched = 0
    no_match = 0

    for play_id, title, original_title, year_written in plays:
        if play_id in progress['plays_enriched'] or play_id in progress['plays_no_match']:
            continue

        print(f"  Searching: {title[:50]}")

        try:
            # Search Wikidata
            play_info = search_and_match_play(title)

            if not play_info:
                # Try original title if different
                if original_title and original_title != title:
                    play_info = search_and_match_play(original_title)

            if not play_info:
                print(f"    -> No match")
                progress['plays_no_match'].append(play_id)
                no_match += 1
            else:
                print(f"    -> Found: {play_info.wikidata_id}")

                # Update play
                cursor.execute("""
                    UPDATE plays SET
                        wikidata_id = ?,
                        original_title = COALESCE(original_title, ?),
                        year_written = COALESCE(year_written, ?),
                        wikipedia_url = COALESCE(wikipedia_url, ?)
                    WHERE id = ?
                """, (
                    play_info.wikidata_id,
                    play_info.original_title,
                    play_info.year_written,
                    play_info.wikipedia_url,
                    play_id
                ))
                conn.commit()

                progress['plays_enriched'].append(play_id)
                enriched += 1

            save_progress(progress_file, progress)
            time.sleep(delay)

        except Exception as e:
            print(f"    -> Error: {e}")
            progress['errors'].append({"type": "play", "id": play_id, "error": str(e)})
            save_progress(progress_file, progress)

    print(f"  Enriched: {enriched}, No match: {no_match}")


def enrich_persons(conn: sqlite3.Connection, progress: dict, progress_file: Path, delay: float):
    """Enrich persons with Wikidata information."""
    cursor = conn.cursor()

    # Get persons without wikidata_id (prioritize those with sceneweb_id or playwright role)
    cursor.execute("""
        SELECT DISTINCT p.id, p.name, p.birth_year, p.death_year
        FROM persons p
        LEFT JOIN plays pl ON p.id = pl.playwright_id
        WHERE p.wikidata_id IS NULL
        ORDER BY
            CASE WHEN pl.id IS NOT NULL THEN 0 ELSE 1 END,
            CASE WHEN p.sceneweb_id IS NOT NULL THEN 0 ELSE 1 END,
            p.id
        LIMIT 200
    """)
    persons = cursor.fetchall()

    print(f"\nEnriching {len(persons)} persons...")
    enriched = 0
    no_match = 0

    for person_id, name, birth_year, death_year in persons:
        if person_id in progress['persons_enriched'] or person_id in progress['persons_no_match']:
            continue

        print(f"  Searching: {name}")

        try:
            # Search Wikidata
            result = search_person_wikidata(name, birth_year)

            if not result:
                print(f"    -> No match")
                progress['persons_no_match'].append(person_id)
                no_match += 1
            else:
                # Fetch full info
                person_info = fetch_person_info(result['wikidata_id'])

                if person_info:
                    print(f"    -> Found: {person_info.wikidata_id} ({person_info.birth_year or '?'}-{person_info.death_year or '?'})")

                    # Update person
                    cursor.execute("""
                        UPDATE persons SET
                            wikidata_id = ?,
                            birth_year = COALESCE(birth_year, ?),
                            death_year = COALESCE(death_year, ?),
                            nationality = COALESCE(nationality, ?),
                            wikipedia_url = COALESCE(wikipedia_url, ?)
                        WHERE id = ?
                    """, (
                        person_info.wikidata_id,
                        person_info.birth_year,
                        person_info.death_year,
                        person_info.nationality,
                        person_info.wikipedia_url,
                        person_id
                    ))
                    conn.commit()

                    progress['persons_enriched'].append(person_id)
                    enriched += 1
                else:
                    progress['persons_no_match'].append(person_id)
                    no_match += 1

            save_progress(progress_file, progress)
            time.sleep(delay)

        except Exception as e:
            print(f"    -> Error: {e}")
            progress['errors'].append({"type": "person", "id": person_id, "error": str(e)})
            save_progress(progress_file, progress)

    print(f"  Enriched: {enriched}, No match: {no_match}")


def enrich_database(db_path: Path, delay: float = 1.0):
    """Enrich database with Wikidata information."""
    print(f"\n{'='*60}")
    print(f"Enriching database with Wikidata")
    print(f"Database: {db_path}")
    print(f"Delay: {delay}s")
    print(f"{'='*60}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Load progress
    progress_file = db_path.parent / "wikidata_progress.json"
    progress = load_progress(progress_file)

    print(f"\nProgress loaded:")
    print(f"  Plays enriched: {len(progress['plays_enriched'])}")
    print(f"  Persons enriched: {len(progress['persons_enriched'])}")

    # Enrich plays first (smaller set, more important)
    enrich_plays(conn, progress, progress_file, delay)

    # Then enrich persons (larger set)
    enrich_persons(conn, progress, progress_file, delay)

    conn.close()

    print(f"\n{'='*60}")
    print(f"Enrichment complete!")
    print(f"  Plays enriched: {len(progress['plays_enriched'])}")
    print(f"  Persons enriched: {len(progress['persons_enriched'])}")
    print(f"  Errors: {len(progress['errors'])}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Enrich database with Wikidata")
    parser.add_argument(
        "--db",
        default="data/kulturperler.db",
        help="Database path (default: data/kulturperler.db)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between requests in seconds (default: 1.0)",
    )

    args = parser.parse_args()

    script_dir = Path(__file__).parent.parent
    db_path = script_dir / args.db

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return

    enrich_database(db_path, args.delay)


if __name__ == "__main__":
    main()
