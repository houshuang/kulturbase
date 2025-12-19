#!/usr/bin/env python3
"""
Audit script for kulturperler database person data quality issues.
"""

import sqlite3
import time
import json
import subprocess
from typing import Optional, Dict, List, Tuple

DB_PATH = "/Users/stian/src/nrk/kulturperler/web/static/kulturperler.db"
REVIEW_FILE = "/Users/stian/src/nrk/kulturperler/data/audit_review.md"

# Statistics
stats = {
    "playwrights_bio_fixed": 0,
    "playwrights_bio_not_found": 0,
    "dates_fixed": 0,
    "duplicates_found": 0,
    "orphaned_persons": 0,
    "invalid_dates_fixed": 0,
}

review_items = []

def get_wikipedia_bio(name: str, lang: str = "no") -> Optional[Dict]:
    """Fetch Wikipedia summary for a person using curl."""
    import urllib.parse
    url_name = urllib.parse.quote(name.replace(' ', '_'))
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{url_name}"
    try:
        result = subprocess.run(
            ['curl', '-s', url],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout:
            data = json.loads(result.stdout)
            if data.get('type') == 'standard':
                return data
    except Exception as e:
        pass
    return None

def extract_bio_and_dates(wiki_data: Dict) -> Tuple[Optional[str], Optional[int], Optional[int]]:
    """Extract bio and birth/death years from Wikipedia data."""
    bio = wiki_data.get('extract')
    birth_year = None
    death_year = None

    # Try to extract dates from description
    description = wiki_data.get('description', '')
    # Common patterns: "1944-2021", "(1944-2021)", "born 1944", "died 2021"
    import re

    # Pattern: YYYY-YYYY or (YYYY-YYYY)
    date_pattern = r'\(?(\d{4})\s*[-–—]\s*(\d{4})\)?'
    match = re.search(date_pattern, description)
    if match:
        birth_year = int(match.group(1))
        death_year = int(match.group(2))
    else:
        # Pattern: born YYYY
        born_pattern = r'born\s+(\d{4})'
        match = re.search(born_pattern, description, re.IGNORECASE)
        if match:
            birth_year = int(match.group(1))

        # Pattern: died YYYY
        died_pattern = r'died\s+(\d{4})'
        match = re.search(died_pattern, description, re.IGNORECASE)
        if match:
            death_year = int(match.group(1))

    return bio, birth_year, death_year

def audit_playwrights_without_bio(conn: sqlite3.Connection):
    """Task 1: Find and fix playwrights without bio."""
    print("\n=== TASK 1: Playwrights without bio ===")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, birth_year, death_year
        FROM persons
        WHERE id IN (SELECT DISTINCT playwright_id FROM plays WHERE playwright_id IS NOT NULL)
        AND (bio IS NULL OR bio = '')
        ORDER BY name
    """)

    playwrights = cursor.fetchall()
    print(f"Found {len(playwrights)} playwrights without bio\n")

    for person_id, name, birth_year, death_year in playwrights:
        print(f"Processing: {name} (id={person_id})")

        # Try Norwegian Wikipedia first
        wiki_data = get_wikipedia_bio(name, "no")
        if not wiki_data:
            # Try English Wikipedia
            wiki_data = get_wikipedia_bio(name, "en")

        if wiki_data:
            bio, wiki_birth, wiki_death = extract_bio_and_dates(wiki_data)

            if bio:
                cursor.execute("UPDATE persons SET bio = ? WHERE id = ?", (bio, person_id))
                print(f"  ✓ Added bio from Wikipedia")
                stats["playwrights_bio_fixed"] += 1

                # Also update birth/death years if missing
                if wiki_birth and not birth_year:
                    cursor.execute("UPDATE persons SET birth_year = ? WHERE id = ?", (wiki_birth, person_id))
                    print(f"  ✓ Added birth year: {wiki_birth}")
                    stats["dates_fixed"] += 1

                if wiki_death and not death_year:
                    cursor.execute("UPDATE persons SET death_year = ? WHERE id = ?", (wiki_death, person_id))
                    print(f"  ✓ Added death year: {wiki_death}")
                    stats["dates_fixed"] += 1

                conn.commit()
            else:
                print(f"  ✗ Wikipedia page found but no bio extract")
                stats["playwrights_bio_not_found"] += 1
                review_items.append(f"- [ ] {name} (id={person_id}) - Playwright without bio (Wikipedia page exists but no extract)")
        else:
            print(f"  ✗ Not found on Wikipedia")
            stats["playwrights_bio_not_found"] += 1
            review_items.append(f"- [ ] {name} (id={person_id}) - Playwright without bio (not found on Wikipedia)")

        time.sleep(0.5)  # Be nice to Wikipedia API

def audit_duplicate_names(conn: sqlite3.Connection):
    """Task 2: Find persons with duplicate names."""
    print("\n=== TASK 2: Persons with duplicate names ===")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p1.id, p1.name, p1.birth_year, p2.id, p2.name, p2.birth_year
        FROM persons p1
        JOIN persons p2 ON p1.name = p2.name AND p1.id < p2.id
        ORDER BY p1.name
    """)

    duplicates = cursor.fetchall()
    print(f"Found {len(duplicates)} pairs of persons with identical names\n")

    for id1, name1, birth1, id2, name2, birth2 in duplicates:
        print(f"Duplicate: {name1}")
        print(f"  Person 1: id={id1}, birth={birth1}")
        print(f"  Person 2: id={id2}, birth={birth2}")

        # Check if they have overlapping roles
        cursor.execute("""
            SELECT COUNT(*) FROM episode_persons
            WHERE person_id = ? AND episode_id IN (
                SELECT episode_id FROM episode_persons WHERE person_id = ?
            )
        """, (id1, id2))

        overlap = cursor.fetchone()[0]
        if overlap > 0:
            print(f"  ⚠️  WARNING: {overlap} overlapping episodes!")
            review_items.append(f"- [ ] {name1} (id={id1} and id={id2}) - Duplicate persons with {overlap} overlapping episodes - likely should be merged")
        else:
            review_items.append(f"- [ ] {name1} (id={id1} and id={id2}) - Duplicate persons (no overlapping episodes)")

        stats["duplicates_found"] += 1

def audit_orphaned_persons(conn: sqlite3.Connection):
    """Task 3: Find orphaned persons."""
    print("\n=== TASK 3: Orphaned persons ===")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, birth_year, death_year
        FROM persons
        WHERE id NOT IN (SELECT DISTINCT person_id FROM episode_persons)
        AND id NOT IN (SELECT DISTINCT playwright_id FROM plays WHERE playwright_id IS NOT NULL)
    """)

    orphaned = cursor.fetchall()
    print(f"Found {len(orphaned)} orphaned persons (no episode links and not a playwright)\n")

    stats["orphaned_persons"] = len(orphaned)

    if len(orphaned) > 0:
        review_items.append(f"\n### Orphaned Persons ({len(orphaned)} total)")
        for person_id, name, birth_year, death_year in orphaned[:50]:  # Limit to first 50
            review_items.append(f"- [ ] {name} (id={person_id}) - Orphaned person (consider cleanup)")

def audit_invalid_dates(conn: sqlite3.Connection):
    """Task 5: Find and fix invalid birth/death years."""
    print("\n=== TASK 5: Invalid birth/death years ===")
    cursor = conn.cursor()

    # Check for birth_year > death_year
    cursor.execute("""
        SELECT id, name, birth_year, death_year
        FROM persons
        WHERE birth_year > death_year
    """)

    invalid = cursor.fetchall()
    print(f"Found {len(invalid)} persons with birth_year > death_year")
    for person_id, name, birth_year, death_year in invalid:
        print(f"  {name} (id={person_id}): birth={birth_year}, death={death_year}")
        review_items.append(f"- [ ] {name} (id={person_id}) - Birth year ({birth_year}) > death year ({death_year})")

    # Check for obviously wrong years (except ancient Greeks like Sophocles)
    cursor.execute("""
        SELECT id, name, birth_year, death_year
        FROM persons
        WHERE (birth_year < 1500 OR birth_year > 2020 OR death_year > 2025)
        AND birth_year > 0
    """)

    weird_dates = cursor.fetchall()
    print(f"\nFound {len(weird_dates)} persons with unusual years")
    for person_id, name, birth_year, death_year in weird_dates:
        # Sophocles is fine (-496 to -406)
        if birth_year < 0 and name == "Sofokles":
            print(f"  {name} (id={person_id}): Ancient playwright, dates OK")
            continue

        print(f"  {name} (id={person_id}): birth={birth_year}, death={death_year}")

        # If birth year is clearly wrong (e.g., > 2020), clear it
        if birth_year and birth_year > 2020:
            cursor.execute("UPDATE persons SET birth_year = NULL WHERE id = ?", (person_id,))
            print(f"    ✓ Cleared invalid birth year: {birth_year}")
            stats["invalid_dates_fixed"] += 1
            conn.commit()

        # If death year is clearly wrong (e.g., > 2025), clear it
        if death_year and death_year > 2025:
            cursor.execute("UPDATE persons SET death_year = NULL WHERE id = ?", (person_id,))
            print(f"    ✓ Cleared invalid death year: {death_year}")
            stats["invalid_dates_fixed"] += 1
            conn.commit()

        if birth_year and (birth_year < 1500 and birth_year > 0):
            review_items.append(f"- [ ] {name} (id={person_id}) - Unusual birth year: {birth_year}")

def main():
    print("Kulturperler Database Person Audit")
    print("=" * 50)

    conn = sqlite3.connect(DB_PATH)

    try:
        audit_playwrights_without_bio(conn)
        audit_duplicate_names(conn)
        audit_orphaned_persons(conn)
        audit_invalid_dates(conn)

        # Write review file
        print("\n" + "=" * 50)
        print("Writing review file...")

        with open(REVIEW_FILE, "w") as f:
            f.write("# Kulturperler Person Data Audit Review\n\n")
            f.write("## Summary\n\n")
            f.write(f"- Playwrights bio fixed: {stats['playwrights_bio_fixed']}\n")
            f.write(f"- Playwrights bio not found: {stats['playwrights_bio_not_found']}\n")
            f.write(f"- Birth/death dates fixed: {stats['dates_fixed']}\n")
            f.write(f"- Invalid dates fixed: {stats['invalid_dates_fixed']}\n")
            f.write(f"- Duplicate names found: {stats['duplicates_found']}\n")
            f.write(f"- Orphaned persons: {stats['orphaned_persons']}\n")
            f.write(f"\n## Issues Needing Review ({len(review_items)} items)\n\n")
            f.write("\n".join(review_items))

        print(f"Review file written to: {REVIEW_FILE}")

        print("\n" + "=" * 50)
        print("AUDIT SUMMARY")
        print("=" * 50)
        print(f"✓ Playwrights bio fixed: {stats['playwrights_bio_fixed']}")
        print(f"✗ Playwrights bio not found: {stats['playwrights_bio_not_found']}")
        print(f"✓ Birth/death dates fixed: {stats['dates_fixed']}")
        print(f"✓ Invalid dates fixed: {stats['invalid_dates_fixed']}")
        print(f"⚠️  Duplicate names found: {stats['duplicates_found']}")
        print(f"⚠️  Orphaned persons: {stats['orphaned_persons']}")
        print(f"\nTotal issues fixed: {stats['playwrights_bio_fixed'] + stats['dates_fixed'] + stats['invalid_dates_fixed']}")
        print(f"Total issues for review: {len(review_items)}")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
