#!/usr/bin/env python3
"""
Enrich plays and playwrights with data from Wikidata.
Uses SPARQL queries to find playwrights and their works.
"""

import sqlite3
import requests
import time
import re
from urllib.parse import quote

DB_PATH = 'static/kulturperler.db'
WIKIDATA_SPARQL = 'https://query.wikidata.org/sparql'

def sparql_query(query):
    """Execute a SPARQL query against Wikidata."""
    headers = {
        'User-Agent': 'Kulturperler/1.0 (educational project)',
        'Accept': 'application/json'
    }
    params = {'query': query, 'format': 'json'}
    response = requests.get(WIKIDATA_SPARQL, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    return response.json()

def get_playwright_by_name(name):
    """Find playwright in Wikidata by name."""
    # Search for playwright/dramatist
    query = f"""
    SELECT ?person ?personLabel ?birthYear ?deathYear ?wikipedia ?sceneweb WHERE {{
      ?person wdt:P106 wd:Q214917 .  # occupation: playwright
      ?person rdfs:label "{name}"@nb .
      OPTIONAL {{ ?person wdt:P569 ?birthDate . BIND(YEAR(?birthDate) AS ?birthYear) }}
      OPTIONAL {{ ?person wdt:P570 ?deathDate . BIND(YEAR(?deathDate) AS ?deathYear) }}
      OPTIONAL {{
        ?wikipedia schema:about ?person .
        ?wikipedia schema:isPartOf <https://no.wikipedia.org/> .
      }}
      OPTIONAL {{ ?person wdt:P4871 ?sceneweb . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "nb,no,en". }}
    }}
    LIMIT 1
    """
    try:
        results = sparql_query(query)
        if results['results']['bindings']:
            return results['results']['bindings'][0]
    except Exception as e:
        print(f"    Error searching for {name}: {e}")

    # Try Norwegian variant (no) label
    query = f"""
    SELECT ?person ?personLabel ?birthYear ?deathYear ?wikipedia ?sceneweb WHERE {{
      ?person wdt:P106 wd:Q214917 .  # occupation: playwright
      ?person rdfs:label "{name}"@no .
      OPTIONAL {{ ?person wdt:P569 ?birthDate . BIND(YEAR(?birthDate) AS ?birthYear) }}
      OPTIONAL {{ ?person wdt:P570 ?deathDate . BIND(YEAR(?deathDate) AS ?deathYear) }}
      OPTIONAL {{
        ?wikipedia schema:about ?person .
        ?wikipedia schema:isPartOf <https://no.wikipedia.org/> .
      }}
      OPTIONAL {{ ?person wdt:P4871 ?sceneweb . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "nb,no,en". }}
    }}
    LIMIT 1
    """
    try:
        results = sparql_query(query)
        if results['results']['bindings']:
            return results['results']['bindings'][0]
    except:
        pass

    return None

def get_play_by_title(title, playwright_name=None):
    """Find play in Wikidata by title."""
    # Search for literary work with title
    filter_clause = ""
    if playwright_name:
        filter_clause = f'?work wdt:P50 ?author . ?author rdfs:label "{playwright_name}"@nb .'

    query = f"""
    SELECT ?work ?workLabel ?year ?authorLabel ?authorId WHERE {{
      ?work wdt:P31/wdt:P279* wd:Q7725634 .  # instance of: literary work
      ?work rdfs:label "{title}"@nb .
      {filter_clause}
      OPTIONAL {{ ?work wdt:P577 ?pubDate . BIND(YEAR(?pubDate) AS ?year) }}
      OPTIONAL {{ ?work wdt:P50 ?authorId . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "nb,no,en". }}
    }}
    LIMIT 1
    """
    try:
        results = sparql_query(query)
        if results['results']['bindings']:
            return results['results']['bindings'][0]
    except Exception as e:
        print(f"    Error searching for {title}: {e}")

    return None

def get_known_playwrights():
    """Get well-known playwrights with NRK Fjernsynsteatret productions."""
    query = """
    SELECT ?person ?personLabel ?birthYear ?deathYear ?wikipedia ?wikidata_id WHERE {
      VALUES ?person {
        wd:Q34741 wd:Q47132 wd:Q36661 wd:Q194280 wd:Q319627
        wd:Q185048 wd:Q23685 wd:Q38392 wd:Q157322 wd:Q165534
        wd:Q708359 wd:Q57429 wd:Q36153 wd:Q82070 wd:Q42511
        wd:Q206685 wd:Q9044 wd:Q7729 wd:Q192 wd:Q37 wd:Q1345358
      }
      ?person wdt:P569 ?birthDate . BIND(YEAR(?birthDate) AS ?birthYear)
      OPTIONAL { ?person wdt:P570 ?deathDate . BIND(YEAR(?deathDate) AS ?deathYear) }
      OPTIONAL {
        ?wikipedia schema:about ?person .
        ?wikipedia schema:isPartOf <https://no.wikipedia.org/> .
      }
      BIND(REPLACE(STR(?person), "http://www.wikidata.org/entity/", "") AS ?wikidata_id)
      SERVICE wikibase:label { bd:serviceParam wikibase:language "nb,no,en". }
    }
    """
    try:
        results = sparql_query(query)
        return results['results']['bindings']
    except Exception as e:
        print(f"Error getting playwrights: {e}")
        return []

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # First, let's add some known playwrights
    known_playwrights = [
        # (name, wikidata_id, birth_year, death_year)
        ('Ludvig Holberg', 'Q34741', 1684, 1754),
        ('Henrik Ibsen', 'Q36661', 1828, 1906),
        ('August Strindberg', 'Q7724', 1849, 1912),
        ('William Shakespeare', 'Q692', 1564, 1616),
        ('Anton Tsjekhov', 'Q5685', 1860, 1904),
        ('Sofokles', 'Q7235', -497, -406),
        ('Euripides', 'Q48305', -480, -406),
        ('Molière', 'Q687', 1622, 1673),
        ('Samuel Beckett', 'Q37327', 1906, 1989),
        ('Bjørnstjerne Bjørnson', 'Q47132', 1832, 1910),
        ('Knut Hamsun', 'Q36694', 1859, 1952),
        ('Alexander Kielland', 'Q319627', 1849, 1906),
        ('Jonas Lie', 'Q473307', 1833, 1908),
        ('Gunnar Heiberg', 'Q708359', 1857, 1929),
        ('Nordahl Grieg', 'Q365133', 1902, 1943),
        ('Tarjei Vesaas', 'Q272107', 1897, 1970),
        ('Torborg Nedreaas', 'Q3066930', 1906, 1987),
        ('Oskar Braaten', 'Q319624', 1881, 1939),
        ('Hans E. Kinck', 'Q634050', 1865, 1926),
        ('Johan Borgen', 'Q726990', 1902, 1979),
    ]

    print("Adding known playwrights...")
    for name, wikidata_id, birth_year, death_year in known_playwrights:
        # Check if already exists
        cursor.execute("SELECT id FROM persons WHERE name = ?", (name,))
        existing = cursor.fetchone()

        wikipedia_url = f"https://no.wikipedia.org/wiki/{name.replace(' ', '_')}"

        if existing:
            cursor.execute("""
                UPDATE persons SET
                    birth_year = COALESCE(birth_year, ?),
                    death_year = COALESCE(death_year, ?),
                    wikidata_id = COALESCE(wikidata_id, ?),
                    wikipedia_url = COALESCE(wikipedia_url, ?)
                WHERE id = ?
            """, (birth_year, death_year, wikidata_id, wikipedia_url, existing['id']))
            print(f"  Updated: {name}")
        else:
            cursor.execute("""
                INSERT INTO persons (name, normalized_name, birth_year, death_year, wikidata_id, wikipedia_url)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, name.lower(), birth_year, death_year, wikidata_id, wikipedia_url))
            print(f"  Added: {name}")

    conn.commit()

    # Now link plays to playwrights based on common patterns
    play_mappings = {
        # title patterns -> playwright name
        'Erasmus Montanus': 'Ludvig Holberg',
        'Jeppe': 'Ludvig Holberg',
        'Den Stundesløse': 'Ludvig Holberg',
        'Barselstuen': 'Ludvig Holberg',
        'Den politiske Kandestøber': 'Ludvig Holberg',
        'Jean de France': 'Ludvig Holberg',
        'Den Vægelsindede': 'Ludvig Holberg',
        'Henrik og Pernille': 'Ludvig Holberg',
        'Et dukkehjem': 'Henrik Ibsen',
        'Vildanden': 'Henrik Ibsen',
        'Peer Gynt': 'Henrik Ibsen',
        'Hedda Gabler': 'Henrik Ibsen',
        'Gengangere': 'Henrik Ibsen',
        'Rosmersholm': 'Henrik Ibsen',
        'Fruen fra havet': 'Henrik Ibsen',
        'Lille Eyolf': 'Henrik Ibsen',
        'Når vi døde vågner': 'Henrik Ibsen',
        'Brand': 'Henrik Ibsen',
        'John Gabriel Borkman': 'Henrik Ibsen',
        'Byggmester Solness': 'Henrik Ibsen',
        'Catilina': 'Henrik Ibsen',
        'De unges forbund': 'Henrik Ibsen',
        'En folkefiende': 'Henrik Ibsen',
        'Fru Inger til Østeraad': 'Henrik Ibsen',
        'Gildet paa Solhoug': 'Henrik Ibsen',
        'Hærmændene paa Helgeland': 'Henrik Ibsen',
        'Kejser og Galilæer': 'Henrik Ibsen',
        'Kjærlighedens Komedie': 'Henrik Ibsen',
        'Kongsemnerne': 'Henrik Ibsen',
        'Samfundets støtter': 'Henrik Ibsen',
        'Over ævne': 'Bjørnstjerne Bjørnson',
        'En hanske': 'Bjørnstjerne Bjørnson',
        'De nygifte': 'Bjørnstjerne Bjørnson',
        'En fallit': 'Bjørnstjerne Bjørnson',
        'Redaktøren': 'Bjørnstjerne Bjørnson',
        'Kongen': 'Bjørnstjerne Bjørnson',
        'Maria Stuart': 'Bjørnstjerne Bjørnson',
        'Sigurd Jorsalfar': 'Bjørnstjerne Bjørnson',
        'Sigurd Slembe': 'Bjørnstjerne Bjørnson',
        'Fröken Julie': 'August Strindberg',
        'Fadren': 'August Strindberg',
        'Dødsdansen': 'August Strindberg',
        'Drømmespillet': 'August Strindberg',
        'Antigone': 'Sofokles',
        'Elektra': 'Sofokles',
        'Kong Ødipus': 'Sofokles',
        'Medea': 'Euripides',
        'Hamlet': 'William Shakespeare',
        'Othello': 'William Shakespeare',
        'Macbeth': 'William Shakespeare',
        'Romeo og Julie': 'William Shakespeare',
        'Kong Lear': 'William Shakespeare',
        'Onkel Vanja': 'Anton Tsjekhov',
        'Kirsebærhagen': 'Anton Tsjekhov',
        'Tre søstre': 'Anton Tsjekhov',
        'Måken': 'Anton Tsjekhov',
        'Tartuffe': 'Molière',
        'Den innbilte syke': 'Molière',
        'Misantropen': 'Molière',
        'Mens vi venter på Godot': 'Samuel Beckett',
        'Sluttspill': 'Samuel Beckett',
    }

    print("\nLinking plays to playwrights...")

    for title_pattern, playwright_name in play_mappings.items():
        # Get playwright ID
        cursor.execute("SELECT id FROM persons WHERE name = ?", (playwright_name,))
        playwright = cursor.fetchone()
        if not playwright:
            print(f"  Warning: Playwright not found: {playwright_name}")
            continue

        # Find matching plays
        cursor.execute("""
            SELECT id, title FROM plays
            WHERE title LIKE ? AND playwright_id IS NULL
        """, (f'%{title_pattern}%',))
        plays = cursor.fetchall()

        for play in plays:
            cursor.execute("UPDATE plays SET playwright_id = ? WHERE id = ?",
                          (playwright['id'], play['id']))
            print(f"  {play['title']} -> {playwright_name}")

    conn.commit()

    # Add year_written for some well-known plays
    year_mappings = {
        'Erasmus Montanus': 1723,
        'Jeppe på Bjerget': 1722,
        'Den Stundesløse': 1723,
        'Den politiske Kandestøber': 1722,
        'Et dukkehjem': 1879,
        'Vildanden': 1884,
        'Peer Gynt': 1867,
        'Hedda Gabler': 1890,
        'Gengangere': 1881,
        'Rosmersholm': 1886,
        'Fruen fra havet': 1888,
        'Brand': 1866,
        'Antigone': -441,
        'Medea': -431,
        'Hamlet': 1600,
        'Fröken Julie': 1888,
        'Kirsebærhagen': 1904,
        'Tre søstre': 1901,
    }

    print("\nAdding year_written...")
    for title_pattern, year in year_mappings.items():
        cursor.execute("""
            UPDATE plays SET year_written = ?
            WHERE title LIKE ? AND year_written IS NULL
        """, (year, f'%{title_pattern}%'))
        if cursor.rowcount > 0:
            print(f"  {title_pattern}: {year}")

    conn.commit()

    # Summary
    cursor.execute("SELECT COUNT(*) FROM plays WHERE playwright_id IS NOT NULL")
    with_playwright = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM plays WHERE year_written IS NOT NULL")
    with_year = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM plays")
    total = cursor.fetchone()[0]

    print(f"\n=== Summary ===")
    print(f"Plays with playwright: {with_playwright}/{total}")
    print(f"Plays with year written: {with_year}/{total}")

    # Show some linked plays
    cursor.execute("""
        SELECT p.title, p.year_written, per.name, per.birth_year, per.death_year
        FROM plays p
        JOIN persons per ON p.playwright_id = per.id
        LIMIT 20
    """)
    print("\nSample linked plays:")
    for row in cursor.fetchall():
        years = f"({row[3]}-{row[4]})" if row[3] else ""
        written = f"({row[1]})" if row[1] else ""
        print(f"  {row[0]} {written} - {row[2]} {years}")

    conn.close()

if __name__ == '__main__':
    main()
