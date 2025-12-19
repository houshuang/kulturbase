#!/usr/bin/env python3
"""
Fetch play synopses from Norwegian Wikipedia.
"""

import sqlite3
import requests
import time
import re

DB_PATH = 'static/kulturperler.db'

# Manual synopses for well-known plays
KNOWN_SYNOPSES = {
    'Peer Gynt': 'Et dramatisk dikt om den eventyrlystne Peer Gynt som flykter fra virkeligheten inn i fantasien. Han forlater sin mor Åse og kjæresten Solveig for å søke lykken, men må til slutt vende tilbake og innse at hans sanne jeg var hjemme hos Solveig hele tiden.',
    'Et dukkehjem': 'Nora Helmer lever tilsynelatende et lykkelig liv med sin mann Torvald. Men et hemmeligholdtlån hun tok opp for å redde mannens liv, truer med å ødelegge alt. Stykket ender med at Nora forlater mann og barn for å finne seg selv.',
    'Hedda Gabler': 'Hedda Gabler har nettopp giftet seg med den kjedelige akademikeren Jørgen Tesman. Utilfreds med livet manipulerer hun menneskene rundt seg, med tragiske konsekvenser.',
    'Vildanden': 'Familien Ekdal lever i en illusjon som holder dem sammen. Når den idealistiske Gregers Werle avslører sannheten, får det fatale følger.',
    'Gengangere': 'Fru Alving vil åpne et barnehjem til minne om sin avdøde mann. Men fortiden innhenter henne når sønnen Osvald kommer hjem, syk og uvitende om farens virkelige karakter.',
    'Rosmersholm': 'Den tidligere presten Johannes Rosmer og Rebekka West prøver å frigjøre seg fra fortiden på godset Rosmersholm, men skyld og hemmeligheter driver dem mot undergangen.',
    'Fruen fra havet': 'Ellida Wangel er gift med en lege i en liten kystby, men føler seg dratt mot havet og en mystisk fremmed fra fortiden. Hun må velge mellom trygghet og frihet.',
    'Byggmester Solness': 'Den aldrende arkitekten Halvard Solness frykter å bli forbigått av yngre krefter. Når den unge Hilde Wangel dukker opp, inspirerer hun ham til å klatre opp i et tårn han selv har bygget.',
    'John Gabriel Borkman': 'Den tidligere bankdirektøren John Gabriel Borkman har sittet fengslet for underslag. Nå går han hvileløst i sitt værelse og venter på at verden skal kalle ham tilbake til makten.',
    'Lille Eyolf': 'Ekteparet Alfred og Rita Allmers får livet snudd på hodet når deres funksjonshemmede sønn Eyolf drukner. De må konfrontere sin egen skyld og sine uoppfylte drømmer.',
    'Brand': 'Presten Brand krever alt eller intet av seg selv og andre. Hans kompromissløse idealisme fører til tragedier for alle rundt ham.',
    'En folkefiende': 'Dr. Stockmann oppdager at byens badeanstalt er forurenset, men når han vil avsløre sannheten, blir han erklært en folkefiende av de som har økonomiske interesser i å holde det skjult.',
    'Erasmus Montanus': 'Studenten Rasmus Berg vender hjem til landsbyen og vil imponere med sin lærdom. Men hans påstand om at jorden er rund, skaper problemer med de lokale myndighetene.',
    'Jeppe på Bjerget': 'Den fattige bonden Jeppe drikker seg full og våkner i baronens seng. Han tror han er blitt baron, men er egentlig offer for en grusom spøk.',
    'Den Stundesløse': 'Vielgeschrey er alltid travel og aldri til stede. Hans kaotiske liv skaper forviklinger for alle rundt ham.',
    'Barselstuen': 'Corfitz har et problem - han mistror sin unge hustru. Fruen ligger på barselstuen og mottar gjester, og Corfitz prøver å overvåke alt som skjer.',
    'Antigone': 'Antigone trosser kong Kreons forbud og begraver sin bror Polyneikes. Hun velger å følge gudenes lover framfor menneskenes, selv om det koster henne livet.',
    'Medea': 'Medea er forlatt av sin mann Jason til fordel for en prinsesse. Hennes hevn blir grusom - hun dreper sine egne barn for å straffe ham.',
    'Tre søstre': 'De tre søstrene Olga, Masja og Irina drømmer om å reise til Moskva og et bedre liv, men blir fanget i provinsens monotoni.',
    'Kirsebærhagen': 'Godseier Ranevskaja må selge familiens kirsebærhage for å betale gjeld. Hagen kjøpes av den tidligere livegne Lopakhin, som vil hugge ned trærne.',
    'Onkel Vanja': 'Vanja har ofret livet sitt for å drive godset til sin svoger, den pensjonerte professoren Serebryakov. Når professoren vil selge godset, bryter Vanjas bitterhet ut.',
}

def get_wikipedia_extract(title):
    """Fetch extract from Norwegian Wikipedia."""
    params = {
        'action': 'query',
        'titles': title,
        'prop': 'extracts',
        'exintro': True,
        'explaintext': True,
        'exsentences': 4,
        'format': 'json',
        'redirects': 1
    }

    headers = {'User-Agent': 'Kulturperler/1.0 (educational project)'}

    try:
        response = requests.get(
            'https://no.wikipedia.org/w/api.php',
            params=params,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        pages = data.get('query', {}).get('pages', {})
        for page_id, page in pages.items():
            if page_id == '-1':
                return None
            if 'extract' in page:
                extract = page['extract']
                # Clean up
                extract = re.sub(r'\s+', ' ', extract).strip()
                return extract

    except Exception as e:
        print(f"  Error fetching {title}: {e}")

    return None

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # First, add manual synopses for well-known plays
    print("Adding known synopses...")
    for title_pattern, synopsis in KNOWN_SYNOPSES.items():
        cursor.execute("""
            UPDATE plays SET synopsis = ?
            WHERE title LIKE ? AND synopsis IS NULL
        """, (synopsis, f'%{title_pattern}%'))
        if cursor.rowcount > 0:
            print(f"  {title_pattern}: Added synopsis")
    conn.commit()

    # Get plays without synopsis that have playwright (more likely to be findable)
    cursor.execute("""
        SELECT p.id, p.title, per.name as playwright_name
        FROM plays p
        LEFT JOIN persons per ON p.playwright_id = per.id
        WHERE p.synopsis IS NULL
        AND p.playwright_id IS NOT NULL
        ORDER BY p.id
        LIMIT 50
    """)
    plays = cursor.fetchall()

    print(f"\nSearching Wikipedia for {len(plays)} plays...")

    for play in plays:
        title = play['title']
        playwright = play['playwright_name']

        # Try different search patterns
        search_terms = [
            f"{title} ({playwright})",
            f"{title} (skuespill)",
            title
        ]

        for search_term in search_terms:
            print(f"  Trying: {search_term}")
            extract = get_wikipedia_extract(search_term)

            if extract and len(extract) > 50:
                # Check if it's about a play (not a person, place, etc.)
                if any(word in extract.lower() for word in ['drama', 'skuespill', 'stykke', 'komedie', 'tragedie', 'teater', 'handling', 'premiere']):
                    cursor.execute("UPDATE plays SET synopsis = ? WHERE id = ?", (extract, play['id']))
                    conn.commit()
                    print(f"    Found: {extract[:60]}...")
                    break

            time.sleep(0.3)

    # Summary
    cursor.execute("SELECT COUNT(*) FROM plays WHERE synopsis IS NOT NULL")
    with_synopsis = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM plays")
    total = cursor.fetchone()[0]

    print(f"\n=== Summary ===")
    print(f"Plays with synopsis: {with_synopsis}/{total}")

    conn.close()

if __name__ == '__main__':
    main()
