#!/usr/bin/env python3
"""Parse multi-part episodes and introduction episodes."""

import re
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "kulturperler.db"


def parse_part_info(title: str) -> tuple[str | None, int | None, int | None]:
    """Extract base title and part info from title like 'Peer Gynt 1:2'."""
    # Pattern: Title X:Y where X is part number and Y is total parts
    match = re.search(r"^(.+?)\s+(\d+):(\d+)$", title.strip())
    if match:
        return match.group(1).strip(), int(match.group(2)), int(match.group(3))

    # Pattern: Title - Del X (av Y)
    match = re.search(r"^(.+?)\s*-?\s*[Dd]el\s+(\d+)(?:\s*av\s*(\d+))?", title)
    if match:
        base = match.group(1).strip()
        part = int(match.group(2))
        total = int(match.group(3)) if match.group(3) else None
        return base, part, total

    return None, None, None


def is_introduction(title: str, description: str | None) -> bool:
    """Check if episode is an introduction/making-of."""
    title_lower = title.lower()
    desc_lower = (description or "").lower()

    intro_keywords = [
        "introduksjon", "innledning", "presentasjon",
        "making of", "bak kulissene"
    ]

    for kw in intro_keywords:
        if kw in title_lower or kw in desc_lower:
            return True

    # Check specific patterns
    if "- om " in title_lower and "teatret" not in title_lower:
        return True
    if title_lower.startswith("fjernsynsteatret viste:") and "introduksjon" in title_lower:
        return True
    if title_lower.startswith("fjernsynsteatret viser - introduksjon"):
        return True

    return False


def extract_intro_target(title: str) -> str | None:
    """Extract the play name that an introduction is about."""
    # Pattern: "Fjernsynsteatret viste: X - Introduksjon"
    match = re.search(r"[Ff]jernsynsteatret\s+viste?:\s*(.+?)\s*-?\s*[Ii]ntroduksjon", title)
    if match:
        return match.group(1).strip()

    # Pattern: "Introduksjon til X"
    match = re.search(r"[Ii]ntroduksjon\s+til\s+(.+?)$", title)
    if match:
        return match.group(1).strip()

    # Pattern: "X og 'Y'" where Y is the play
    match = re.search(r'og\s*["\'](.+?)["\']', title)
    if match:
        return match.group(1).strip()

    return None


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get all episodes
    cur.execute("SELECT prf_id, title, description, play_id FROM episodes")
    episodes = cur.fetchall()

    print(f"Processing {len(episodes)} episodes...")

    parts_updated = 0
    intros_found = 0
    intros_linked = 0

    for ep in episodes:
        prf_id = ep["prf_id"]
        title = ep["title"]
        description = ep["description"]

        # Check for part info
        base_title, part_num, total_parts = parse_part_info(title)
        if part_num:
            cur.execute("""
                UPDATE episodes
                SET part_number = ?, total_parts = ?
                WHERE prf_id = ?
            """, (part_num, total_parts, prf_id))
            parts_updated += 1
            print(f"  Part {part_num}/{total_parts or '?'}: {title}")

        # Check for introduction
        if is_introduction(title, description):
            cur.execute("""
                UPDATE episodes
                SET is_introduction = 1
                WHERE prf_id = ?
            """, (prf_id,))
            intros_found += 1

            # Try to link to parent play
            target_name = extract_intro_target(title)
            if target_name:
                # Find matching play
                cur.execute("""
                    SELECT id FROM plays
                    WHERE title LIKE ? OR title LIKE ?
                    LIMIT 1
                """, (f"%{target_name}%", f"{target_name}%"))
                play = cur.fetchone()
                if play:
                    cur.execute("""
                        UPDATE episodes
                        SET play_id = ?
                        WHERE prf_id = ?
                    """, (play["id"], prf_id))
                    intros_linked += 1
                    print(f"  Intro linked: {title} -> play_id {play['id']}")
                else:
                    print(f"  Intro (unlinked): {title} (target: {target_name})")
            else:
                print(f"  Intro (no target): {title}")

    conn.commit()
    conn.close()

    print(f"\nDone!")
    print(f"  Parts updated: {parts_updated}")
    print(f"  Introductions found: {intros_found}")
    print(f"  Introductions linked: {intros_linked}")


if __name__ == "__main__":
    main()
