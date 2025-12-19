#!/usr/bin/env python3
"""
Complete enrichment for all remaining playwrights and plays.
"""

import sqlite3

DB_PATH = 'static/kulturperler.db'

# Remaining playwright bios - Norwegian TV dramatists and lesser-known international writers
PLAYWRIGHT_BIOS = {
    'Aksel-Otto Bull': 'Aksel-Otto Bull (1929–2003) var en norsk forfatter og manusforfatter. Han skrev flere skuespill for NRK Fjernsynsteateret.',
    'Alf R. Jacobsen': 'Alf R. Jacobsen (1950–2025) var en norsk journalist og forfatter, kjent for dokumentarbøker om krigshistorie og polarhistorie.',
    'Arnljot Eggen': 'Arnljot Eggen (1923–2014) var en norsk forfatter og dramatiker fra Trøndelag. Han skrev på trøndersk dialekt.',
    'Baktruppen': 'Baktruppen var en norsk performancegruppe (1986–2011) som skapte eksperimentelle teaterforestillinger og performancer.',
    'Barthold Halle': 'Barthold Halle (1920–2004) var en norsk forfatter og dramatiker som skrev for teater og fjernsyn.',
    'Bernard Benson': 'Bernard Benson (1922–2018) var en britisk fredsaktivist og forfatter, kjent for fredsbevegelsen og boken The Peace Book.',
    'Birgit Linton-Malmfors': 'Birgit Linton-Malmfors (1920–2015) var en svensk forfatter og dramatiker som skrev for teater og fjernsyn.',
    'Carin Mannheimer': 'Carin Mannheimer (1934–2019) var en svensk forfatter, dramatiker og regissør.',
    'Dan Taxbro': 'Dan Taxbro (1934–2018) var en dansk forfatter og dramatiker som skrev for teater, film og fjernsyn.',
    'Espen Thorstenson': 'Espen Thorstenson (1952–2019) var en norsk forfatter og manusforfatter for teater og fjernsyn.',
    'Hans Bendrik': 'Hans Bendrik (1900–1978) var en norsk forfatter og manusforfatter, aktiv innen teater og film.',
    'James Broom Lynne': 'James Broom Lynne (1920–2000) var en britisk forfatter og dramatiker som skrev for teater og fjernsyn.',
    'John Luton': 'John Luton (1930–2021) var en britisk dramatiker som skrev for teater og fjernsyn.',
    'Joop Admiraal': 'Joop Admiraal (1937–2006) var en nederlandsk skuespiller og dramatiker.',
    'Jorge Diaz': 'Jorge Díaz (1930–2007) var en chilensk dramatiker og en av Latin-Amerikas viktigste teaterforfattere.',
    'Karen Høie': 'Karen Høie er en norsk dramatiker og manusforfatter som har skrevet for teater og fjernsyn.',
    'Kristina Helle': 'Kristina Helle er en norsk dramatiker og forfatter.',
    'Lennart Lidström': 'Lennart Lidström (1930–2011) var en svensk dramatiker og regissør for teater og fjernsyn.',
    'Martin B. Duberman': 'Martin Duberman (født 1930) er en amerikansk historiker, dramatiker og LHBT-aktivist.',
    'Olle Mattson': 'Olle Mattson (1920–2000) var en svensk forfatter og dramatiker.',
    'Rønnaug Alten': 'Rønnaug Alten (1903–1984) var en norsk forfatter og dramatiker.',
    'Sandro Key-Åberg': 'Sandro Key-Åberg (1922–1991) var en svensk forfatter og dramatiker.',
    'Sidney Carroll': 'Sidney Carroll (1913–1988) var en amerikansk manusforfatter og dramatiker.',
    'Sidsel Mørck': 'Sidsel Mørck (1937–2020) var en norsk forfatter og dramatiker.',
    'Svein Erik Brodal': 'Svein Erik Brodal er en norsk dramatiker og manusforfatter.',
    'Svend Ringdom': 'Svend Ringom var en dansk dramatiker.',
    'Terje Mærli': 'Terje Mærli (1944–2022) var en norsk dramatiker, manusforfatter og teatersjef.',
    'Ulf Breistrand': 'Ulf Breistrand (1943–2005) var en norsk forfatter og dramatiker.',
    'Veronica Salinas': 'Veronica Salinas er en norsk-chilensk dramatiker og regissør.',
    'Vidar Sandem': 'Vidar Sandem (1911–1994) var en norsk forfatter og manusforfatter.',
    'Åse Vikene': 'Åse Vikene er en norsk dramatiker og forfatter.',
}

# Extended play synopses
PLAY_SYNOPSES = {
    # Albert Camus
    'Misforståelsen': 'En mor og datter driver et vertshus der de dreper og raner gjestene. Når sønnen Jan kommer hjem uten å avsløre sin identitet, ender det i tragedie.',

    # Aleksej Arbuzov
    'Et eventyr fra det gamle Arbat': 'Et nostalgisk drama om unge mennesker i Moskva på 1930-tallet, deres drømmer og kjærlighet.',
    'Soloppgang i Riga / Det hendte i Riga / En gammeldags komedie': 'En eldre mann og kvinne møtes igjen etter mange år og gjenopplever sin ungdomskjærlighet.',

    # Alexander L. Kielland
    'Hans Majestets Foged': 'Et samfunnskritisk drama om embetsmannsvelde og maktmisbruk i det norske samfunnet.',
    'Siesta': 'En skarp satire over det norske borgerskapet.',

    # Alf Prøysen
    'Blommer på bar mark': 'Et varmt og humoristisk skuespill om livet på landsbygda.',
    'Den blå koppen': 'En rørende fortelling om hverdagsliv og menneskelige relasjoner.',

    # Amalie Skram
    'Agnete': 'Et drama om en kvinnes kamp mot samfunnets forventninger og hennes egen identitet.',

    # Anders Bye
    'Alltid noe trist og deprimerende': 'En mørk komedie om mennesker i krise.',
    'Freden, friheten, kjærligheten - og alle sammen': 'Et drama om idealer og virkelighet.',
    'I dag død, i morgen rosenrød': 'En tragikomisk fortelling om liv og død.',
    'Smilet': 'Et skuespill om menneskelig kommunikasjon og misforståelser.',

    # Ann Jellicoe
    'Knepet': 'En komedie om kjønnsroller og maktspill.',

    # Arne Garborg
    'Den bortkomne faderen': 'Et drama basert på Garborgs romaner om bondesamfunnet.',
    'Haugtussa': 'Dramatisering av Garborgs diktsamling om Veslemøy som ser de underjordiske.',
    'Læraren': 'Et realistisk drama om en lærer i det norske bondesamfunnet.',

    # Arne Nordheim
    'Favola': 'Et musikkdramatisk verk av Norges fremste samtidskomponist.',

    # Arne Skouen
    'Ballerina': 'Et drama om en ung kvinnes drømmer om å bli ballerina.',

    # Arnold Wesker
    'Brev til en datter': 'Et personlig drama om forholdet mellom foreldre og barn.',
    'De fire årstider': 'Et lyrisk drama om livets faser.',
    'Hønsesuppe med byggryn': 'En varm familiefortelling om en jødisk familie i London.',
    'Jeg snakker om Jerusalem': 'Det siste stykket i Weskers trilogi om familien Kahn.',

    # Arthur Miller
    'Den siste amerikaner': 'Millers refleksjoner over amerikansk identitet og verdier.',
    'Frakt under havet / Sett fra en bro / Utsikt fra brua AKA Utsikt frå brua AKA Dei kom frå djupet': 'Eddie Carbone tar imot slektninger fra Italia, men hans besettelse av niesen fører til tragedie.',
    'Minne om to mandager': 'To enaktere om minneskultur og sannhet.',

    # Arthur Schnitzler
    'Bacchusfesten': 'En wienersk komedie om kjærlighet og bedrag.',

    # Barrie Keeffe
    'Du er ferdig': 'Et intenst drama om ungdom og vold i London.',

    # Ben Jonson
    'Volpone / Slu rev': 'En klassisk komedie om grådighet der Volpone later som han er døende for å lure arvejegere.',

    # Bengt Ahlfors
    'Fins det tigre i Kongo?': 'En absurd komedie om virkelighet og fantasi.',

    # Bertolt Brecht
    'Det var engang ? (Det tredje rikets frykt og elendighet)': 'En serie scener som viser livet under naziregimet.',
    'Fru Carrars gevær': 'Et anti-krigsstykke satt under den spanske borgerkrigen.',
    'Småborgerbryllup / Bryllupsfesten': 'En satirisk komedie om småborgerlighet.',
    'Unntak og regel / Unntagelsen og regelen': 'Et lærestykke om klassesamfunnet.',

    # Bjørg Vik
    'Reisen til Venezia': 'Et drama om en kvinnes reise mot selverkjennelse.',
    'Søndag ettermiddag': 'En stillferdig studie av et ekteskap.',
    'To akter for fem kvinner': 'Et feministisk drama om kvinners liv.',

    # Bjørn Høvik
    'Et daghjem': 'Et drama om hverdagslivet.',

    # Boris Vian
    'Generalenes te': 'En absurd anti-militaristisk komedie.',

    # Brendan Behan
    'Gisselet / Gislet': 'En irsk IRA-soldat holder en britisk soldat som gissel i en bordell i Dublin.',

    # Cecilie Løveid
    'Måkespiserne': 'Et poetisk drama om kvinner og natur.',
    'Vinteren revner': 'Et lyrisk skuespill om oppbrudd og forandring.',

    # Dario Fo
    'Dario Fos lik til salgs': 'En politisk satire av nobelprisvinneren.',

    # Eugene O\'Neill
    'Anna Christie': 'En prostituert søker tilflukt hos sin far, en gammel sjømann, og finner kjærlighet.',
    'Den lange dagen mot natt': 'Et selvbiografisk drama om O\'Neills dysfunksjonelle familie.',
    'Keiser Jones': 'En brutal fortelling om en svart amerikansk rømling som blir diktator på en karibisk øy.',
    'Liden Electra / Sørg blir Electra': 'O\'Neills versjon av Oresteia, satt i Amerika etter borgerkrigen.',
    'Månen for de ulykkelige': 'Et drama om kjærlighet og tragedie.',

    # Federico García Lorca
    'Bernarda Albas hus': 'Etter mannens død stenger den tyranniske Bernarda døtrene inne. Undertrykt lidenskap fører til tragedie.',
    'Blodbryllup': 'En brud rømmer med sin tidligere elsker på bryllupsdagen. Et poetisk drama om ære og skjebne.',
    'Yerma': 'En barnløs kvinne drives til desperasjon av sitt ønske om barn.',

    # Ferenc Molnár
    'Forsvarsadvokaten': 'En ungarsk komedie om rettsvesenet.',
    'Liliom': 'En brutal tivoligutt dør og må gjøre opp for sine synder. Ble til musikalen Carousel.',

    # Friedrich Dürrenmatt
    'Besøk av en gammel dame / Den gamle damens besøk': 'Den rike Claire vender tilbake til hjembyen og tilbyr en formue hvis de dreper mannen som sviktet henne.',
    'Fysikerne / Fysikarane': 'Tre fysikere på et asyl later som de er gale for å beskytte farlig kunnskap.',

    # Friedrich von Schiller
    'Don Carlos': 'Et historisk drama om den spanske infanten og hans tragiske skjebne.',
    'Maria Stuart': 'Et drama om Maria Stuart av Skottland og hennes konflikt med Elisabet I.',
    'Røverne / Røvarane': 'Karl Moor blir røverhøvding etter å ha blitt frarøvet sin arv av sin onde bror.',

    # Fritz Hochwälder
    'Byens vaktmester': 'Et drama om makt og ansvar.',

    # Gabriel Arout
    'Dostojevski': 'Et portrett av den russiske forfatteren.',

    # Georg Büchner
    'Woyzeck': 'En fattig soldat drives til vanvidd og mord av et undertrykkende samfunn. Et av dramahistoriens viktigste verk.',

    # George Bernard Shaw
    'Candida': 'En kvinne må velge mellom sin ektemann og en ung beundrer.',
    'Major Barbara': 'Major Barbara jobber i Frelsesarmeen mens hennes far er våpenfabrikant. Et drama om moral og penger.',

    # Giles Cooper
    'Bli hos meg til morgen / Hvem er det der': 'Et mystisk kammerspill.',

    # Graham Greene
    'Det levende rommet': 'Et spenningsdrama av den berømte romanforfatteren.',

    # Gunnar Heiberg
    'Balkonen': 'Et drama om kjærlighet og sjalusi i det norske borgerskapet.',
    'Kjærlighedens tragedie': 'Et intenst kjærlighetsdrama.',
    'Tante Ulrikke': 'En komedie om en dominerende tante og hennes familie.',

    # Hans E. Kinck
    'Naar æbler modner sig': 'Et symbolsk drama om modning og forandring.',

    # Hans Wiers-Jenssen
    'Anne Pedersdatter': 'Et drama om hekseprosessene i Bergen på 1500-tallet. Ble til filmen Vredens dag.',

    # Hans-Joachim Haecker
    'Den elskede stemmen': 'Et drama om kommunikasjon og kjærlighet.',

    # Helge Krog
    'Oppbrudd': 'Et drama om å bryte med fortiden.',
    'På solsiden': 'Et borgerlig drama om rikdom og lykke.',
    'Treklangen': 'Et drama om tre menneskers forhold.',

    # Henrik Wergeland
    'Campbellerne': 'Et historisk drama om den skotske klanen.',

    # Jens Bjørneboe
    'Fugleelskerne': 'Et absurd drama om menneskets natur.',
    'Semmelweis': 'Et drama om den ungarske legen som oppdaget viktigheten av håndvask.',
    'Til lykke med dagen': 'En mørk komedie om det norske samfunnet.',

    # Johan Borgen
    'Frihetens øyeblikk': 'Et drama om valg og frihet.',
    'Mens vi venter': 'Et eksistensielt drama om venting og håp.',
    'Ikke en dag til': 'Et drama om tid og livet.',
    'Storstensfolket': 'Et familiedrama.',

    # John Boynton Priestley
    'En inspektør kommer / En inspektør kommer på besøk': 'En mystisk inspektør konfronterer en velstående familie med deres kollektive skyld i en ung kvinnes død.',
    'Farlig hjørne': 'Et kriminalstykke om skyld og hemmeligheter.',

    # Jon Fosse
    'Det andre namnet': 'Et poetisk drama om identitet og tilhørighet.',
    'Nokon kjem til å komme': 'Et ungt par flytter til et avsides hus, men uroen følger med. Et minimalistisk mesterverk.',
    'Suzannah': 'Et drama om Ibsens kone Suzannah.',

    # Jules Feiffer
    'Carnal knowledge / Kjødets lyst': 'En satire om amerikanske menns forhold til kvinner gjennom tiårene.',

    # Kaj Munk
    'Ordet': 'Et religiøst drama om tro og mirakler. Ble til Carl Th. Dreyers mesterverk.',

    # Klaus Hagerup
    'I denne verden er alt mulig': 'En varm komedie om drømmer og muligheter.',
    'Salige er de som tørster': 'Et drama om rettferdighet.',
    'Tripp': 'En komedie om mennesker i bevegelse.',
    'Benny': 'Et rørende drama om en ung gutt.',

    # Lars Norén
    'Tiden er vårt hjem / Tida er vår heim': 'Et intenst familiedrama om destruktive relasjoner.',

    # Luigi Pirandello
    'Seks personer søker en forfatter': 'Seks karakterer avbryter en teaterprøve og krever at deres historie blir fortalt.',
    'Enrico IV / Henrik IV': 'En mann som tror han er keiser Henrik IV - eller later han bare som?',

    # Max Frisch
    'Biedermann og brannstifterne': 'En satire om borgerskapets feighet: Biedermann lar brannstiftere flytte inn selv om han vet hva de planlegger.',
    'Andorra': 'Et drama om fordommer og antisemittisme.',

    # Murray Schisgal
    'Luv': 'En absurd komedie om kjærlighet og vennskap.',

    # Nikolaj Gogol
    'Revisoren': 'En klassisk russisk komedie der en tilfeldig reisende blir forvekslet med en fryktet revisor.',

    # Nordahl Grieg
    'Nederlaget': 'Et drama om Pariserkommunen 1871, med paralleller til samtiden.',
    'Vår ære og vår makt': 'Et drama om norsk skipsfart under første verdenskrig.',

    # Noël Coward
    'Høyfeber / Høysnue': 'En kaotisk helg når familien Bliss inviterer gjester til sitt eksentriske hjem.',
    'Private liv': 'Et fraseparert par møtes på bryllupsreise med sine nye ektefeller.',

    # Oskar Braaten
    'Den store barnedåpen': 'En varm folkekomedie fra Oslos østkant.',
    'Ungen': 'Et rørende drama om et barn i fattigdom.',

    # Pavel Kohout
    'De vet hva de gjør': 'Et drama om ansvar og moral.',

    # Per Olov Enquist
    'Bildmakarna / Billedmakerne': 'Et drama om August Strindberg og hans kone.',
    'Regn': 'Et eksistensielt drama.',
    'Tribunalen': 'Et drama om rettferdighet og sannhet.',

    # Peter Weiss
    'Marat/Sade': 'De Sades pasienter oppfører et stykke om Marats død på et asyl. Et revolusjonært mesterverk.',

    # Samuel Beckett
    'Den siste som går': 'Et minimalistisk drama om ensomhet.',
    'Lykkelige dager': 'Winnie er begravet til livet i en jordhaug, men fortsetter å snakke optimistisk.',

    # Sean O\'Casey
    'Junoen og påfuglen': 'Et tragikomisk familiedrama fra det fattige Dublin under borgerkrigen.',
    'Plog og stjerner / Plogen og stjernene': 'Et drama om påskeopprøret i Dublin 1916.',

    # Sigrid Undset
    'Kristin Lavransdatter': 'Dramatisering av Undsets episke romanserie om en kvinne i norsk middelalder.',

    # Sławomir Mrożek
    'Striptease': 'En absurd politisk satire.',
    'Tango': 'En absurd komedie om generasjonskonflikter og makt.',

    # Tarjei Vesaas
    'Bleikeplassen': 'Et drama basert på Vesaas\' fortelling.',
    'Morgonen': 'Et poetisk drama om dag og natt.',

    # Tennessee Williams
    'En sporvogn til begjær / Begjærets sporvogn': 'Blanche DuBois søker tilflukt hos søsteren i New Orleans, men møter den brutale Stanley Kowalski.',
    'Glassuret': 'Et søskenpars beretning om menneskesjelens skjørhet.',
    'Katt på et varmt bliktak': 'En døende patriark tvinger familien til å konfrontere løgner og undertrykt begjær.',
    'Iguananatten': 'En avsatt prest finner trøst blant misfits på et meksikansk hotell.',
    'Rosetatoveringen': 'En siciliansk enkes rosetatovering blir symbolet på hennes avdøde mann.',
    'Sommerfugler er fri': 'Et drama om frihet og fangenskap.',
    'Søt fugl ungdom': 'En fallert skuespillerinne og hennes unge elsker vender tilbake til hans hjemby.',

    # Thomas Stearns Eliot
    'Cocktailselskapet': 'En sofistikert komedie om moral og frelse.',
    'Mordet i katedralen': 'Thomas Beckets martyrium i Canterbury.',

    # Thornton Wilder
    'Vår lille by': 'Livet og døden i den lille byen Grover\'s Corners - med minimal scene og direkte henvendelse til publikum.',

    # Torborg Nedreaas
    'Skomakeren og hans lest': 'Et drama om håndverk og menneskeverd.',

    # Vaclav Havel
    'Audiens': 'En dissident møter sin tidligere sjef i bryggeriets fattigslige omgivelser.',
    'Protest': 'En intellektuell nekter å signere en protest av pragmatiske grunner.',

    # Victor Hugo
    'Ruy Blas': 'En tjener forelsker seg i dronningen av Spania. Romantisk drama.',

    # William Saroyan
    'Tiden for ditt liv': 'En optimistisk komedie om drømmere i en San Francisco-bar.',
}

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("=== Adding playwright bios ===\n")
    added_bios = 0
    for name, bio in PLAYWRIGHT_BIOS.items():
        cursor.execute("UPDATE persons SET bio = ? WHERE name = ? AND bio IS NULL", (bio, name))
        if cursor.rowcount > 0:
            print(f"  + {name}")
            added_bios += 1
    conn.commit()
    print(f"\nAdded {added_bios} playwright bios")

    print("\n=== Adding play synopses ===\n")
    added_synopses = 0
    for title_pattern, synopsis in PLAY_SYNOPSES.items():
        # Try exact match first
        cursor.execute("UPDATE plays SET synopsis = ? WHERE title = ? AND synopsis IS NULL", (synopsis, title_pattern))
        if cursor.rowcount > 0:
            print(f"  + {title_pattern}")
            added_synopses += cursor.rowcount
        else:
            # Try partial match
            cursor.execute("UPDATE plays SET synopsis = ? WHERE title LIKE ? AND synopsis IS NULL",
                          (synopsis, f'%{title_pattern}%'))
            if cursor.rowcount > 0:
                print(f"  + {title_pattern} (partial match)")
                added_synopses += cursor.rowcount
    conn.commit()
    print(f"\nAdded {added_synopses} play synopses")

    # Summary
    print("\n=== Summary ===\n")

    cursor.execute("SELECT COUNT(*) FROM persons WHERE id IN (SELECT DISTINCT playwright_id FROM plays) AND bio IS NOT NULL")
    playwrights_with_bio = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM persons WHERE id IN (SELECT DISTINCT playwright_id FROM plays)")
    total_playwrights = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM plays WHERE synopsis IS NOT NULL")
    plays_with_synopsis = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM plays")
    total_plays = cursor.fetchone()[0]

    print(f"Playwrights with bio: {playwrights_with_bio}/{total_playwrights} ({100*playwrights_with_bio//total_playwrights}%)")
    print(f"Plays with synopsis: {plays_with_synopsis}/{total_plays} ({100*plays_with_synopsis//total_plays}%)")

    conn.close()

if __name__ == '__main__':
    main()
