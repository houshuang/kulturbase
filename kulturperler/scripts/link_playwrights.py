#!/usr/bin/env python3
"""
Extract playwright names from episode descriptions and link them to plays.

Patterns to match:
- "av den [nationality] dramatikeren [Name]"
- "av [Name]" (at start or after punctuation)
- "Av [Name]"
"""

import re
import sqlite3
from pathlib import Path


def extract_playwright(description: str) -> str | None:
    """Extract playwright name from description."""
    if not description:
        return None

    # Pattern: "av den [adj] dramatikeren [Name]" or "av dramatikeren [Name]"
    match = re.search(
        r'[Aa]v (?:den )?(?:\w+ )?dramatiker(?:en|inn?a)? ([A-ZÆØÅÖÄ][a-zæøåöä]+(?:\s+[A-ZÆØÅÖÄ][a-zæøåöä]+)+)',
        description
    )
    if match:
        return match.group(1)

    # Pattern: "av forfatteren [Name]"
    match = re.search(
        r'[Aa]v (?:den )?(?:\w+ )?forfatter(?:en|inn?a)? ([A-ZÆØÅÖÄ][a-zæøåöä]+(?:\s+[A-ZÆØÅÖÄ][a-zæøåöä]+)+)',
        description
    )
    if match:
        return match.group(1)

    # Pattern: "etter ... av [Name]" (e.g., "Drama etter en novelle av Cora Sandel")
    match = re.search(
        r'[Ee]tter .+? av ([A-ZÆØÅÖÄ][a-zæøåöä]+(?:\s+[A-ZÆØÅÖÄ][a-zæøåöä]+)+)',
        description
    )
    if match:
        return match.group(1)

    # Pattern: "forfatter av stykket [Name]"
    match = re.search(
        r'forfatter (?:av stykket |)["]?([A-ZÆØÅÖÄ][a-zæøåöä]+(?:\s+[A-ZÆØÅÖÄ][a-zæøåöä]+)*)["]?',
        description
    )
    if match and len(match.group(1).split()) >= 2:
        return match.group(1)

    # Pattern at start: "Av [Name]." or after period
    match = re.search(
        r'(?:^|\. )[Aa]v ([A-ZÆØÅÖÄ][a-zæøåöä]+(?:\s+[A-ZÆØÅÖÄ][a-zæøåöä]+)+)\.',
        description
    )
    if match:
        return match.group(1)

    # Pattern: Fjernsynsteatret viser "Title" av [Name]
    match = re.search(
        r'Fjernsynsteatret (?:viser|syner) ".+?" av ([A-ZÆØÅÖÄ][a-zæøåöä]+(?:\s+[A-ZÆØÅÖÄ][a-zæøåöä]+)+)',
        description
    )
    if match:
        return match.group(1)

    # Pattern: "til ... dikt av [Name]"
    match = re.search(
        r'til .+?dikt av ([A-ZÆØÅÖÄ][a-zæøåöä]+(?:\s+[A-ZÆØÅÖÄ][a-zæøåöä]+)+)',
        description
    )
    if match:
        return match.group(1)

    # Pattern: noveller av [Name]
    match = re.search(
        r'novelle(?:r|n)? av ([A-ZÆØÅÖÄ][a-zæøåöä]+(?:\s+[A-ZÆØÅÖÄ][a-zæøåöä]+)+)',
        description
    )
    if match:
        return match.group(1)

    # Pattern: mentions playwright name directly (e.g., "Strindberg tok...")
    known_playwrights = [
        ("Strindberg", "August Strindberg"),
        ("Ibsen", "Henrik Ibsen"),
        ("Bjørnson", "Bjørnstjerne Bjørnson"),
        ("Shakespeare", "William Shakespeare"),
        ("Molière", "Molière"),
        ("Tsjekhov", "Anton Tsjekhov"),
        ("Chekhov", "Anton Tsjekhov"),
        ("Brecht", "Bertolt Brecht"),
    ]
    for short_name, full_name in known_playwrights:
        if short_name in description:
            return full_name

    return None


# Well-known plays that we can identify by title
KNOWN_PLAYS = {
    "Seks personer søker en forfatter": "Luigi Pirandello",
    "Når den ny vin blomstrer": "Bjørnstjerne Bjørnson",
    "Fugleelskerne": "Dario Fo",
    "En folkefiende": "Henrik Ibsen",
    "Vildanden": "Henrik Ibsen",
    "Hedda Gabler": "Henrik Ibsen",
    "Et dukkehjem": "Henrik Ibsen",
    "Gengangere": "Henrik Ibsen",
    "Peer Gynt": "Henrik Ibsen",
    "Brand": "Henrik Ibsen",
    "Fruen fra havet": "Henrik Ibsen",
    "John Gabriel Borkman": "Henrik Ibsen",
    "Lille Eyolf": "Henrik Ibsen",
    "Rosmersholm": "Henrik Ibsen",
    "Byggmester Solness": "Henrik Ibsen",
    "De unges forbund": "Henrik Ibsen",
    "Kongsemnerne": "Henrik Ibsen",
    "Samfundets støtter": "Henrik Ibsen",
    "Catilina": "Henrik Ibsen",
    "Gildet på Solhaug": "Henrik Ibsen",
    "Hærmændene på Helgeland": "Henrik Ibsen",
    "Kjærlighedens komedie": "Henrik Ibsen",
    "Kongs-Emnerne": "Henrik Ibsen",
    "Når vi døde vågner": "Henrik Ibsen",
    "Tre søstre": "Anton Tsjekhov",
    "Kirsebærhaven": "Anton Tsjekhov",
    "Måken": "Anton Tsjekhov",
    "Onkel Vanja": "Anton Tsjekhov",
    "Hamlet": "William Shakespeare",
    "Macbeth": "William Shakespeare",
    "Kong Lear": "William Shakespeare",
    "Othello": "William Shakespeare",
    "Romeo og Julie": "William Shakespeare",
    "En midtsommernattsdrøm": "William Shakespeare",
    "Stormen": "William Shakespeare",
    "Mye styr for ingenting": "William Shakespeare",
    "Lystige koner i Windsor": "William Shakespeare",
    "Richard III": "William Shakespeare",
    "Julius Cæsar": "William Shakespeare",
    "Erasmus Montanus": "Ludvig Holberg",
    "Jeppe på Berget": "Ludvig Holberg",
    "Den politiske kandestøber": "Ludvig Holberg",
    "Den stundesløse": "Ludvig Holberg",
    "Barselstuen": "Ludvig Holberg",
    "Maskarade": "Ludvig Holberg",
    "Den vegelsinnede": "Ludvig Holberg",
    "Tartuffe": "Molière",
    "Den innbilte syke": "Molière",
    "Den gjerrige": "Molière",
    "Misantropen": "Molière",
    "Don Juan": "Molière",
    "Frøken Julie": "August Strindberg",
    "Dødsdansen": "August Strindberg",
    "Fadren": "August Strindberg",
    "Faderen": "August Strindberg",
    "Spøksonaten": "August Strindberg",
    "Ett drömspel": "August Strindberg",
    "Fröken Julie": "August Strindberg",
    "Pelikanen": "August Strindberg",
    "Påske": "August Strindberg",
    "Glassmenasjeriet": "Tennessee Williams",
    "Sporvogn til begjær": "Tennessee Williams",
    "Katten på det varme blikktak": "Tennessee Williams",
    "Hvem er redd for Virginia Woolf?": "Edward Albee",
    "Antigone": "Sofokles",
    "Kong Oidipus": "Sofokles",
    "Elektra": "Sofokles",
    "Medea": "Euripides",
    "Vente på Godot": "Samuel Beckett",
    "Sluttspill": "Samuel Beckett",
    "Lykkelige dager": "Samuel Beckett",
}


def find_or_create_person(conn: sqlite3.Connection, name: str) -> int:
    """Find existing person or create new one. Returns person_id."""
    cursor = conn.cursor()

    # Try exact match first
    cursor.execute("SELECT id FROM persons WHERE name = ?", (name,))
    row = cursor.fetchone()
    if row:
        return row[0]

    # Try case-insensitive match
    cursor.execute("SELECT id, name FROM persons WHERE LOWER(name) = LOWER(?)", (name,))
    row = cursor.fetchone()
    if row:
        return row[0]

    # Create new person
    cursor.execute(
        "INSERT INTO persons (name) VALUES (?)",
        (name,)
    )
    return cursor.lastrowid


def main():
    script_dir = Path(__file__).parent.parent
    db_path = script_dir / "web" / "static" / "kulturperler.db"

    print("=" * 60)
    print("Linking playwrights to plays")
    print("=" * 60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Find plays without playwright that have episode descriptions
    cursor.execute("""
        SELECT DISTINCT p.id, p.title, e.description
        FROM plays p
        JOIN episodes e ON e.play_id = p.id
        WHERE p.playwright_id IS NULL
        AND e.description IS NOT NULL
        AND LENGTH(e.description) > 20
    """)

    plays_to_update = []
    for play_id, play_title, description in cursor.fetchall():
        playwright_name = None

        # First check if it's a known play by title
        if play_title in KNOWN_PLAYS:
            playwright_name = KNOWN_PLAYS[play_title]
        else:
            # Try to extract from description
            playwright_name = extract_playwright(description)

        if playwright_name:
            # Filter out obvious non-names
            if playwright_name.lower() in ['med', 'for', 'fra', 'til', 'hos']:
                continue
            if len(playwright_name.split()) < 2 and playwright_name != "Molière":
                continue
            plays_to_update.append((play_id, play_title, playwright_name, description))

    print(f"Found {len(plays_to_update)} plays with extractable playwright names")

    linked = 0
    created_persons = 0

    for play_id, play_title, playwright_name, description in plays_to_update:
        # Check if person exists
        cursor.execute("SELECT id FROM persons WHERE LOWER(name) = LOWER(?)", (playwright_name,))
        existing = cursor.fetchone()

        person_id = find_or_create_person(conn, playwright_name)

        if not existing:
            created_persons += 1
            print(f"  CREATE: {playwright_name}")

        # Update play
        cursor.execute("UPDATE plays SET playwright_id = ? WHERE id = ?", (person_id, play_id))
        print(f"  LINK: '{play_title}' -> {playwright_name}")
        linked += 1

    conn.commit()
    conn.close()

    print(f"\n{'=' * 60}")
    print("Results:")
    print(f"  Plays linked to playwright: {linked}")
    print(f"  New persons created: {created_persons}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
