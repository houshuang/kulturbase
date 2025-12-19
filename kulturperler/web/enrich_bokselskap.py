#!/usr/bin/env python3
"""
Enrich plays database with bokselskap.no digital text links.

This script:
1. Uses pre-scraped play data from bokselskap.no
2. Matches them to existing plays in the database by title + playwright
3. Inserts links into the play_external_links table with type='bokselskap'
"""

import sqlite3
import re
from pathlib import Path

# Bokselskap plays data (from the plan file)
BOKSELSKAP_PLAYS = [
    {"title": "Den Politiske Kandstøber", "author": "Ludvig Holberg", "url": "https://www.bokselskap.no/boker/kandstober"},
    {"title": "Jeppe paa Bierget", "author": "Ludvig Holberg", "url": "https://www.bokselskap.no/boker/jeppe"},
    {"title": "Erasmus Montanus", "author": "Ludvig Holberg", "url": "https://www.bokselskap.no/boker/erasmus"},
    {"title": "Jomfrue Pecunia", "author": "Johan Nordahl Brun", "url": "https://www.bokselskap.no/boker/jomfruepecunia"},
    {"title": "Zarine", "author": "Johan Nordahl Brun", "url": "https://www.bokselskap.no/boker/zarine"},
    {"title": "Kierlighed uden Strømper", "author": "Johan Herman Wessel", "url": "https://www.bokselskap.no/boker/kierlighedudenstromper"},
    {"title": "Republikken paa Øen", "author": "Johan Nordahl Brun", "url": "https://www.bokselskap.no/boker/republikken"},
    {"title": "Terje Vigen", "author": "Henrik Ibsen", "url": "https://www.bokselskap.no/boker/terjevigen"},
    {"title": "Sigurd Slembe", "author": "Bjørnstjerne Bjørnson", "url": "https://www.bokselskap.no/boker/sigurdslembe"},
    {"title": "De Nygifte", "author": "Bjørnstjerne Bjørnson", "url": "https://www.bokselskap.no/boker/denygifte"},
    {"title": "Brand", "author": "Henrik Ibsen", "url": "https://www.bokselskap.no/boker/brand"},
    {"title": "Peer Gynt", "author": "Henrik Ibsen", "url": "https://www.bokselskap.no/boker/peergynt"},
    {"title": "En fallit", "author": "Bjørnstjerne Bjørnson", "url": "https://www.bokselskap.no/boker/fallit"},
    {"title": "Et dukkehjem", "author": "Henrik Ibsen", "url": "https://www.bokselskap.no/boker/dukkehjem"},
    {"title": "Leonarda", "author": "Bjørnstjerne Bjørnson", "url": "https://www.bokselskap.no/boker/leonarda"},
    {"title": "Det ny system", "author": "Bjørnstjerne Bjørnson", "url": "https://www.bokselskap.no/boker/detnysystem"},
    {"title": "Gengangere", "author": "Henrik Ibsen", "url": "https://www.bokselskap.no/boker/gengangere"},
    {"title": "En folkefiende", "author": "Henrik Ibsen", "url": "https://www.bokselskap.no/boker/folkefiende"},
    {"title": "Over ævne, første stykke", "author": "Bjørnstjerne Bjørnson", "url": "https://www.bokselskap.no/boker/overaevne1"},
    {"title": "En hanske", "author": "Bjørnstjerne Bjørnson", "url": "https://www.bokselskap.no/boker/hanske"},
    {"title": "Vildanden", "author": "Henrik Ibsen", "url": "https://www.bokselskap.no/boker/vildanden"},
    {"title": "Tante Ulrikke", "author": "Gunnar Heiberg", "url": "https://www.bokselskap.no/boker/tanteulrikke"},
    {"title": "Geografi og kærlighed", "author": "Bjørnstjerne Bjørnson", "url": "https://www.bokselskap.no/boker/geografi"},
    {"title": "Rosmersholm", "author": "Henrik Ibsen", "url": "https://www.bokselskap.no/boker/rosmersholm"},
    {"title": "Fruen fra havet", "author": "Henrik Ibsen", "url": "https://www.bokselskap.no/boker/fruenfrahavet"},
    {"title": "Hedda Gabler", "author": "Henrik Ibsen", "url": "https://www.bokselskap.no/boker/hedda"},
    {"title": "Bygmester Solness", "author": "Henrik Ibsen", "url": "https://www.bokselskap.no/boker/bygmester"},
    {"title": "Over ævne, andet stykke", "author": "Bjørnstjerne Bjørnson", "url": "https://www.bokselskap.no/boker/overaevne2"},
    {"title": "Paul Lange og Tora Parsberg", "author": "Bjørnstjerne Bjørnson", "url": "https://www.bokselskap.no/boker/langeogparsberg"},
    {"title": "Lilje Gunda og andre forteljingar", "author": "Oskar Braaten", "url": "https://www.bokselskap.no/boker/liljegunda"},
    {"title": "Sorgenfri", "author": "Oskar Braaten", "url": "https://www.bokselskap.no/boker/sorgenfri"},
    {"title": "Ulvehiet", "author": "Oskar Braaten", "url": "https://www.bokselskap.no/boker/ulvehiet"},
    {"title": "Den store barnedåpen", "author": "Oskar Braaten", "url": "https://www.bokselskap.no/boker/barnedaapen"},
]

def normalize_title(title: str) -> str:
    """Normalize title for matching: lowercase, remove punctuation, normalize whitespace."""
    title = title.lower()
    # Remove punctuation including Norwegian special chars that might vary
    title = re.sub(r'[^\w\s]', '', title)
    # Normalize whitespace
    title = re.sub(r'\s+', ' ', title).strip()
    return title

def normalize_author(author: str) -> str:
    """Extract last name for author matching."""
    parts = author.split()
    return parts[-1].lower() if parts else ""

def get_playwright_for_play(cursor, play_id: int) -> str:
    """Get playwright name for a play via episode_persons."""
    cursor.execute("""
        SELECT DISTINCT per.name
        FROM episodes e
        JOIN episode_persons ep ON e.prf_id = ep.episode_id
        JOIN persons per ON ep.person_id = per.id
        WHERE e.play_id = ? AND ep.role = 'playwright'
        LIMIT 1
    """, (play_id,))
    result = cursor.fetchone()
    return result["name"] if result else ""

def match_plays(db_path: str):
    """Match bokselskap plays to database plays and insert into play_external_links."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get all plays
    cursor.execute("SELECT id, title, original_title FROM plays")
    db_plays = cursor.fetchall()

    matched = 0
    unmatched = []

    # Clear existing bokselskap links first
    cursor.execute("DELETE FROM play_external_links WHERE type = 'bokselskap'")
    print(f"Cleared existing bokselskap links\n")

    for bok_play in BOKSELSKAP_PLAYS:
        bok_title_norm = normalize_title(bok_play["title"])
        bok_author_norm = normalize_author(bok_play["author"])

        best_match = None
        best_score = 0

        for db_play in db_plays:
            db_title_norm = normalize_title(db_play["title"] or "")
            db_orig_norm = normalize_title(db_play["original_title"] or "")

            # Calculate title match score
            score = 0
            if bok_title_norm == db_title_norm or bok_title_norm == db_orig_norm:
                score = 100  # Exact match
            elif db_title_norm and bok_title_norm in db_title_norm:
                score = 70  # Bokselskap title is substring of DB title
            elif db_title_norm and db_title_norm in bok_title_norm:
                score = 60  # DB title is substring of Bokselskap title
            elif db_orig_norm and bok_title_norm in db_orig_norm:
                score = 70  # Match in original title
            elif db_orig_norm and db_orig_norm in bok_title_norm:
                score = 60

            # If we have a decent title match, check playwright
            if score >= 60:
                playwright = get_playwright_for_play(cursor, db_play["id"])
                if playwright:
                    db_author_norm = normalize_author(playwright)
                    if bok_author_norm == db_author_norm:
                        score += 50  # Bonus for matching playwright

            if score > best_score:
                best_score = score
                best_match = (db_play, playwright if score >= 110 else "")

        # Accept matches with score >= 60 (title match) or >= 110 (title + author)
        if best_score >= 60:
            db_play, playwright_name = best_match
            cursor.execute("""
                INSERT INTO play_external_links (play_id, url, title, type, description, access_note)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                db_play["id"],
                bok_play["url"],
                "Bokselskap.no",
                "bokselskap",
                "Les hele teksten gratis",
                None
            ))
            author_info = f" ({bok_play['author']})" if playwright_name else ""
            print(f"✓ [{best_score:3d}] {bok_play['title']}{author_info} -> {db_play['title']} (ID: {db_play['id']})")
            matched += 1
        else:
            unmatched.append(bok_play)

    conn.commit()
    conn.close()

    print(f"\n{'='*60}")
    print(f"Matched: {matched}/{len(BOKSELSKAP_PLAYS)}")
    print(f"{'='*60}")

    if unmatched:
        print(f"\nUnmatched plays from bokselskap.no:")
        for play in unmatched:
            print(f"  - {play['title']} ({play['author']})")
    else:
        print("\nAll plays matched successfully!")

if __name__ == "__main__":
    db_path = Path(__file__).parent / "static" / "kulturperler.db"
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        exit(1)

    print(f"Enriching database at: {db_path}")
    print(f"Processing {len(BOKSELSKAP_PLAYS)} plays from bokselskap.no\n")
    match_plays(str(db_path))
