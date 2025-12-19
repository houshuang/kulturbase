#!/usr/bin/env python3
"""
Comprehensive enrichment script for fetching Norwegian summaries for authors and plays.
- Fetches author bios from Norwegian Wikipedia
- Fetches play synopses from Norwegian Wikipedia
- Includes manual synopses for famous works
"""

import sqlite3
import requests
import time
import re

DB_PATH = 'static/kulturperler.db'

# Extended manual synopses for well-known plays
KNOWN_SYNOPSES = {
    # Ibsen
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
    'Når vi døde våkner': 'Billedhuggeren Rubek møter igjen sin tidligere modell Irene. Sammen konfronterer de det livet de ofret for kunsten.',
    'Samfunnets støtter': 'Skipsrederen Karsten Bernick har bygget sin makt på løgner og bedrag. Når fortiden innhenter ham, må han velge mellom ærlighet og alt han har oppnådd.',
    'Fru Inger til Østråt': 'Fru Inger er fanget mellom lojalitet til Norge og beskyttelse av sine barn. En dramatisk natt på Østråt avslører hemmeligheter som får fatale følger.',

    # Holberg
    'Erasmus Montanus': 'Studenten Rasmus Berg vender hjem til landsbyen og vil imponere med sin lærdom. Men hans påstand om at jorden er rund, skaper problemer med de lokale myndighetene.',
    'Jeppe på Bjerget': 'Den fattige bonden Jeppe drikker seg full og våkner i baronens seng. Han tror han er blitt baron, men er egentlig offer for en grusom spøk.',
    'Den Stundesløse': 'Vielgeschrey er alltid travel og aldri til stede. Hans kaotiske liv skaper forviklinger for alle rundt ham.',
    'Barselstuen': 'Corfitz har et problem - han mistror sin unge hustru. Fruen ligger på barselstuen og mottar gjester, og Corfitz prøver å overvåke alt som skjer.',
    'Den vægelsindede': 'Lucretia skifter mening hvert øyeblikk. Hennes vægelsindethet skaper kaos for alle som prøver å forstå henne.',
    'Den Forvandlede Brudgom': 'En forvekslingskomedie der en mann må utgi seg for å være en annen for å vinne sin elskede.',

    # Strindberg
    'Frøken Julie': 'Midsommernatt på et svensk gods. Grevinne Julies dans med tjeneren Jean utløser en maktkamp mellom klassene og kjønnene som ender i tragedie.',
    'Dødsdansen': 'Det bitre ekteskapet mellom kapteinen Edgar og hans kone Alice på en isolert festning er en hensynsløs kamp der begge prøver å tilintetgjøre den andre.',
    'Kreditorer': 'Gustav manipulerer sin ekskones nye ektemann Adolphe til å innse at hans kunstneriske selvtillit bygger på løgner.',
    'Mester Olof': 'Den unge reformatoren Olaus Petri kjemper for den lutherske tro i Sverige på 1500-tallet, fanget mellom idealisme og politisk makt.',
    'Pelikanen': 'En mor som har utsultet sine barn hele livet blir konfrontert med sannheten. Strindbergs mørke kammerspill om familiens hemmeligheter.',
    'Kameratene': 'Bertha og Axel er likestilte kunstnere og ektefeller, men når Bertha får suksess og Axel mislykkes, settes forholdet på prøve.',
    'Leke med ilden': 'En mann inviterer sin venn hjem for å teste sin kones troskap. Leken får uventede konsekvenser.',
    'Paria': 'To menn møtes på en øde øy. Den ene er arkeolog, den andre er på flukt. En intens psykologisk duell utspiller seg.',
    'Båndet': 'Et ektepar strides om omsorgsretten til barnet. En bitter kamp der begge bruker alle midler.',
    'Etter brannen': 'Etter en brann som har ødelagt familiens hjem, avsløres hemmelighetene som har holdt familien sammen.',

    # Tsjekhov
    'Tre søstre': 'De tre søstrene Olga, Masja og Irina drømmer om å reise til Moskva og et bedre liv, men blir fanget i provinsens monotoni.',
    'Kirsebærhagen': 'Godseier Ranevskaja må selge familiens kirsebærhage for å betale gjeld. Hagen kjøpes av den tidligere livegne Lopakhin, som vil hugge ned trærne.',
    'Onkel Vanja': 'Vanja har ofret livet sitt for å drive godset til sin svoger, den pensjonerte professoren Serebryakov. Når professoren vil selge godset, bryter Vanjas bitterhet ut.',
    'Måken': 'På et gods ved en innsjø krysses skjebner: den unge forfatteren Treplev elsker skuespillerinnen Nina, som drømmer om berømmelse. En historie om kunst, kjærlighet og skuffelse.',
    'Jubileet': 'En korrupt bankdirektør feirer bankens jubileum mens kaos bryter ut rundt ham. En satirisk enakter om grådighet og hykleri.',
    'Tobakkens skadelige virkninger': 'En mann holder et foredrag om tobakkens farer, men avslører egentlig alt om sitt elendige ekteskap. En tragikomisk monolog.',
    'Svanesong': 'En gammel skuespiller blir igjen alene på scenen etter forestillingen. I samtale med suffløren reflekterer han over et liv viet teateret.',

    # Shakespeare
    'Stormen': 'Den forviste hertugen Prospero lever på en øy med sin datter Miranda. Med magi setter han i gang en storm som bringer hans fiender til øya for et endelig oppgjør.',
    'Hamlet': 'Prins Hamlet av Danmark må hevne sin fars mord, begått av hans onkel som nå har giftet seg med hans mor. En tragedie om tvil, galskap og hevn.',
    'Macbeth': 'Hekser spår at Macbeth skal bli konge. Drevet av ærgjerrighet og sin kone, myrder han kongen og tar makten, men skyldfølelsen driver ham til galskap.',
    'Kong Lear': 'Den gamle kongen Lear deler riket mellom sine tre døtre basert på deres kjærlighetserklæringer. Hans fatale feilbedømming fører til tragedie.',
    'Othello': 'Generalen Othello er lykkelig gift med Desdemona, men den ondsinnede Iago såer tvil om hennes troskap. Sjalusi fører til mord.',
    'En midtsommernattsdrøm': 'I en fortryllet skog blandes kjærlighet, magi og teater når feer, elskende og håndverkere møtes midsommernatten.',

    # Beckett
    'Mens vi venter på Godot': 'Vladimir og Estragon venter på en mann som heter Godot. Han kommer aldri. En absurd og poetisk meditasjon over menneskets eksistens.',
    'Sluttspill': 'I et postapokalyptisk rom bor den blinde Hamm og hans tjener Clov. Hammens foreldre bor i søppelbøtter. En mørk komedie om avslutninger.',
    'Krapps siste spole': 'Den gamle Krapp lytter til lydopptak han gjorde som ung. Han konfronterer minnene om en tapt kjærlighet og et forfeilet liv.',
    'Hva, Joe?': 'Joe sitter alene mens en stemme anklager ham for forbrytelser mot kvinner han har kjent. Et intenst TV-drama om skyld og ensomhet.',

    # Pinter
    'Vaktmesteren': 'To brødre lar en hjemløs mann bo i et falleferdig rom. Et makspill utfolder seg der ingenting er som det ser ut til.',
    'Kjøkkenheisen': 'To leiemordere venter i et kjellerlokale. En kjøkkenheis begynner å sende ned bestillinger. En uhyggelig komedie om lydighet og absurditet.',
    'Rommet': 'Rose bor i et rom hun aldri forlater. Besøkende truer hennes trygghet. Pinters første stykke om angst og territorium.',
    'Elskeren': 'Et ektepar lever et dobbeltliv der de later som de har elskerinner og elskere. Grensene mellom rollespill og virkelighet viskes ut.',
    'Kolleksjonen': 'To menn konfronterer hverandres koner om en påstått affære. Sannheten forblir uklar i dette spillet om sjalusi og makt.',

    # Miller
    'En handelsreisendes død': 'Willy Loman er en aldrende handelsreisende som klamrer seg til den amerikanske drømmen. Når illusjonene rakner, faller alt sammen.',
    'Alle Mine Sønner': 'Joe Keller solgte defekte flydeler under krigen. Nå må han konfrontere konsekvensene da hans overlevende sønn oppdager sannheten.',

    # Bjørnson
    'En Fallit': 'En forretningsmann står overfor konkurs og må velge mellom ære og økonomisk overlevelse.',
    'En Hanske': 'En ung kvinne nekter å gifte seg med sin forlovede fordi han har hatt et forhold før henne. Et drama om dobbeltmoral.',
    'Geografi og kjærlighet': 'Professor Tygesen er så oppslukt av sitt geografiske arbeid at han forsømmer familien. En komedie om akademisk besettelse.',

    # Greek
    'Antigone': 'Antigone trosser kong Kreons forbud og begraver sin bror Polyneikes. Hun velger å følge gudenes lover framfor menneskenes, selv om det koster henne livet.',
    'Medea': 'Medea er forlatt av sin mann Jason til fordel for en prinsesse. Hennes hevn blir grusom - hun dreper sine egne barn for å straffe ham.',
    'Kong Ødipus': 'Kong Ødipus søker å finne morderen som har brakt pest over Theben. Hans etterforskning avslører en forferdelig sannhet om hans egen fortid.',
    'Elektra': 'Elektra venter på sin bror Orestes for å hevne mordet på deres far Agamemnon, drept av deres mor Klytaimnestra.',

    # Molière
    'Tartuffe': 'Bedrageren Tartuffe har lurt seg inn i en velstående familie ved å utgi seg for å være from. Bare husets datter gjennomskuer ham.',
    'Den innbilte syke': 'Argan er overbevist om at han er dødssyk og omgir seg med leger. Hans familie prøver å redde ham fra hans innbilte sykdommer - og fra seg selv.',
    'Misantropen': 'Alceste hater menneskehetens hykleri, men er forelsket i den forfengelige Célimène. En komedie om ærlighetens grenser.',
}

def get_wikipedia_extract(title, sentences=4):
    """Fetch extract from Norwegian Wikipedia."""
    params = {
        'action': 'query',
        'titles': title,
        'prop': 'extracts',
        'exintro': True,
        'explaintext': True,
        'exsentences': sentences,
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
                extract = re.sub(r'\s+', ' ', extract).strip()
                return extract
    except Exception as e:
        print(f"  Error: {e}")

    return None

def get_wikipedia_bio_and_image(title):
    """Fetch bio and image from Norwegian Wikipedia."""
    params = {
        'action': 'query',
        'titles': title,
        'prop': 'extracts|pageimages',
        'exintro': True,
        'explaintext': True,
        'exsentences': 3,
        'piprop': 'thumbnail',
        'pithumbsize': 250,
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

            result = {}
            if 'extract' in page:
                result['bio'] = re.sub(r'\s+', ' ', page['extract']).strip()
            if 'thumbnail' in page:
                result['image_url'] = page['thumbnail']['source']

            return result if result else None
    except Exception as e:
        print(f"  Error: {e}")

    return None

def search_wikipedia(query):
    """Search Norwegian Wikipedia and return first result title."""
    params = {
        'action': 'query',
        'list': 'search',
        'srsearch': query,
        'srlimit': 1,
        'format': 'json'
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

        results = data.get('query', {}).get('search', [])
        if results:
            return results[0]['title']
    except:
        pass

    return None

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Ensure columns exist
    for col in [('persons', 'bio'), ('persons', 'image_url'), ('plays', 'synopsis')]:
        try:
            cursor.execute(f"ALTER TABLE {col[0]} ADD COLUMN {col[1]} TEXT")
            print(f"Added {col[1]} column to {col[0]}")
        except:
            pass
    conn.commit()

    print("\n=== ENRICHING PLAY SYNOPSES ===\n")

    # First add all known synopses
    print("Adding known synopses...")
    added = 0
    for title_pattern, synopsis in KNOWN_SYNOPSES.items():
        # Try exact match first, then partial
        cursor.execute("""
            UPDATE plays SET synopsis = ?
            WHERE (title = ? OR title LIKE ?) AND synopsis IS NULL
        """, (synopsis, title_pattern, f'%{title_pattern}%'))
        if cursor.rowcount > 0:
            added += cursor.rowcount
            print(f"  + {title_pattern}")
    conn.commit()
    print(f"Added {added} known synopses\n")

    # Try Wikipedia for plays by major playwrights
    cursor.execute("""
        SELECT p.id, p.title, per.name as playwright_name
        FROM plays p
        JOIN persons per ON p.playwright_id = per.id
        WHERE p.synopsis IS NULL
        AND per.wikipedia_url IS NOT NULL
        ORDER BY per.name, p.title
    """)
    plays = cursor.fetchall()

    print(f"Searching Wikipedia for {len(plays)} plays by known authors...")
    found = 0

    for play in plays:
        title = play['title']
        playwright = play['playwright_name']

        # Clean title for search
        clean_title = re.sub(r'\s*/\s*.*', '', title)  # Remove "/ alternative title"
        clean_title = re.sub(r'\s*\(.*\)', '', clean_title)  # Remove parenthetical

        # Try search patterns
        search_patterns = [
            f"{clean_title} (skuespill)",
            f"{clean_title} {playwright}",
            clean_title
        ]

        for pattern in search_patterns:
            wiki_title = search_wikipedia(pattern)
            if wiki_title:
                extract = get_wikipedia_extract(wiki_title)
                if extract and len(extract) > 50:
                    # Check if it's about a play
                    keywords = ['drama', 'skuespill', 'stykke', 'komedie', 'tragedie',
                               'teater', 'premiere', 'akt', 'scene', 'uroppført']
                    if any(kw in extract.lower() for kw in keywords):
                        cursor.execute("UPDATE plays SET synopsis = ? WHERE id = ?",
                                      (extract, play['id']))
                        conn.commit()
                        print(f"  + {title}: {extract[:50]}...")
                        found += 1
                        break
            time.sleep(0.2)

    print(f"\nFound {found} synopses from Wikipedia")

    print("\n=== ENRICHING AUTHOR BIOS ===\n")

    # Get authors with Wikipedia URLs but no bio
    cursor.execute("""
        SELECT id, name, wikipedia_url
        FROM persons
        WHERE wikipedia_url IS NOT NULL AND bio IS NULL
    """)
    persons = cursor.fetchall()

    print(f"Fetching bios for {len(persons)} authors...")

    for person in persons:
        wiki_title = person['wikipedia_url'].split('/')[-1].replace('_', ' ')
        data = get_wikipedia_bio_and_image(wiki_title)

        if data:
            updates = []
            params = []

            if 'bio' in data:
                updates.append("bio = ?")
                params.append(data['bio'])

            if 'image_url' in data:
                updates.append("image_url = ?")
                params.append(data['image_url'])

            if updates:
                params.append(person['id'])
                cursor.execute(f"UPDATE persons SET {', '.join(updates)} WHERE id = ?", params)
                conn.commit()
                print(f"  + {person['name']}")

        time.sleep(0.2)

    # Summary
    print("\n=== SUMMARY ===\n")

    cursor.execute("SELECT COUNT(*) FROM plays")
    total_plays = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM plays WHERE synopsis IS NOT NULL")
    plays_with_synopsis = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM persons WHERE id IN (SELECT DISTINCT playwright_id FROM plays WHERE playwright_id IS NOT NULL)")
    total_playwrights = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM persons WHERE bio IS NOT NULL AND id IN (SELECT DISTINCT playwright_id FROM plays WHERE playwright_id IS NOT NULL)")
    playwrights_with_bio = cursor.fetchone()[0]

    print(f"Plays with synopsis: {plays_with_synopsis}/{total_plays}")
    print(f"Playwrights with bio: {playwrights_with_bio}/{total_playwrights}")

    # Show sample
    print("\nSample synopses:")
    cursor.execute("SELECT title, synopsis FROM plays WHERE synopsis IS NOT NULL ORDER BY RANDOM() LIMIT 3")
    for row in cursor.fetchall():
        preview = row['synopsis'][:80] + '...' if len(row['synopsis']) > 80 else row['synopsis']
        print(f"  {row['title']}: {preview}")

    conn.close()

if __name__ == '__main__':
    main()
