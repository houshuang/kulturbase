#!/usr/bin/env python3
"""
Fetch bios for playwrights from Wikipedia.
"""

import sqlite3
import time
import urllib.parse
import urllib.request
import json
from pathlib import Path


def fetch_wikipedia_summary(name: str, lang: str = "no") -> str | None:
    """Fetch summary from Wikipedia API."""
    import subprocess

    # Try Norwegian Wikipedia first, then English
    for wiki_lang in [lang, "en"]:
        try:
            encoded_name = name.replace(" ", "_")
            url = f"https://{wiki_lang}.wikipedia.org/api/rest_v1/page/summary/{encoded_name}"

            result = subprocess.run(
                ["curl", "-s", "-H", "User-Agent: KulturperlerBot/1.0", url],
                capture_output=True,
                text=True,
                timeout=15
            )

            if result.returncode == 0 and result.stdout:
                data = json.loads(result.stdout)
                if data.get("type") == "standard" and data.get("extract"):
                    return data["extract"]
        except Exception as e:
            pass

    return None


def main():
    script_dir = Path(__file__).parent.parent
    db_path = script_dir / "web" / "static" / "kulturperler.db"

    print("=" * 60)
    print("Fetching bios for playwrights")
    print("=" * 60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get playwrights without bios
    cursor.execute("""
        SELECT DISTINCT p.id, p.name
        FROM persons p
        WHERE p.id IN (SELECT DISTINCT playwright_id FROM plays WHERE playwright_id IS NOT NULL)
        AND (p.bio IS NULL OR p.bio = '')
        ORDER BY p.name
    """)

    playwrights = cursor.fetchall()
    print(f"Found {len(playwrights)} playwrights without bios")

    updated = 0
    not_found = []

    for person_id, name in playwrights:
        print(f"  Fetching: {name}...", end=" ", flush=True)

        bio = fetch_wikipedia_summary(name)

        if bio:
            # Truncate if too long
            if len(bio) > 2000:
                bio = bio[:1997] + "..."

            cursor.execute("UPDATE persons SET bio = ? WHERE id = ?", (bio, person_id))
            print("OK")
            updated += 1
        else:
            print("not found")
            not_found.append(name)

        time.sleep(0.5)  # Be nice to Wikipedia

    conn.commit()
    conn.close()

    print(f"\n{'=' * 60}")
    print("Results:")
    print(f"  Bios updated: {updated}")
    print(f"  Not found: {len(not_found)}")
    if not_found:
        print(f"\nNot found on Wikipedia:")
        for name in not_found:
            print(f"  - {name}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
