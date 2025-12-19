#!/usr/bin/env python3
"""
Merge duplicate playwrights and fetch bios from English Wikipedia for those missing.
Uses curl to avoid SSL issues. Translates English bios to Norwegian.
"""

import sqlite3
import subprocess
import json
import time
import re
import urllib.parse
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "static" / "kulturperler.db"

# Duplicate merges: (keep_id, merge_id)
DUPLICATES = [
    (2126, 3130),  # Anton Tsjekhov, Anton Tsjekov
    (2589, 2591),  # C S Forester, C.S. Forester
    (1449, 2231),  # Johannes Solberg, Johs Solberg
    (1783, 2454),  # John W Wainwright, John Wainwright
    (2924, 2927),  # K M Peyton, K. M. Peyton
    (2020, 1996),  # R.D. Wingfield, Rodney D Wingfield
]

# English Wikipedia name mappings for playwrights who need English lookup
ENGLISH_NAMES = {
    "Alistar MacLeans roman ": "Alistair MacLean",
    "Babbis Friis Baastad": "Babis Friis-Baastad",
    "Barbara Sleigh": "Barbara Sleigh",
    "Bill Cleaver": "Bill Cleaver (author)",
    "C S Forester": "C. S. Forester",
    "Charlotte B. Chorpenning": "Charlotte Chorpenning",
    "Dennis McIntyre": "Dennis McIntyre (playwright)",
    "Dorothy Sterling": "Dorothy Sterling",
    "E Nesbit": "E. Nesbit",
    "Edward Boyd": "Edward Boyd (scriptwriter)",
    "Ethel Lina White": "Ethel Lina White",
    "Frances Burnett": "Frances Hodgson Burnett",
    "Francis Durbridge": "Francis Durbridge",
    "Franz Xavier Kroetz": "Franz Xaver Kroetz",
    "Friedrich Glauser": "Friedrich Glauser",
    "Gavin Lyall": "Gavin Lyall",
    "Giles Cooper": "Giles Cooper (playwright)",
    "Gina Ruck-Pauquèt": "Gina Ruck-Pauquèt",
    "Ivy Litvinov": "Ivy Litvinov",
    "John W Wainwright": "John Wainwright (author)",
    "K M Peyton": "K. M. Peyton",
    "Kaptein Marryat": "Frederick Marryat",
    "Leslie Charteris": "Leslie Charteris",
    "Martin B. Duberman": "Martin Duberman",
    "Michelle Magorian": "Michelle Magorian",
    "P D James": "P. D. James",
    "Ponson du Terrail": "Pierre Alexis Ponson du Terrail",
    "Quentin Patrick": "Q. Patrick",
    "R.D. Wingfield": "R. D. Wingfield",
    "Roy Horniman": "Roy Horniman",
    "Ruth Underhill": "Ruth Murray Underhill",
    "Samuel Scoville jr.": "Samuel Scoville Jr.",
    "Samuel W Taylor": "Samuel W. Taylor",
    "Tom Kristensen": "Tom Kristensen (author)",
    "Vera Caspary": "Vera Caspary",
}


def merge_duplicates(conn: sqlite3.Connection):
    """Merge duplicate person entries."""
    cursor = conn.cursor()

    for keep_id, merge_id in DUPLICATES:
        cursor.execute("SELECT name FROM persons WHERE id = ?", (keep_id,))
        keep_row = cursor.fetchone()
        cursor.execute("SELECT name FROM persons WHERE id = ?", (merge_id,))
        merge_row = cursor.fetchone()

        if not keep_row or not merge_row:
            print(f"  Skipping {keep_id}/{merge_id} - one not found")
            continue

        print(f"Merging '{merge_row[0]}' ({merge_id}) into '{keep_row[0]}' ({keep_id})")

        # Update plays to point to keep_id
        cursor.execute("UPDATE plays SET playwright_id = ? WHERE playwright_id = ?", (keep_id, merge_id))

        # Update episode_persons
        cursor.execute("UPDATE episode_persons SET person_id = ? WHERE person_id = ?", (keep_id, merge_id))

        # Update performance_persons if exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='performance_persons'")
        if cursor.fetchone():
            cursor.execute("UPDATE performance_persons SET person_id = ? WHERE person_id = ?", (keep_id, merge_id))

        # Delete the merged person
        cursor.execute("DELETE FROM persons WHERE id = ?", (merge_id,))

    conn.commit()
    print(f"Merged {len(DUPLICATES)} duplicate pairs")


def fetch_english_wikipedia(title: str) -> tuple[str | None, str | None]:
    """Fetch extract from English Wikipedia using curl."""
    encoded_title = urllib.parse.quote(title.replace(" ", "_"))
    api_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_title}"

    try:
        result = subprocess.run(
            ['curl', '-s', '-L', '-H', 'User-Agent: Kulturperler/1.0', api_url],
            capture_output=True,
            text=True,
            timeout=15
        )

        if result.returncode != 0:
            return None, None

        data = json.loads(result.stdout)

        if data.get('type') == 'https://mediawiki.org/wiki/HyperSwitch/errors/not_found':
            return None, None

        extract = data.get('extract', '')
        page_url = data.get('content_urls', {}).get('desktop', {}).get('page', '')

        # Limit to first 3-4 sentences
        if extract and len(extract) > 450:
            sentences = extract.split('. ')
            short_extract = ''
            for sentence in sentences:
                if len(short_extract) + len(sentence) < 450:
                    short_extract += sentence + '. '
                else:
                    break
            extract = short_extract.strip()

        return extract if extract else None, page_url if page_url else None

    except Exception as e:
        print(f"  Error: {e}")
        return None, None


def translate_to_norwegian(bio_en: str, name: str) -> str:
    """Create a Norwegian summary from English bio."""
    if not bio_en:
        return ""

    # Extract birth/death years
    years_match = re.search(r'\((\d{4})\s*[–-]\s*(\d{4})\)', bio_en)
    birth_death = ""
    if years_match:
        birth_death = f"({years_match.group(1)}–{years_match.group(2)})"
    else:
        birth_match = re.search(r'\(born\s+(\d{4})\)', bio_en, re.I)
        if birth_match:
            birth_death = f"(født {birth_match.group(1)})"

    # Determine nationality
    nationality_map = {
        'american': 'amerikansk',
        'british': 'britisk',
        'english': 'engelsk',
        'scottish': 'skotsk',
        'irish': 'irsk',
        'welsh': 'walisisk',
        'french': 'fransk',
        'german': 'tysk',
        'austrian': 'østerriksk',
        'swedish': 'svensk',
        'danish': 'dansk',
        'norwegian': 'norsk',
        'russian': 'russisk',
        'soviet': 'sovjetisk',
        'italian': 'italiensk',
        'spanish': 'spansk',
        'polish': 'polsk',
        'czech': 'tsjekkisk',
        'hungarian': 'ungarsk',
        'greek': 'gresk',
        'dutch': 'nederlandsk',
        'belgian': 'belgisk',
        'swiss': 'sveitsisk',
        'canadian': 'kanadisk',
        'australian': 'australsk',
        'new zealand': 'newzealandsk',
        'south african': 'sørafrikansk',
        'chilean': 'chilensk',
        'argentinian': 'argentinsk',
        'brazilian': 'brasiliansk',
        'finnish': 'finsk',
        'romanian': 'rumensk',
        'serbian': 'serbisk',
        'croatian': 'kroatisk',
        'ukrainian': 'ukrainsk',
        'japanese': 'japansk',
    }

    nationality = ""
    bio_lower = bio_en.lower()
    for eng, nor in nationality_map.items():
        if eng in bio_lower:
            nationality = nor
            break

    # Determine profession(s)
    professions = []
    profession_map = {
        'playwright': 'dramatiker',
        'dramatist': 'dramatiker',
        'screenwriter': 'manusforfatter',
        'novelist': 'romanforfatter',
        'poet': 'dikter',
        'crime writer': 'krimforfatter',
        'mystery writer': 'krimforfatter',
        'detective fiction': 'krimforfatter',
        'children\'s writer': 'barnebokforfatter',
        'children\'s author': 'barnebokforfatter',
        'science fiction': 'science fiction-forfatter',
        'writer': 'forfatter',
        'author': 'forfatter',
        'journalist': 'journalist',
    }

    for eng, nor in profession_map.items():
        if eng in bio_lower and nor not in professions:
            professions.append(nor)
            if len(professions) >= 2:
                break

    if not professions:
        professions = ['forfatter']

    # Build Norwegian bio
    if len(professions) > 1:
        prof_str = ' og '.join(professions[:2])
    else:
        prof_str = professions[0]

    # Check if deceased
    is_deceased = bool(years_match) or 'was a' in bio_lower or 'died' in bio_lower
    verb = "var" if is_deceased else "er"

    # Create base bio
    if nationality:
        bio_no = f"{name} {birth_death} {verb} en {nationality} {prof_str}.".replace("  ", " ").strip()
    else:
        bio_no = f"{name} {birth_death} {verb} en {prof_str}.".replace("  ", " ").strip()

    # Try to extract notable works
    work_match = re.search(r'(?:best known for|known for|famous for)[^.]*?"([^"]+)"', bio_en, re.I)
    if not work_match:
        work_match = re.search(r'(?:best known for|known for|famous for)[^.]*?\'([^\']+)\'', bio_en, re.I)

    if work_match:
        work = work_match.group(1)
        bio_no += f" Kjent for «{work}»."

    return bio_no


def fetch_missing_bios(conn: sqlite3.Connection):
    """Fetch bios from English Wikipedia for playwrights still missing them."""
    cursor = conn.cursor()

    # Get playwrights without bios
    cursor.execute("""
        SELECT DISTINCT p.id, p.name
        FROM persons p
        JOIN plays pl ON p.id = pl.playwright_id
        WHERE p.bio IS NULL OR p.bio = ''
        ORDER BY p.name
    """)

    playwrights = cursor.fetchall()
    print(f"\nFound {len(playwrights)} playwrights without bios")

    updated = 0
    for person_id, name in playwrights:
        # Check if we have an English name mapping
        english_name = ENGLISH_NAMES.get(name)

        if not english_name:
            # Try the name directly
            english_name = name

        print(f"Fetching: {name} -> {english_name}...", end=" ", flush=True)

        bio_en, wiki_url = fetch_english_wikipedia(english_name)

        if bio_en:
            # Translate to Norwegian
            translated_bio = translate_to_norwegian(bio_en, name)

            if translated_bio:
                cursor.execute(
                    "UPDATE persons SET bio = ?, wikipedia_url = COALESCE(wikipedia_url, ?) WHERE id = ?",
                    (translated_bio, wiki_url, person_id)
                )
                updated += 1
                print(f"OK ({len(translated_bio)} chars)")
            else:
                print("Translation failed")
        else:
            print("Not found")

        time.sleep(0.3)

    conn.commit()
    print(f"\nUpdated {updated} playwrights with translated English bios")


def main():
    print("=" * 60)
    print("Merging duplicates and fetching English Wikipedia bios")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    try:
        print("\n--- Merging duplicates ---")
        merge_duplicates(conn)

        print("\n--- Fetching English Wikipedia bios ---")
        fetch_missing_bios(conn)
    finally:
        conn.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
