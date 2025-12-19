#!/usr/bin/env python3
"""
Fetch play synopses from Norwegian and English Wikipedia.
Prioritizes well-known plays by famous playwrights.
"""

import sqlite3
import subprocess
import json
import time
import re
import urllib.parse
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "static" / "kulturperler.db"

# Manual synopses for well-known plays (Norwegian)
KNOWN_SYNOPSES = {
    "Peer Gynt": "Peer Gynt er et dramatisk dikt av Henrik Ibsen fra 1867. Det handler om den norske bondesønnen Peer Gynt og hans eventyrlige liv, fra ungdomsårene i Gudbrandsdalen, gjennom reiser verden rundt, til han vender tilbake som gammel mann. Stykket utforsker temaer som identitet, selvbedrag og kjærlighet.",
    "Hedda Gabler": "Hedda Gabler er et skuespill av Henrik Ibsen fra 1890. Det handler om den frustrerte og ambisiøse Hedda som er fanget i et kjedelig ekteskap med akademikeren Jørgen Tesman. Hennes manipulerende forsøk på å kontrollere menneskene rundt seg fører til tragedie.",
    "Et dukkehjem": "Et dukkehjem er et skuespill av Henrik Ibsen fra 1879. Det følger Nora Helmer som oppdager at hennes tilsynelatende lykkelige ekteskap er bygget på løgner og at hun har levd som en dukke i sitt eget hjem. Stykket var banebrytende for sin tids diskusjon om kvinners rettigheter.",
    "Vildanden": "Vildanden er et skuespill av Henrik Ibsen fra 1884. Det handler om familien Ekdal og konsekvensene når sannheten om fortiden avsløres. Vildanden på loftet blir et symbol på familiens illusjoner og selvbedrag.",
    "Gengangere": "Gengangere er et skuespill av Henrik Ibsen fra 1881. Det handler om fru Alving som forsøker å minnes sin avdøde mann ved å opprette et barnehjem, men fortiden innhenter henne når sannheten om mannens liv avsløres.",
    "Brand": "Brand er et dramatisk dikt av Henrik Ibsen fra 1866. Det handler om den kompromissløse presten Brand som krever alt eller intet av seg selv og sine nærmeste. Hans fanatiske idealisme fører til tragedie.",
    "En folkefiende": "En folkefiende er et skuespill av Henrik Ibsen fra 1882. Det handler om doktor Stockmann som oppdager at byens kurbad er forurenset, men møter motstand fra myndighetene og befolkningen når han forsøker å avsløre sannheten.",
    "Rosmersholm": "Rosmersholm er et skuespill av Henrik Ibsen fra 1886. Det utspiller seg på den gamle slektsgården Rosmersholm hvor Johannes Rosmer og Rebekka West kjemper med skyld, idealer og kjærlighet i skyggen av den avdøde fru Rosmer.",
    "Fruen fra havet": "Fruen fra havet er et skuespill av Henrik Ibsen fra 1888. Det handler om Ellida Wangel som føler seg dratt mot havet og en mystisk fremmed fra fortiden, mens hun er gift med en eldre lege.",
    "Lille Eyolf": "Lille Eyolf er et skuespill av Henrik Ibsen fra 1894. Det handler om ekteparet Allmers og deres funksjonshemmede sønn Eyolf. Etter en tragedie tvinges foreldrene til å konfrontere sitt ekteskap og sine livsprioriteter.",
    "Byggmester Solness": "Byggmester Solness er et skuespill av Henrik Ibsen fra 1892. Det handler om den aldrende arkitekten Halvard Solness som frykter den yngre generasjonen, og hans møte med den unge Hilde Wangel som utfordrer ham til å nå nye høyder.",
    "John Gabriel Borkman": "John Gabriel Borkman er et skuespill av Henrik Ibsen fra 1896. Det handler om den tidligere bankdirektøren Borkman som har sonet en fengselsstraff for underslag og nå lever isolert i sitt eget hjem, drømmende om gjenreisning.",
    "Når vi døde vågner": "Når vi døde vågner er et skuespill av Henrik Ibsen fra 1899. Det handler om billedhuggeren Rubek som møter sin tidligere modell Irene igjen etter mange år, og sammen konfronterer de sine valg og tapte muligheter.",
    "Samfundets støtter": "Samfundets støtter er et skuespill av Henrik Ibsen fra 1877. Det handler om skipsrederen Karsten Bernick som lever et dobbeltliv med mørke hemmeligheter bak fasaden som byens respekterte borger.",
    "Frøken Julie": "Frøken Julie er et naturalistisk skuespill av August Strindberg fra 1888. Det utspiller seg på midtsommernatten når grevedatteren Julie innleder et forhold til tjeneren Jean, med fatale konsekvenser.",
    "Spøkelsesonaten": "Spøkelsesonaten er et kammerspill av August Strindberg fra 1907. Det handler om studenten Arkenholz som blir trukket inn i en mystisk familie med mørke hemmeligheter og overnaturlige elementer.",
    "Dødsdansen": "Dødsdansen er et skuespill av August Strindberg fra 1900. Det handler om det bitre ekteskapet mellom kaptein Edgar og hans kone Alice, fanget på en isolert festningsøy.",
    "Tre søstre": "Tre søstre er et skuespill av Anton Tsjekhov fra 1901. Det handler om søstrene Olga, Masja og Irina som drømmer om å vende tilbake til Moskva mens de lever et stillestående liv i provinsen.",
    "Kirsebærhaven": "Kirsebærhaven er et skuespill av Anton Tsjekhov fra 1904. Det handler om en adelig familie som tvinges til å selge sitt kjære gods med den berømte kirsebærhaven på grunn av økonomiske problemer.",
    "Måken": "Måken er et skuespill av Anton Tsjekhov fra 1896. Det handler om unge kunstnere og deres kjærlighetsforhold, med en skutt måke som sentralt symbol. Stykket utforsker temaer som kunst, kjærlighet og livets skuffelser.",
    "Onkel Vanja": "Onkel Vanja er et skuespill av Anton Tsjekhov fra 1897. Det handler om Vanja og hans niese Sonja som har ofret sine liv for å drive et gods for den selvopptatte professor Serebriakov.",
    "Erasmus Montanus": "Erasmus Montanus er en komedie av Ludvig Holberg fra 1731. Det handler om bondestudenten Rasmus Berg som vender hjem fra København med latinnavnet Erasmus Montanus og akademisk arroganse som skaper konflikt i landsbyen.",
    "Jeppe på bjerget": "Jeppe på bjerget er en komedie av Ludvig Holberg fra 1722. Det handler om bonden Jeppe som våkner opp i baronens seng etter en fyllekule og tror han har blitt baron, med komiske forviklinger som følge.",
    "Den stundesløse": "Den stundesløse er en komedie av Ludvig Holberg fra 1723. Det handler om den rastløse Vielgeschrey som alltid har det travelt uten egentlig å utrette noe, en satire over viktigpetere.",
    "Den politiske kannestøper": "Den politiske kannestøper er en komedie av Ludvig Holberg fra 1722. Det handler om kannestøperen Herman von Bremen som er mer opptatt av politikk enn sitt eget håndverk.",
    "Romeo og Julie": "Romeo og Julie er en tragedie av William Shakespeare fra ca. 1595. Det handler om de to unge elskende fra de rivaliserende familiene Montague og Capulet i Verona, hvis kjærlighet ender i tragedie.",
    "Hamlet": "Hamlet er en tragedie av William Shakespeare fra ca. 1600. Det handler om prins Hamlet av Danmark som søker hevn over sin onkel Claudius som har drept hans far og giftet seg med hans mor.",
    "Macbeth": "Macbeth er en tragedie av William Shakespeare fra ca. 1606. Det handler om den skotske generalen Macbeth som drives av ambisjon og profetier til å myrde kongen og ta tronen, med katastrofale følger.",
    "En midtsommernattsdrøm": "En midtsommernattsdrøm er en komedie av William Shakespeare fra ca. 1595. Det handler om forviklinger mellom elskende par i en magisk skog utenfor Athen, hvor alver blander seg inn i menneskers anliggender.",
    "Othello": "Othello er en tragedie av William Shakespeare fra ca. 1603. Det handler om den mauriske generalen Othello som blir manipulert av den misunnelige Iago til å tro at hans kone Desdemona er utro.",
    "Kong Lear": "Kong Lear er en tragedie av William Shakespeare fra ca. 1605. Det handler om den aldrende kongen Lear som deler sitt rike mellom døtrene basert på deres smiger, med tragiske konsekvenser.",
    "Stormen": "Stormen er et skuespill av William Shakespeare fra ca. 1611. Det handler om trollmannen Prospero som bruker magi for å hevne seg på sine fiender etter å ha blitt strandet på en øy.",
    "Tartuffe": "Tartuffe er en komedie av Molière fra 1664. Det handler om hykleren Tartuffe som lurer seg inn i en borgerlig familie ved å spille from og from, og nesten ødelegger familien.",
    "Den innbilte syke": "Den innbilte syke er en komedie av Molière fra 1673. Det handler om hypokonderende Argan som er besatt av sin egen helse og manipuleres av leger og sin andre kone.",
    "Ventetid på Godot": "Ventetid på Godot er et absurdistisk skuespill av Samuel Beckett fra 1953. Det handler om Vladimir og Estragon som venter på den mystiske Godot som aldri kommer, en meditasjon over livets meningsløshet.",
    "Mor Courage og hennes barn": "Mor Courage og hennes barn er et antikrigs-skuespill av Bertolt Brecht fra 1939. Det handler om marketentersken Anna Fierling som forsøker å tjene penger på trettiårskrigen mens hun mister alle sine barn.",
    "Tolvskillingsoperaen": "Tolvskillingsoperaen er et musikkteater av Bertolt Brecht med musikk av Kurt Weill fra 1928. Det handler om forbryteren Macheath i et korrupt London, en modernisering av John Gays The Beggar's Opera.",
    "Kaukasiske Krittringen": "Den kaukasiske krittringen er et skuespill av Bertolt Brecht fra 1944. Det handler om tjenestepiken Grusche som redder et barn under en borgerkrig, og den påfølgende rettssaken om hvem som er barnets rette mor.",
    "Glasmenasjeriet": "Glasmenasjeriet er et minnespill av Tennessee Williams fra 1944. Det handler om familien Wingfield i St. Louis: den drømmende moren Amanda, den funksjonshemmede datteren Laura og sønnen Tom som lengter etter å rømme.",
    "En sporvogn til begjær": "En sporvogn til begjær er et skuespill av Tennessee Williams fra 1947. Det handler om Blanche DuBois som søker tilflukt hos søsteren Stella i New Orleans, men konfronteres med den brutale Stanley Kowalski.",
    "Katten på et varmt blikktak": "Katten på et varmt blikktak er et skuespill av Tennessee Williams fra 1955. Det handler om spenningene i en sørstats-familie når patriarken Big Daddy er døende og arvespørsmål kommer på bordet.",
    "En handelsreisendes død": "En handelsreisendes død er et skuespill av Arthur Miller fra 1949. Det handler om den aldrende selgeren Willy Loman som konfronterer sin egen fiasko og sviket mot den amerikanske drømmen.",
    "Heksejakt": "Heksejakt er et skuespill av Arthur Miller fra 1953. Det handler om hekseprosessene i Salem i 1692, men er også en allegori over McCarthyismen og politisk forfølgelse i 1950-tallets USA.",
    "Utsikt fra broen": "Utsikt fra broen er et skuespill av Arthur Miller fra 1955. Det handler om havnearbeideren Eddie Carbone i Brooklyn som utvikler et destruktivt forhold til sin niese Catherine.",
    "Nora": "Nora er et annet navn for Et dukkehjem, et skuespill av Henrik Ibsen fra 1879. Det følger Nora Helmer som oppdager at hennes tilsynelatende lykkelige ekteskap er bygget på løgner.",
    "Gjengangere": "Gjengangere er et skuespill av Henrik Ibsen fra 1881. Det handler om fru Alving som forsøker å minnes sin avdøde mann ved å opprette et barnehjem, men fortiden innhenter henne.",
    "Catilina": "Catilina er Henrik Ibsens første drama fra 1850. Det handler om den romerske politikeren Catilina og hans sammensvergelse mot republikken.",
    "Terje Vigen": "Terje Vigen er et episk dikt av Henrik Ibsen fra 1862. Det handler om sjømannen Terje Vigen under blokaden av Norge 1807-1814, hans fangenskap og endelige forsoning.",
    "Kongsemnerne": "Kongsemnerne er et historisk drama av Henrik Ibsen fra 1863. Det handler om maktkampen mellom kong Håkon og jarl Skule i Norge på 1200-tallet.",
    "Hærmændene på Helgeland": "Hærmændene på Helgeland er et drama av Henrik Ibsen fra 1858. Det er basert på norrøne sagaer og handler om ære, kjærlighet og hevn i vikingtiden.",
    "De unges forbund": "De unges forbund er en satirisk komedie av Henrik Ibsen fra 1869. Det handler om den ambisiøse advokaten Stensgaard og hans politiske spill i en liten norsk by.",
    "Kejser og Galilæer": "Kejser og Galilæer er et historisk drama av Henrik Ibsen fra 1873. Det handler om den romerske keiseren Julian og hans forsøk på å gjeninnføre hedendommen.",
    "Kongs-Emnerne": "Kongs-Emnerne er et historisk drama av Henrik Ibsen fra 1863. Det handler om maktkampen mellom kong Håkon og jarl Skule i Norge på 1200-tallet.",
}

# Wikipedia title mappings for plays that need different lookup names
WIKIPEDIA_TITLES = {
    "Peer Gynt": "Peer Gynt",
    "Hedda Gabler": "Hedda Gabler",
    "Et dukkehjem": "Et dukkehjem",
    "Vildanden": "Vildanden",
    "Gengangere": "Gengangere (skuespill)",
    "Brand": "Brand (Ibsen)",
    "En folkefiende": "En folkefiende",
    "Rosmersholm": "Rosmersholm",
    "Fruen fra havet": "Fruen fra havet",
    "Lille Eyolf": "Lille Eyolf",
    "Byggmester Solness": "Byggmester Solness",
    "John Gabriel Borkman": "John Gabriel Borkman",
    "Når vi døde vågner": "Når vi døde vågner",
    "Frøken Julie": "Frøken Julie",
    "Tre søstre": "Tre søstre",
    "Kirsebærhaven": "Kirsebærhaven",
    "Måken": "Måken (skuespill)",
    "Erasmus Montanus": "Erasmus Montanus",
    "Jeppe på bjerget": "Jeppe på Bjerget",
    "Den stundesløse": "Den Stundesløse",
}


def fetch_norwegian_wikipedia(title: str) -> str | None:
    """Fetch synopsis from Norwegian Wikipedia."""
    lookup_title = WIKIPEDIA_TITLES.get(title, title)
    encoded_title = urllib.parse.quote(lookup_title.replace(" ", "_"))
    api_url = f"https://no.wikipedia.org/api/rest_v1/page/summary/{encoded_title}"

    try:
        result = subprocess.run(
            ['curl', '-s', '-L', '-H', 'User-Agent: Kulturperler/1.0', api_url],
            capture_output=True,
            text=True,
            timeout=15
        )

        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)

        if data.get('type') == 'https://mediawiki.org/wiki/HyperSwitch/errors/not_found':
            return None

        extract = data.get('extract', '')

        # Skip disambiguation pages
        if 'flere betydninger' in extract.lower() or 'kan vise til' in extract.lower():
            return None

        # Limit length
        if extract and len(extract) > 500:
            sentences = extract.split('. ')
            short_extract = ''
            for sentence in sentences:
                if len(short_extract) + len(sentence) < 500:
                    short_extract += sentence + '. '
                else:
                    break
            extract = short_extract.strip()

        return extract if extract else None

    except Exception as e:
        print(f"  Error: {e}")
        return None


def fetch_english_wikipedia(title: str, playwright: str = None) -> str | None:
    """Fetch synopsis from English Wikipedia."""
    # Try with playwright name for disambiguation
    search_title = title
    if playwright:
        search_title = f"{title} ({playwright})"

    encoded_title = urllib.parse.quote(search_title.replace(" ", "_"))
    api_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_title}"

    try:
        result = subprocess.run(
            ['curl', '-s', '-L', '-H', 'User-Agent: Kulturperler/1.0', api_url],
            capture_output=True,
            text=True,
            timeout=15
        )

        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)

        if data.get('type') == 'https://mediawiki.org/wiki/HyperSwitch/errors/not_found':
            # Try without playwright
            if playwright:
                return fetch_english_wikipedia(title, None)
            return None

        extract = data.get('extract', '')

        # Skip disambiguation pages
        if 'may refer to' in extract.lower() or 'commonly refers to' in extract.lower():
            return None

        return extract if extract else None

    except Exception as e:
        print(f"  Error: {e}")
        return None


def translate_synopsis(text: str, title: str, playwright: str = None) -> str:
    """Create Norwegian synopsis from English text."""
    if not text:
        return ""

    # Simple translation of key phrases
    result = text

    # Determine article type
    is_play = any(word in text.lower() for word in ['play', 'drama', 'tragedy', 'comedy'])

    # Extract year if present
    year_match = re.search(r'(\d{4})', text)
    year = year_match.group(1) if year_match else None

    # Build Norwegian synopsis
    if is_play and playwright and year:
        # Start with standard Norwegian format
        genre = "skuespill"
        if "tragedy" in text.lower():
            genre = "tragedie"
        elif "comedy" in text.lower():
            genre = "komedie"
        elif "drama" in text.lower():
            genre = "drama"

        synopsis = f"{title} er et {genre} av {playwright}"
        if year:
            synopsis += f" fra {year}"
        synopsis += "."

        # Try to extract plot summary
        plot_indicators = ['tells the story', 'is about', 'follows', 'centers on', 'depicts', 'concerns']
        for indicator in plot_indicators:
            if indicator in text.lower():
                idx = text.lower().find(indicator)
                plot_part = text[idx:].split('.')[0]
                # Translate common phrases
                plot_part = plot_part.replace('tells the story of', 'handler om')
                plot_part = plot_part.replace('is about', 'handler om')
                plot_part = plot_part.replace('follows', 'følger')
                plot_part = plot_part.replace('centers on', 'handler om')
                plot_part = plot_part.replace('depicts', 'skildrer')
                plot_part = plot_part.replace('concerns', 'handler om')
                synopsis += " Det " + plot_part + "."
                break

        return synopsis

    return ""


def fetch_synopses(conn: sqlite3.Connection):
    """Fetch synopses for plays."""
    cursor = conn.cursor()

    # Get plays without synopses, prioritized by performance count
    cursor.execute("""
        SELECT p.id, p.title, pw.name as playwright,
          (SELECT COUNT(*) FROM performances pf WHERE pf.work_id = p.id) as perf_count
        FROM plays p
        LEFT JOIN persons pw ON p.playwright_id = pw.id
        WHERE p.synopsis IS NULL OR p.synopsis = ''
        ORDER BY perf_count DESC, p.title
    """)

    plays = cursor.fetchall()
    print(f"Found {len(plays)} plays without synopses")

    updated = 0
    for play_id, title, playwright, perf_count in plays:
        # First check manual synopses
        if title in KNOWN_SYNOPSES:
            synopsis = KNOWN_SYNOPSES[title]
            cursor.execute("UPDATE plays SET synopsis = ? WHERE id = ?", (synopsis, play_id))
            updated += 1
            print(f"Manual: {title} ({len(synopsis)} chars)")
            continue

        # Try Norwegian Wikipedia
        print(f"Fetching: {title}...", end=" ", flush=True)
        synopsis = fetch_norwegian_wikipedia(title)

        if synopsis:
            cursor.execute("UPDATE plays SET synopsis = ? WHERE id = ?", (synopsis, play_id))
            updated += 1
            print(f"NO Wiki ({len(synopsis)} chars)")
        else:
            # Try English Wikipedia
            en_text = fetch_english_wikipedia(title, playwright)
            if en_text:
                synopsis = translate_synopsis(en_text, title, playwright)
                if synopsis and len(synopsis) > 30:
                    cursor.execute("UPDATE plays SET synopsis = ? WHERE id = ?", (synopsis, play_id))
                    updated += 1
                    print(f"EN Wiki translated ({len(synopsis)} chars)")
                else:
                    print("Translation too short")
            else:
                print("Not found")

        time.sleep(0.2)

        # Commit periodically
        if updated % 20 == 0:
            conn.commit()

    conn.commit()
    print(f"\nUpdated {updated} plays with synopses")


def main():
    print("=" * 60)
    print("Fetching play synopses from Wikipedia")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    try:
        fetch_synopses(conn)
    finally:
        conn.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
