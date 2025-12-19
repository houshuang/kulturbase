#!/usr/bin/env python3
"""
More play synopses to complete the enrichment.
"""

import sqlite3

DB_PATH = 'static/kulturperler.db'

# More play synopses
PLAY_SYNOPSES = {
    # Anonymous/unknown playwright
    'Bendik og Årolilja': 'En norsk folkevise dramatisert, om den tragiske kjærligheten mellom Bendik og Årolilja.',
    'Linje 5': 'Et samtidsdrama som utspiller seg på trikkelinje 5 i Oslo, med ulike menneskers historier.',
    'Mester Pierre Pathelin': 'En klassisk fransk farse fra middelalderen om en listig advokat.',
    'Myten om Orfeus og Eurydike': 'Den greske myten om Orfeus som reiser til underverdenen for å hente sin elskede.',
    'Utafor': 'Et drama om utenforskap og radikalisering blant unge.',

    # Aleksandr Vampilov
    'Hotell Tajgaen': 'Et russisk drama om mennesker som møtes på et hotell i Sibir.',

    # Alfonso Sastre
    'Den lille krittringen, også kjent som Den fillete dokka / Krittsirkelen - eventyret om den forlatte dokka': 'Et drama om en forlatt dukke og et barns fantasi.',

    # Andreas Markusson
    'Morgengaven': 'Et norsk drama om ekteskapets utfordringer.',

    # Arild Kolstad
    'Gruer-saken': 'Et drama basert på en virkelig kriminalsak.',
    'Ripsvin og reinlender': 'Et folkelivsbilde fra norsk bygdeliv.',

    # Arnljot Berg
    'Solveien seksten': 'Et drama fra et norsk borettslag.',

    # Arnljot Eggen
    'Pendlerne': 'Et drama om mennesker som pendler mellom by og bygd.',

    # Barthold Halle
    'Roser i ørkenen': 'Et poetisk drama om håp i vanskelige tider.',

    # Bernard Benson
    'Fredsboka': 'Et fredsbudskap dramatisert for barn.',

    # Birgit Linton-Malmfors
    'Velkomstmiddag': 'Et svensk kammerspill om en familiesammenkomst.',

    # Boris Vian
    'Trappen, eller Imperiebyggerne': 'En absurd allegori der en familie stadig flytter oppover i et hus mens rommet krymper.',
    'Generalenes te': 'En antimilitaristisk satire.',

    # Brendan Behan
    'Gisselet': 'En britisk soldat holdes som gissel av IRA i en Dublin-bordell. Tragikomisk mesterverk.',
    'Særlingen': 'Et drama om irsk identitet og ensomhet.',

    # Carin Mannheimer
    'Vi har da alltid hatt det så bra': 'Et svensk familiedrama om fasade og virkelighet.',

    # Cecilie Løveid
    'Kan du elske?': 'Et lyrisk drama om kjærlighet og identitet.',

    # Charles Ludlam
    'Mysteriet Myrna Vep': 'En camp-klassiker der to skuespillere spiller alle rollene i en gotisk parodi.',

    # Claire Luckham
    'Beslutningen': 'Et drama om vanskelige valg.',

    # Clive Exton
    'Jeg lar deg ikke glemme': 'Et psykologisk drama om minne og tap.',

    # Cora Sandel
    'Bare Alberte': 'Dramatisering av Sandels romaner om Alberte og hennes kamp for frihet.',
    'Flukten til Amerika': 'Et drama om emigrasjon og drømmer.',
    'Kranes konditori': 'En kvinne lever et monotont liv på et konditori til hun får en ny sjanse.',

    # Dan Taxbro
    'Rød bil til salgs': 'En dansk komedie.',

    # Dario Fo
    'Mistero buffo': 'Fos berømte one-man-show med middelalderhistorier om folket mot makten.',

    # David Eldridge
    'Begynnelse': 'Et drama om et par som møtes for første gang.',

    # David Mercer
    'Vi lever kvart vårt liv': 'Et drama om splittede liv.',

    # Edvard Rønning
    'Himmelplaneten': 'Et fantasifullt drama.',
    'Pappa Bues flyttedag': 'Et familiedrama.',

    # Edward Albee
    'Bessie Smiths død': 'Et drama om rasisme i amerikansk Sør, basert på blueslegenden Bessie Smiths død.',
    'Den amerikanske drømmen': 'En absurd satire over den amerikanske middelklassen og dens tomme verdier.',
    'Dyrehagehistorien / The Zoo Story / I dyrehagen': 'To menn møtes på en benk i Central Park. En intens konfrontasjon utspiller seg.',

    # Egon Wolff
    'Papirblomster': 'Et chilensk drama om klasse og makt.',

    # Eimear McBride
    'En jente er en halvferdig ting': 'Et eksperimentelt drama basert på McBrides roman.',

    # Erling Pedersen
    'Frihetens pris': 'Et drama om krigen og motstandskampen.',
    'Kvitveistid': 'Et vårdrama fra norsk bygd.',
    'Til odel og eie': 'Et drama om arv og eiendom.',

    # Erwin Sylvanus
    'Doktor Korczak og barna': 'Et drama om den polsk-jødiske legen som fulgte barna sine til gasskammeret.',

    # Espen Thorstenson
    'Fire sommerdager': 'Et drama om sommer og minner.',

    # Eugene O\'Neill
    'Den lange reisen hjem': 'Et tidlig O\'Neill-drama om sjøfolk.',
    'Hughie': 'En gammel spillemann forteller sin historie til en nattportier. Et intimt kammerspill.',

    # Eugène Ionesco
    'Delirium for to / Vær så go´ - galskap for to': 'Et absurd drama om et ektepar.',
    'Den skallete sangerinnen': 'Ionescos anti-stykke der språket bryter sammen. Absurdismens gjennombrudd.',
    'Privattimen': 'En professor myrder elevene sine. Absurd og skremmende.',
    'Stolene / Stolane': 'Et gammelt ektepar forbereder publikum til en viktig tale som aldri kommer.',

    # Eva Koefoed Sevaldson
    'Benjamin Bevers byggverk': 'Et barnedrama.',

    # Federico García Lorca
    'Bernardas hus': 'En tyrannisk mor holder døtrene sine innestengt etter farens død.',
    'Frøken Rosita': 'Et poetisk drama om en kvinne som venter på sin forlovede i 25 år.',

    # Fernando Arrabal
    'Frokost i det grønne / Utflukt til ytterste linje': 'Et surrealistisk anti-krigsstykke.',

    # Finn Carling
    'Fangen i det blå tårn': 'Et eksistensielt drama.',

    # Fjodor Dostojevskij
    'Den evige ektemann': 'Et drama basert på Dostojevskijs novelle om en mann som oppsøker kona sin tidligere elsker.',

    # Franz Kafka
    'Prosessen': 'Josef K. arresteres uten å vite hvorfor. Kafkas mareritt dramatisert.',

    # Franz Xaver Kroetz
    'Aprilbilder': 'Et tysk hverdagsdrama om vanlige menneskers liv.',

    # Friedrich Dürrenmatt
    'Besøk av en gammel dame / Besøk av ei gammal dame': 'Claire tilbyr en formue til hjembyen hvis de dreper mannen som sviktet henne.',

    # Fritz Hochwälder
    'Den uskyldige': 'Et drama om skyld og uskyld.',

    # Gabriel Arout
    'Skilsmissefeber': 'En komedie om ekteskapets opp- og nedturer.',

    # George Bernard Shaw
    'Mrs. Warrens forretning': 'Mrs. Warren driver bordeller, noe datteren oppdager. Et drama om moral og økonomi.',

    # George Furth
    'Twigs': 'Tre enaktere om kvinner i ulike livsfaser.',

    # Georges Berr
    'Min Søster og Jeg': 'En fransk komedie.',

    # Georges Feydeau
    'Fruens salige mor': 'En klassisk farsekunst om forviklinger.',

    # Gerhard Kelling
    'Arbeidsgivere': 'Et drama om makt på arbeidsplassen.',

    # Gert Hofmann
    'Borgermesteren': 'Et drama om makt og korrupsjon.',

    # Giles Cooper
    'Den ensomme vei': 'Et mystisk drama.',
    'Bli hos meg til morgen / Hvem er det der': 'Et spenningsdrama.',

    # Graham Greene
    'Den nøysomme elsker': 'En komedie om en beskjeden mann i kjærlighet.',

    # Gunnar Bull Gundersen
    'Noe å glede seg til - etspill for en nesten helt edru mann': 'En norsk monolog om alkohol og håp.',

    # Gunnar Staalesen
    'Falne engler': 'Et drama fra krimforfatteren Staalesen.',

    # Hans Bendrik
    'Høyt spill med fyrstikker': 'Et spenningsdrama.',

    # Hans Christian Branner
    'Søsken': 'Et dansk familiedrama.',

    # Hans Wiers-Jenssen
    'Jan Herwitz - Gamle Bergensbilleder': 'Historiske scener fra Bergen.',

    # Hans-Joachim Haecker
    'Minnedagen': 'Et tysk drama om minne og fortid.',
    'Vend deg ikke om': 'Et drama om å slippe fortiden.',

    # Hans-Magnus Ystgaard
    'Bydelen som ikke vil dø': 'Et drama om byfornyelse og motstand.',
    'La ditt problem bli vårt problem': 'Et sosialt drama.',
    'Mødrekupe': 'Et drama om moderskap.',

    # Harold Pinter
    'Den nye verdensorden': 'En sketsj om maktmisbruk og tortur.',
    'Går ut i kveld': 'Et drama om ekteskap og utroskap.',

    # Helge Hagerup
    'Den avskyelige snødamen': 'Et drama for barn.',
    'Katteslottet': 'Et barneteater om dyr og eventyr.',
    'Miranda': 'Et kjærlighetsdrama.',

    # Helge Krog
    'Hvem vet?': 'Et drama om livet og dets mysterier.',
    'Underveis': 'Et reisedrama om mennesker på vei.',

    # Henrik Wergeland
    'Efterspil til "Fjeldeventyret"': 'En fortsettelse av det norske nasjonalromantiske eventyret.',

    # Herbert Lichtenfeld
    'Herr Print oppdager seg selv': 'Et psykologisk drama om selverkjennelse.',
    'Tysklandsreisen': 'Et drama om å konfrontere fortiden.',

    # Herman Wouk
    'Mytteriet på Caine': 'Et rettsdrama om kapteinen på krigsskipet Caine og hans mentale sammenbrudd.',

    # Hugh Walpole
    'De gamle damene': 'Et britisk drama om aldrende kvinner.',

    # Idar Lind
    'En mann må gjøre det han må': 'Et norsk drama om plikter og valg.',

    # Ingeborg Refling Hagen
    'Vi løfter de lenkede hendene våre': 'Et drama om frigjøring.',

    # Ingmar Bergman
    'Scener fra et ekteskap': 'Bergmans intense utforskning av et ekteskaps oppløsning gjennom seks scener.',

    # István Örkény
    'Kattelek': 'En ungarsk tragedie om to søstre fanget i fortiden.',

    # Jacques-François Ancelot
    'Frieren og hans Ven': 'En fransk komedie om vennskap og kjærlighet.',

    # James Broom Lynne
    'En hyggelig fyr': 'Et britisk drama om en tilsynelatende hyggelig mann.',

    # James Patrick Donleavy
    'New York-idyller': 'Absurde scener fra New York.',

    # Jean Anouilh
    'Lerken / Lerka Jeanne d\'Arc': 'Anouilhs versjon av Jeanne d\'Arcs historie.',
    'Toreadorvalsen': 'En komedie om begjær og bedrag.',

    # Jean Cocteau
    'Stemmen / Din stemme / Menneskerøysta': 'En kvinne snakker i telefon med sin elsker som forlater henne.',

    # Jean Genet
    'Hushjelpene': 'To søstre drømmer om å myrde sin arbeidsgiver i et rituelt rollespill.',

    # Jean Giraudoux
    'Apollon fra Bellac': 'En komedie om skjønnhet og smiger.',

    # Jean Racine
    'Fedra': 'Den klassiske tragedien om Fedras forbudte kjærlighet til sin stesønn.',

    # Molière (Jean-Baptiste)
    'Den innbilt syke': 'Argan er overbevist om at han er dødssyk og omgir seg med leger. Molières siste stykke.',
    'Scapins skøierstreker': 'Tjeneren Scapin hjelper unge elskende med listige triks.',

    # Jean-Paul Sartre
    'Den anstendige skjøgen': 'Et drama om en kvinne som selger seg.',
    'Skitne hender': 'Et politisk drama om en ung kommunist som må drepe en partikamerat.',

    # Jerome Kilty
    'Kjære Løgnhals': 'Brevvekslingen mellom George Bernard Shaw og skuespillerinnen Mrs. Patrick Campbell.',

    # Jochen Ziem
    'Nyheter fra provinsen - 12 adferdsmønstre': 'Satiriske scener fra tysk provins.',

    # Johan Falkberget
    'Den fjerde nattevakt': 'Et gruvedrama fra Røros.',

    # John Boynton Priestley
    'Det er fra politiet': 'En mystisk komedie om identitet.',

    # John Hollen
    'Blant brødre': 'Et drama om brødre og familie.',
    'Nattsvermere': 'Et drama om mennesker som lever om natten.',

    # John Luton
    'De gamle mestrene': 'Et drama om kunst og aldring.',
    'Den som graver en grav': 'Et kriminaldrama.',

    # John Millington Synge
    'I skuggen av fjellet / Fjelldalens skygge': 'Et irsk drama om en gammel mann som later som han er død.',

    # John Osborne
    'Se deg om i vrede': 'Jimmy Porter raser mot det britiske klassesamfunnet. Stykket som startet "de sinte unge menn".',

    # Joop Admiraal
    'Du er moren min': 'Et nederlandsk familiedrama.',

    # Jorge Díaz
    'I denne lange natt / Canto libre': 'Et chilensk drama om undertrykkelse.',

    # Jules Feiffer
    'Mord i det hvite hus': 'En satirisk kriminalfortelling.',

    # Kaj Munk
    'Han sittter ved smeltedigelen / Han sit ved smeltedigelen': 'Et drama om en vitenskapsmann og hans ansvar.',

    # Karen Høie
    'Naboer': 'Et drama om naboskap og konflikter.',

    # Kateb Yacine
    'Nedjma': 'Et algerisk drama om kolonialisme og identitet.',

    # Kjell Askildsen
    'Du verden': 'Et eksistensielt drama basert på Askildsens tekster.',
    'Thomas F´s siste nedtegnelser til allmenheten': 'Et drama basert på novellen.',

    # Klaus Hagerup
    'Blå Fugler': 'Et drama om drømmer og flukt.',
    'Desperadosklubben og den mystiske mistenkte': 'Et barnemysterium.',
    'Rivalen': 'Et drama om konkurranse og vennskap.',

    # Knut Faldbakken
    'Kort opphold i Verona': 'Et norsk drama om reise og møter.',

    # Kristina Helle
    'Turnjentene': 'Et drama om unge turnere og press.',

    # Leck Fischer
    'Frisøndag': 'Et dansk drama om en fridag.',

    # Leif Inge Jacobsen
    'Det udødelige parti': 'Et sjakkdrama.',

    # Lennart Lidström
    'Milde himmel': 'Et svensk drama.',

    # Leonhard Frank
    'Karl og Anna': 'En soldat kommer hjem fra krigen og overtar sin døde kamerats identitet - og kone.',

    # Lorees Yerby
    'Orkesterplass til evigheten': 'Et drama om musikk og døden.',

    # Luigi Pirandello
    'For å skjule sin nakenhet': 'Et drama om sannhet og løgn.',

    # Margaret Johansen
    'Gamle venninner': 'Et drama om vennskap gjennom årene.',

    # Marguerite Duras
    'Hele dager i trærne': 'En mor og sønn konfronterer sin fortid.',
    'La musica': 'Et par som skilles, møtes en siste gang.',

    # Maria Irene Fornés
    'Vellykket liv for 3': 'Et absurd drama om tre kvinner.',

    # Marit Tusvik
    'Etter William': 'Et drama om et liv etter Shakespeare.',
    'Mugg': 'Et drama om forfall.',

    # Martin B. Duberman
    'I de hvites amerika': 'Et drama om rasisme i USA.',

    # Martin Walser
    'Den sorte svane': 'Et tysk drama om skyld og fortid.',

    # Mathis Mathisen
    'De blanke knappene': 'Et norsk drama.',
    'Trilopites': 'Et drama om fossiler og tid.',
    'Ærefrykt for livet': 'Et drama om livet og døden.',

    # Max Frisch
    'Dr. Philipp Hotz raser ut': 'En sveitsisk komedie om en mann i krise.',

    # Maxwell Anderson
    'Hun som ble Jeanne d\'Arc': 'Andersons versjon av Jeanne d\'Arc-historien.',
    'Vintersolhverv / Mot vår': 'Et drama om rettferdighet.',

    # May-Britt Skjelvik
    'Liv': 'Et drama om en kvinnes liv.',

    # Mayo Simon
    'Kunsten å overleve': 'Et drama om overlevelse og menneskelig styrke.',

    # Monica Isakstuen
    'Takk for gaven': 'Et norsk familiedrama.',

    # Morten Strøksnes
    'Havboka': 'Dramatisering av Strøksnes\' bok om havet og håkjerringfiske.',

    # Murray Schisgal
    'Kontoristene og Tigeren': 'En absurd komedie om kontorlivet.',

    # Märta Tikkanen
    'Århundrets kjærlighetssaga': 'En kvinnes oppgjør med sin alkoholiserte ektemann.',

    # Nikolaj Gogol
    'En gal manns dagbok': 'En embedsmann glir inn i galskap. Gogols mesterlige novelle dramatisert.',

    # Nikolaj Erdman
    'Skyt deg, Senja! / Stakkars helt / Gjør det fort, kjære!': 'En satirisk sovjetisk komedie.',

    # Nils Collett Vogt
    'Fangen': 'Et drama om fangenskap.',

    # Nils Kjær
    'Det lykkelige valg': 'Et drama om valg i livet.',

    # Nini Roll Anker
    'Den som henger i en tråd': 'Et drama om kvinner i vanskelige situasjoner.',
    'Kvinnen og den svarte fuglen': 'Et symbolsk drama om en kvinnes indre kamp.',

    # Noël Coward
    'Høyfeber, også kjent som Week-end': 'En kaotisk helg med familien Bliss.',

    # Ola Bauer
    'Mater': 'Et drama om en mor.',
    'Sabeltigerens sønn': 'Et drama om forhistorie og identitet.',

    # Olav Duun
    'Medmenneske': 'Et drama om nestekjærlighet fra Duuns univers.',

    # Olle Mattson
    'Lat ugraset vekse': 'Et svensk drama om natur og samfunn.',

    # Paal-Helge Haugen
    'Som natt og dag': 'Et poetisk drama.',

    # Per Olov Enquist
    'Den 25. timen': 'Et drama om en mann som venter på sin skjebne.',
    'Tribadernas natt': 'Et drama om Strindberg og hans første kone Siri von Essen.',

    # Peter Terson
    'Mooney og campingvognen': 'En britisk komedie om drømmer.',
    'Samaritanen': 'Et drama om å hjelpe andre.',

    # Peter Weiss
    'Ransakningen': 'Weiss\' dokumentardrama basert på Auschwitz-rettsakene.',

    # Pierre de Marivaux
    'Disputten / De evige spørsmål': 'En filosofisk komedie om natur og kultur.',

    # Reginald Rose
    'Sycamore Street': 'Et drama om et amerikansk nabolag.',

    # Robert Bolt
    'Ridder Bolle og hans kamp mot drager og baroner / Ridder Runde og hans kamp mot drager og baroner': 'Et eventyrlig barnedrama.',

    # Robert Patrick
    'Kennedys barn': 'Et drama om unge mennesker i New York etter Kennedy-mordet.',

    # Roger Hirson
    'Mordersken': 'Et kriminaldrama.',

    # Runar Schildt
    'Galgemannen': 'Et finlandssvensk drama om døden.',

    # Rønnaug Alten
    'Det angår ikke oss!': 'Et drama om likegyldighet og ansvar.',

    # Sandro Key-Åberg
    'Dannede mennesker': 'En satirisk komedie om dannelse.',

    # Saul Bellow
    'Ut av klemmen': 'En komedie basert på Bellows tekster.',

    # Sean O\'Casey
    'Er du våken, Angela?': 'Et irsk drama.',
    'Juno og påfuglen': 'En irsk familie rammes av borgerkrigen. Tragikomisk mesterverk.',
    'Raude roser åt meg': 'Et drama om drømmer og virkelighet.',
    'Skuggen av ein helt': 'Et irsk drama om heltemyter.',

    # Sidney Carroll
    'Julia Harrington': 'Et drama om en kvinnes liv.',

    # Sidsel Mørck
    'De spurte ikke meg': 'Et drama om overgrep og taushet.',

    # Sigbjørn Hølmebakk
    'Det siste kvarter': 'Et drama om livets siste fase.',
    'Pappa er ikke glad i oss lenger': 'Et familiedrama om skilsmisse.',

    # Sigrid Undset
    'I grålysningen': 'Et drama om overganger.',
    'Jenny': 'En ung kvinnelig kunstner i Roma søker frihet.',
    'Omkring Sedelighetsballet': 'Et drama om moral og samfunn.',
    'Selma Brøter': 'Et drama om en kvinnes kamp.',

    # Solveig Christov
    'Veversken': 'Et drama om tekstilarbeid og kvinneliv.',

    # Suzie Miller
    'Prima Facie': 'En forsvarsadvokat må revurdere alt når hun selv blir offer for overgrep.',

    # Svein Erik Brodal
    'Ælle menneskja mine': 'Et norsk drama på dialekt.',

    # Svend Ringdom
    'Duell': 'Et drama om konfrontasjon.',

    # Sverre Udnæs
    'Aske': 'Et drama om tap og sorg.',
    'Barbara': 'Et drama om en kvinne.',
    'Lek': 'Et drama om spill og virkelighet.',
    'Løvfall': 'Et høstdrama om aldring.',
    'Og du': 'Et intimt kammerspill.',
    'Skallet': 'Et drama om alderdom.',
    'Symptomer': 'Et drama om sykdom og tegn.',
    'Vinger': 'Et drama om frihet.',
    'Visittid': 'Et drama fra et sykehus.',

    # Sławomir Mrożek
    'En lykkelig begivenhet': 'En absurd komedie.',
    'Huset på grensen': 'Et polsk absurd drama.',
    'Politi, politi!': 'En satire over politistaten.',

    # Tankred Dorst
    'Krangel ved bymuren': 'Et tysk drama om konflikter.',

    # Tennessee Williams
    'Glassmenasjeriet': 'Tom ser tilbake på sin mor og søster Laura med hennes glassfigurer.',
    'Hilsen fra Bertha': 'En prostituert sender hilsener fra sitt dødsleie.',
    'Varsel for små farty': 'Et drama om mennesker på sjøen.',

    # Terence Rattigan
    'Avskjedsgaven': 'Et britisk drama om avskjed.',
    'Hånden på hjertet': 'Et drama om ærlighet.',

    # Terje Mærli
    'Aksel og Marit': 'Et norsk kjærlighetsdrama.',

    # Terje Stigen
    'Fridagen': 'Et drama om en fridag og dens betydning.',

    # Thomas Stearns Eliot
    'Cocktailparty': 'Gjester på et cocktailparty avslører sine hemmeligheter.',

    # Thornton Wilder
    'Den lykkelige reisen': 'En families reise blir en meditasjon over livet.',
    'Frankrikes dronninger': 'Et historisk drama.',

    # Tom Eyen
    '22. november - Den store leiegården': 'Et drama om Kennedy-attentatet.',

    # Tor Åge Bringsværd
    'Kjemp for alt hva du har kjært': 'Et norsk drama om verdier.',
    'Kodémus': 'Et eventyrlig drama.',

    # Torun Lian
    'Afrika': 'Et drama om drømmer og fjerne steder.',
    'Spor': 'Et drama om å følge spor.',

    # Ulf Breistrand
    'Fedrelandet': 'Et drama om nasjon og tilhørighet.',

    # Ursula Krechel
    'Erika': 'Et drama om en kvinne.',

    # Václav Havel
    'Innvielse': 'Et drama om å bli innviet i systemet.',
    'Sirkulæret': 'En byråkratisk satire.',

    # Veronica Salinas
    'Vinduer': 'Et drama om innsyn og utsyn.',

    # Vibeke Idsøe
    'Høstens første bilde': 'Et drama om kunst og årstider.',
    'Michael Jordan og hun med håret': 'Et ungdomsdrama.',

    # Victor Borg
    'Helene': 'Et drama om en kvinne.',

    # Victor Hugo
    'Århundrenes legende AKA Århundredernes legende': 'Hugos episke verk dramatisert.',

    # Victorien Sardou
    'Patriot / Alt for fedrelandet': 'Et patriotisk drama.',

    # Vidar Sandem
    'KLAAR....EN...TOO....KJØØØØR': 'Et norsk drama om start og bevegelse.',

    # Vigdis Stokkelien
    'Før sjøforklaringen': 'Et drama om en sjøulykke.',
    'Granaten': 'Et drama om krig og ettervirkninger.',

    # Vilhelm Krag
    'De Gamles Julaften': 'Et nostalgisk juledrama.',

    # William Inge
    'Kom tilbake, lille Sheba / Kom hjem igjen, lille Sheba': 'Et ektepar sørger over den hunden de mistet - og livet som forsvant.',

    # William Saroyan
    'Østersen og perlen': 'En optimistisk komedie om hverdagslige mirakler.',

    # Willis Hall
    'Utenfor sesongen': 'Et britisk drama.',

    # Zeshan Shakar
    'Abrahams barn': 'Svein Tindbergs forestilling om religionsdialog mellom jødedom, kristendom og islam.',

    # Åse Vikene
    'På vinterveier': 'Et norsk vinterdrama.',

    # Ödön von Horváth
    'Sladek den svarte riksvernsmann': 'Et drama om fascismens fremvekst.',

    # Påske by Aksel-Otto Bull
    'Påske': 'Et påskedrama.',
}

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("=== Adding more play synopses ===\n")
    added = 0
    for title, synopsis in PLAY_SYNOPSES.items():
        cursor.execute("UPDATE plays SET synopsis = ? WHERE title = ? AND synopsis IS NULL", (synopsis, title))
        if cursor.rowcount > 0:
            print(f"  + {title}")
            added += cursor.rowcount
        else:
            # Try partial match
            cursor.execute("UPDATE plays SET synopsis = ? WHERE title LIKE ? AND synopsis IS NULL",
                          (synopsis, f'%{title}%'))
            if cursor.rowcount > 0:
                print(f"  + {title} (partial)")
                added += cursor.rowcount

    conn.commit()
    print(f"\nAdded {added} synopses")

    # Summary
    cursor.execute("SELECT COUNT(*) FROM plays WHERE synopsis IS NOT NULL")
    with_synopsis = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM plays")
    total = cursor.fetchone()[0]

    print(f"\nPlays with synopsis: {with_synopsis}/{total} ({100*with_synopsis//total}%)")

    # Show remaining
    cursor.execute("SELECT title FROM plays WHERE synopsis IS NULL ORDER BY title")
    remaining = [r[0] for r in cursor.fetchall()]
    if remaining:
        print(f"\nRemaining without synopsis ({len(remaining)}):")
        for title in remaining[:20]:
            print(f"  - {title}")
        if len(remaining) > 20:
            print(f"  ... and {len(remaining)-20} more")

    conn.close()

if __name__ == '__main__':
    main()
