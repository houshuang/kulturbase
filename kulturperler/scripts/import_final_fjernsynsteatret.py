#!/usr/bin/env python3
"""
Import remaining Fjernsynsteatret performances from Archive.org.
These are confirmed performances that don't exist in the NRK database.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
import re

# Confirmed Fjernsynsteatret performances to import
PERFORMANCES = [
    {
        "title": "Bård Skolemesters historie",
        "archive_url": "https://archive.org/details/NRKTV-FTEA007281-199103058-ST",
        "nrk_url": "https://tv.nrk.no/se?v=FTEA007281",
        "prf_id": "FTEA007281",
        "description": "Marie Louise Tank leser historien om Bård skolemester fra romanen \"En glad gutt\" av Bjørnstjerne Bjørnson. Sendt i Fjernsynsteatret, første gang i 1982.",
        "year": 1982,
    },
    {
        "title": "Ælle menneskja mine (Alle menneskene mine)",
        "archive_url": "https://archive.org/details/NRKTV-FTEA004789-AR-199049296",
        "nrk_url": "https://tv.nrk.no/se?v=FTEA004789",
        "prf_id": "FTEA004789",
        "description": "Teateroppsetning fra NRKs faste scene, Fjernsynsteatret.",
        "year": 1990,
    },
    {
        "title": "Skuggen av ein helt (Skyggen av en helt)",
        "archive_url": "https://archive.org/details/NRKTV-FTEA001272-AR-199311328",
        "nrk_url": "https://tv.nrk.no/se?v=FTEA001272",
        "prf_id": "FTEA001272",
        "description": "Fjernsynsteatret syner \"Skuggen av ein helt\" av Sean O'Casey. (The shadow of a gunman). Omsett av Hartvig Kiran.",
        "year": 1972,
    },
    {
        "title": "Meister Olof (Mester Olof)",
        "archive_url": "https://archive.org/details/NRKTV-FTEA000477AU",
        "archive_url_part2": "https://archive.org/details/NRKTV-FTEA000477BU",
        "nrk_url": "https://tv.nrk.no/se?v=FTEA000477",
        "prf_id": "FTEA000477",
        "description": "Fjernsynsteatret viser \"Meister Olof\" av August Strindberg. (Mäster Olof). Omsett av Bjørn Endreson.",
        "year": 1977,
    },
    {
        "title": "Spel utan ord (Spill uten ord)",
        "archive_url": "https://archive.org/details/NRKTV-FTEA006487-AR-199305268",
        "nrk_url": "https://tv.nrk.no/se?v=FTEA006487",
        "prf_id": "FTEA006487",
        "description": "Teateroppsetning fra NRKs faste scene, Fjernsynsteatret.",
        "year": 1988,
    },
    {
        "title": "Skolkamerater (Skolekamerater)",
        "archive_url": "https://archive.org/details/NRKTV-FTEA000062-AR-199416101",
        "nrk_url": "https://tv.nrk.no/se?v=FTEA62003162",
        "prf_id": "FTEA62003162",
        "description": "Stig Järell leser en monolog av Kar de Mumma - om gjensyn med en gammel skolekamerat. Gjestespill fra Lilla Teatern, Helsinki.",
        "year": 1962,
    },
    {
        "title": "Parkbänk (Parkbenk)",
        "archive_url": "https://archive.org/details/NRKTV-FTEA000062-AR-199416089",
        "nrk_url": "https://tv.nrk.no/se?v=FTEA62001162",
        "prf_id": "FTEA62001162",
        "description": "Drama av den finske dramatikeren Solveig von Schoultz. Gjestespill fra Lilla Teatern, Helsinki. Et tilfeldig møte mellom to mennesker.",
        "year": 1962,
    },
    {
        "title": "Lat ugraset vekse (La ugresset vokse)",
        "archive_url": "https://archive.org/details/NRKTV-FTEA001972-AR-199212243",
        "nrk_url": "https://tv.nrk.no/se?v=FTEA001972",
        "prf_id": "FTEA001972",
        "description": "Fjernsynsteatret syner \"Lat ugraset vekse\" av Olle Mattson. Det er byen sin krig mot bygda.",
        "year": 1973,
    },
    {
        "title": "Kva Joe? (Hva Joe?)",
        "archive_url": "https://archive.org/details/NRKTV-FTEA001976-AR-199204039",
        "nrk_url": "https://tv.nrk.no/se?v=FTEA001976",
        "prf_id": "FTEA001976",
        "description": "Fjernsynsteatret viser \"Kva Joe?\" av Samuel Beckett. Becketts første TV-spel, enakter skrevet 1965.",
        "year": 1977,
    },
    {
        "title": "gnr",
        "archive_url": "https://archive.org/details/NRKTV-FTEA006190-AR-199305380",
        "nrk_url": "https://tv.nrk.no/se?v=FTEA006190",
        "prf_id": "FTEA006190",
        "description": "Av den danske forfatteren Vita Andersen. En ung jente har lørdagsfri og skal planlegge dagen så den får mening og gjør henne glad.",
        "year": 1991,
    },
    {
        "title": "Nederlaget",
        "archive_url": "https://archive.org/details/NRKTV-FTEA00010066-AR-199316241",
        "nrk_url": "https://tv.nrk.no/se?v=FTEA66000066",
        "prf_id": "FTEA66000066",
        "description": "Fjernsynsteatret viser \"Nederlaget\" av Nordahl Grieg. Skuespill fra 1937.",
        "year": 1966,
    },
    {
        "title": "Kodemus",
        "archive_url": "https://archive.org/details/NRKTV-FTEA001271-AR-199001040",
        "nrk_url": "https://tv.nrk.no/se?v=FTEA001271",
        "prf_id": "FTEA001271",
        "description": "Fjernsynsteatret viser \"Kodémus\" av Tor Åge Bringsværd. Et norsk fjernsynsspill, science fiction.",
        "year": 1971,
    },
]


def main():
    script_dir = Path(__file__).parent.parent
    db_path = script_dir / "web" / "static" / "kulturperler.db"

    print("=" * 60)
    print("Importing remaining Fjernsynsteatret performances")
    print("=" * 60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    added = 0
    skipped = 0

    for perf in PERFORMANCES:
        prf_id = perf["prf_id"]
        title = perf["title"]

        # Check if already exists
        cursor.execute("SELECT 1 FROM episodes WHERE prf_id = ?", (prf_id,))
        if cursor.fetchone():
            print(f"  SKIP (exists): {title}")
            skipped += 1
            continue

        print(f"  ADD: {title} ({prf_id})")

        # Insert episode
        cursor.execute("""
            INSERT INTO episodes (prf_id, title, description, year, nrk_url, medium, source)
            VALUES (?, ?, ?, ?, ?, 'tv', 'archive')
        """, (prf_id, title, perf.get("description"), perf.get("year"), perf.get("nrk_url")))

        # Add Archive.org as primary resource
        cursor.execute("""
            INSERT INTO external_resources (url, title, type, description, added_date)
            VALUES (?, ?, 'archive_primary', ?, ?)
        """, (perf["archive_url"], title, perf.get("description"), datetime.now().isoformat()))

        resource_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO episode_resources (episode_id, resource_id)
            VALUES (?, ?)
        """, (prf_id, resource_id))

        # If there's a part 2, add that as well
        if perf.get("archive_url_part2"):
            cursor.execute("""
                INSERT INTO external_resources (url, title, type, description, added_date)
                VALUES (?, ?, 'archive_primary', ?, ?)
            """, (perf["archive_url_part2"], f"{title} (Part 2)", perf.get("description"), datetime.now().isoformat()))

            resource_id = cursor.lastrowid
            cursor.execute("""
                INSERT INTO episode_resources (episode_id, resource_id)
                VALUES (?, ?)
            """, (prf_id, resource_id))

        added += 1

    conn.commit()
    conn.close()

    print(f"\n{'=' * 60}")
    print("Results:")
    print(f"  Added: {added}")
    print(f"  Skipped: {skipped}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
