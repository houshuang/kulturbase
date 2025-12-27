#!/usr/bin/env python3
"""Import Swedish radio theatre from Yle (Finnish Broadcasting Company)."""

import yaml
from pathlib import Path

DATA_DIR = Path('data')

def save_yaml(path, data):
    """Save data to YAML file."""
    with open(path, 'w') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

# Starting IDs
next_play_id = 3433
next_person_id = 4758
next_perf_id = 3294

# Track created persons to avoid duplicates
persons = {}

def create_person(name, birth_year=None, nationality='Finnish-Swedish', bio=None, wikipedia_url=None):
    """Create a person entry."""
    global next_person_id
    if name in persons:
        return persons[name]

    person_id = next_person_id
    next_person_id += 1

    person_data = {
        'id': person_id,
        'name': name,
        'normalized_name': name.lower(),
    }
    if birth_year:
        person_data['birth_year'] = birth_year
    person_data['nationality'] = nationality
    if bio:
        person_data['bio'] = bio
    if wikipedia_url:
        person_data['wikipedia_url'] = wikipedia_url

    save_yaml(DATA_DIR / 'persons' / f'{person_id}.yaml', person_data)
    persons[name] = person_id
    print(f"Created person {person_id}: {name}")
    return person_id

def create_play(play_id, title, playwright_id=None, year_written=None, synopsis=None,
                category='teater', work_type='radioteater', language='sv'):
    """Create a play/work entry."""
    play_data = {
        'id': play_id,
        'title': title,
        'language': language,
        'category': category,
        'work_type': work_type,
    }
    if playwright_id:
        play_data['playwright_id'] = playwright_id
    if year_written:
        play_data['year_written'] = year_written
    if synopsis:
        play_data['synopsis'] = synopsis

    save_yaml(DATA_DIR / 'plays' / f'{play_id}.yaml', play_data)
    print(f"Created play {play_id}: {title}")
    return play_id

def create_performance(perf_id, work_id, title, year, director_id=None, credits=None,
                       source='yle', medium='radio', duration=None):
    """Create a performance entry."""
    perf_data = {
        'id': perf_id,
        'work_id': work_id,
        'title': title,
        'source': source,
        'medium': medium,
        'year': year,
    }
    if duration:
        perf_data['total_duration'] = duration
    if credits:
        perf_data['credits'] = credits

    save_yaml(DATA_DIR / 'performances' / f'{perf_id}.yaml', perf_data)
    print(f"Created performance {perf_id}: {title}")
    return perf_id

def create_episode(prf_id, title, performance_id, year=None, duration=None,
                   description=None, nrk_url=None, episode_number=None):
    """Create an episode entry."""
    ep_data = {
        'prf_id': prf_id,
        'title': title,
        'performance_id': performance_id,
        'source': 'yle',
        'medium': 'radio',
        'language': 'sv',
    }
    if year:
        ep_data['year'] = year
    if duration:
        ep_data['duration_seconds'] = duration
    if description:
        ep_data['description'] = description
    if nrk_url:
        ep_data['nrk_url'] = nrk_url
    if episode_number:
        ep_data['episode_number'] = episode_number

    save_yaml(DATA_DIR / 'episodes' / f'{prf_id}.yaml', ep_data)
    print(f"Created episode {prf_id}: {title}")
    return prf_id

# ============================================================================
# IMPORT YLE SWEDISH RADIO THEATRE
# ============================================================================

print("\n=== Importing Yle Swedish Radio Theatre ===\n")

# ----------------------------------------------------------------------------
# 1. MEDEAS DOTTER (2023) - Prix Italia finalist
# ----------------------------------------------------------------------------
are_nikkinen = create_person('Are Nikkinen', nationality='Finnish',
                              bio='Finsk dramatiker och manusförfattare.')
jessica_eden = create_person('Jessica Edén', nationality='Finnish-Swedish',
                              bio='Finlandssvensk regissör och producent vid Svenska Yle.')
tyra_wingren = create_person('Tyra Wingren', nationality='Finnish-Swedish',
                              bio='Finlandssvensk skådespelare och modell.')
jessica_grabowsky = create_person('Jessica Grabowsky', nationality='Finnish-Swedish',
                                   bio='Finlandssvensk skådespelare.')
elmer_back = create_person('Elmer Bäck', nationality='Finnish-Swedish',
                            bio='Finlandssvensk skådespelare.')

play_medeas = create_play(
    next_play_id,
    'Medeas dotter',
    playwright_id=are_nikkinen,
    year_written=2023,
    synopsis='En 16-årig flicka vid namn Hanna ser sin värld rasa samman när hennes styvfar Jacob lämnar hennes mor för en kollega. Tillsammans med sina vänner Theo och Zaida planerar Hanna hämnd, men planen får katastrofala följder. Nominerad till Prix Italia 2024.'
)
next_play_id += 1

perf_medeas = create_performance(
    next_perf_id, play_medeas, 'Medeas dotter', 2023,
    director_id=jessica_eden,
    credits=[
        {'person_id': tyra_wingren, 'role': 'actor', 'character_name': 'Hanna'},
        {'person_id': jessica_grabowsky, 'role': 'actor', 'character_name': 'Kajsa'},
        {'person_id': elmer_back, 'role': 'actor', 'character_name': 'Jacob'},
        {'person_id': jessica_eden, 'role': 'director'},
    ],
    duration=6300  # 3 x 35 min
)
next_perf_id += 1

# Create 3 episodes for Medeas dotter
for i in range(1, 4):
    create_episode(
        f'YLE_MEDEAS_{i}',
        f'Medeas dotter, del {i}',
        perf_medeas,
        year=2023,
        duration=2100,  # 35 min
        episode_number=i,
        nrk_url='https://arenan.yle.fi/'
    )

# ----------------------------------------------------------------------------
# 2. LYSSNAR PÅ KILLAR (2019)
# ----------------------------------------------------------------------------
ida_kronholm = create_person('Ida Kronholm', nationality='Finnish-Swedish',
                              bio='Finlandssvensk dramatiker och regissör.')
sara_soulie = create_person('Sara Soulié', nationality='Finnish-Swedish',
                             bio='Finlandssvensk skådespelare.')
pelle_heikkila = create_person('Pelle Heikkilä', nationality='Finnish-Swedish',
                                bio='Finlandssvensk skådespelare.')

play_killar = create_play(
    next_play_id,
    'Lyssnar på killar - ett hörspel om bortslösade timmar',
    playwright_id=ida_kronholm,
    year_written=2019,
    synopsis='Ett ljuddrama som utforskar bortslösad tid genom ett ensemble av karaktärer.'
)
next_play_id += 1

perf_killar = create_performance(
    next_perf_id, play_killar, 'Lyssnar på killar', 2019,
    credits=[
        {'person_id': ida_kronholm, 'role': 'director'},
        {'person_id': sara_soulie, 'role': 'actor'},
        {'person_id': pelle_heikkila, 'role': 'actor'},
    ],
    duration=6300  # 105 min
)
next_perf_id += 1

create_episode(
    'YLE_KILLAR_1',
    'Lyssnar på killar - ett hörspel om bortslösade timmar',
    perf_killar,
    year=2019,
    duration=6300,
    nrk_url='https://arenan.yle.fi/1-50111414'
)

# ----------------------------------------------------------------------------
# 3. VAR DET EN HUND? (2017)
# ----------------------------------------------------------------------------
kristofer_moller = create_person('Kristofer Möller', nationality='Finnish-Swedish',
                                  bio='Finlandssvensk dramatiker och skådespelare.')
camilla_thelestam = create_person('Camilla Thelestam', nationality='Finnish-Swedish',
                                   bio='Finlandssvensk regissör vid Svenska Yle.')
cecilia_paul = create_person('Cecilia Paul', nationality='Finnish-Swedish',
                              bio='Finlandssvensk skådespelare.')
pekka_strang = create_person('Pekka Strang', nationality='Finnish',
                              bio='Finsk skådespelare, känd från filmer som Tom of Finland.')

play_hund = create_play(
    next_play_id,
    'Var det en hund?',
    playwright_id=kristofer_moller,
    year_written=2017,
    synopsis='Ett hörspel av Kristofer Möller producerat av Svenska Yle.'
)
next_play_id += 1

perf_hund = create_performance(
    next_perf_id, play_hund, 'Var det en hund?', 2017,
    credits=[
        {'person_id': camilla_thelestam, 'role': 'director'},
        {'person_id': cecilia_paul, 'role': 'actor'},
        {'person_id': pekka_strang, 'role': 'actor'},
        {'person_id': kristofer_moller, 'role': 'actor'},
    ],
    duration=1894  # 31:34
)
next_perf_id += 1

create_episode(
    'YLE_HUND_1',
    'Var det en hund?',
    perf_hund,
    year=2017,
    duration=1894,
    nrk_url='https://arenan.yle.fi/poddar/1-4265783'
)

# ----------------------------------------------------------------------------
# 4. EXIT POE (2009) - Edgar Allan Poe's last days
# ----------------------------------------------------------------------------
petri_salin = create_person('Petri Salin', nationality='Finnish',
                             bio='Finsk dramatiker, vinnare av Nordiska radioteaterpriset 2000 för "Inbjudan till resa".')
solveig_mattsson = create_person('Solveig Mattsson', nationality='Finnish-Swedish',
                                  bio='Finlandssvensk regissör.')
marcus_groth = create_person('Marcus Groth', nationality='Finnish-Swedish',
                              bio='Finlandssvensk skådespelare.')

play_poe = create_play(
    next_play_id,
    'Exit Poe',
    playwright_id=petri_salin,
    year_written=2009,
    synopsis='Ett hörspel om Edgar Allan Poes sista dagar, lika fulla av mystik som hans egna skräckhistorier.'
)
next_play_id += 1

perf_poe = create_performance(
    next_perf_id, play_poe, 'Exit Poe', 2009,
    credits=[
        {'person_id': solveig_mattsson, 'role': 'director'},
        {'person_id': pekka_strang, 'role': 'actor'},
        {'person_id': marcus_groth, 'role': 'actor'},
    ],
    duration=2477  # 41:17
)
next_perf_id += 1

create_episode(
    'YLE_POE_1',
    'Exit Poe',
    perf_poe,
    year=2009,
    duration=2477,
    nrk_url='https://arenan.yle.fi/poddar/1-4267315'
)

# ----------------------------------------------------------------------------
# 5. TRE VITA SKJORTOR (1960) - Walentin Chorell classic
# ----------------------------------------------------------------------------
walentin_chorell = create_person('Walentin Chorell', birth_year=1912,
                                  nationality='Finnish-Swedish',
                                  bio='Finlandssvensk författare och dramatiker (1912-1983), känd för sina arbetarskildringar.',
                                  wikipedia_url='https://sv.wikipedia.org/wiki/Walentin_Chorell')
ralf_langbacka = create_person('Ralf Långbacka', birth_year=1932,
                                nationality='Finnish-Swedish',
                                bio='Finlandssvensk teaterregissör (1932-2023), en av Nordens mest framstående teaterregissörer.',
                                wikipedia_url='https://sv.wikipedia.org/wiki/Ralf_Långbacka')

play_skjortor = create_play(
    next_play_id,
    'Tre vita skjortor',
    playwright_id=walentin_chorell,
    year_written=1960,
    synopsis='Ett hörspel som skildrar en arbetarfamilj och temat klassresan som modern i familjen drömmer om.'
)
next_play_id += 1

perf_skjortor = create_performance(
    next_perf_id, play_skjortor, 'Tre vita skjortor', 1960,
    credits=[
        {'person_id': ralf_langbacka, 'role': 'director'},
    ],
    duration=3000  # ~50 min estimated
)
next_perf_id += 1

create_episode(
    'YLE_SKJORTOR_1',
    'Tre vita skjortor',
    perf_skjortor,
    year=1960,
    duration=3000,
    description='Chorells klassiska hörspel om en arbetarfamilj. Nyutsändning 2012 i samband med Chorells 100-årsjubileum.',
    nrk_url='https://arenan.yle.fi/poddar/1-1564453'
)

# ----------------------------------------------------------------------------
# 6. NÄR BAROMETERN STOD PÅ KARL ÖBERG (1972) - Ulla-Lena Lundberg
# ----------------------------------------------------------------------------
ulla_lena_lundberg = create_person('Ulla-Lena Lundberg', birth_year=1947,
                                    nationality='Finnish-Swedish',
                                    bio='Finlandssvensk författare (f. 1947), vinnare av Nordiska rådets litteraturpris 2012.',
                                    wikipedia_url='https://sv.wikipedia.org/wiki/Ulla-Lena_Lundberg')

play_barometern = create_play(
    next_play_id,
    'När barometern stod på Karl Öberg',
    playwright_id=ulla_lena_lundberg,
    year_written=1972,
    synopsis='Ett hörspel till minne av sex män och deras värld: Carl Isidorus, Erik Arthur, Algot Leonard, Gustaf Richard, August Mauriz.'
)
next_play_id += 1

perf_barometern = create_performance(
    next_perf_id, play_barometern, 'När barometern stod på Karl Öberg', 1972,
    duration=3000  # 50 min
)
next_perf_id += 1

create_episode(
    'YLE_BAROMETERN_1',
    'När barometern stod på Karl Öberg',
    perf_barometern,
    year=1972,
    duration=3000,
    nrk_url='https://arenan.yle.fi/poddar/1-1786066'
)

# ----------------------------------------------------------------------------
# 7. NILS HOLGERSSONS UNDERBARA RESA (2020) - Selma Lagerlöf
# ----------------------------------------------------------------------------
# Selma Lagerlöf already exists as person 4752

mika_fagerudd = create_person('Mika Fagerudd', nationality='Finnish-Swedish',
                               bio='Finlandssvensk regissör och skådespelare, grundare av Teater Fabel.')

play_nils = create_play(
    next_play_id,
    'Nils Holgerssons underbara resa genom Sverige',
    playwright_id=4752,  # Selma Lagerlöf
    year_written=1906,
    synopsis='Selma Lagerlöfs klassiska berättelse om pojken Nils som förvandlas till en pyssling och reser genom Sverige på ryggen av en tam gås. Radioteaterpjäs med nykomponerad musik för barn.',
    work_type='barneteater'
)
next_play_id += 1

perf_nils = create_performance(
    next_perf_id, play_nils, 'Nils Holgerssons underbara resa genom Sverige', 2020,
    credits=[
        {'person_id': mika_fagerudd, 'role': 'director'},
    ],
    duration=9000  # 17 episodes x ~9 min each
)
next_perf_id += 1

# Episodes for Nils Holgersson (17 episodes found)
nils_episodes = [
    (1, 'Pojken', 'Nils blir förvandlad till pyssling'),
    (2, 'Vildgässen', 'Nils möter vildgässen'),
    (3, 'Akka från Kebnekajse', 'Nils möter gässens ledare'),
    (4, 'Vit gåskarl', 'Mårten gåskarl'),
    (5, 'Glimmingehus', 'Äventyret på Glimmingehus'),
    (6, 'Storken', 'Storkens berättelse'),
    (7, 'Stormarna', 'Stormar över Sverige'),
    (8, 'Råttornas krig', 'Gråråttorna försöker ta över'),
    (9, 'Skogen', 'I den stora skogen'),
    (10, 'Korpen', 'Mötet med korpen'),
    (11, 'Rävleken', 'Räven och hans lekar'),
    (12, 'Sjöfåglar', 'Bland sjöfåglar'),
    (13, 'Hunden', 'Mötet med hunden'),
    (14, 'Karr', 'Berättelsen om Karr'),
    (15, 'Kolmården', 'Äventyret i Kolmården'),
    (16, 'Lappland', 'Resan till Lappland'),
    (17, 'Skansen', 'Hemkomsten till Skansen'),
]

for ep_num, ep_title, ep_desc in nils_episodes:
    create_episode(
        f'YLE_NILS_{ep_num:02d}',
        f'Nils Holgerssons underbara resa - Avsnitt {ep_num}: {ep_title}',
        perf_nils,
        year=2020,
        duration=540,  # ~9 min per episode
        description=ep_desc,
        episode_number=ep_num,
        nrk_url='https://arenan.yle.fi/audio/1-50681307'
    )

# ----------------------------------------------------------------------------
# 8. AWARD-WINNING CLASSICS
# ----------------------------------------------------------------------------

# Fjädern (1990) - Prix Italia winner
erik_ohls = create_person('Erik Ohls', nationality='Finnish-Swedish',
                           bio='Finlandssvensk dramatiker och författare. Vinnare av Prix Italia 1990 för hörspelet "Fjädern".')

play_fjadern = create_play(
    next_play_id,
    'Fjädern',
    playwright_id=erik_ohls,
    year_written=1990,
    synopsis='Ett stilfullt och intellektuellt hörspel som vann Prix Italia 1990.'
)
next_play_id += 1

perf_fjadern = create_performance(
    next_perf_id, play_fjadern, 'Fjädern', 1990,
    duration=3600
)
next_perf_id += 1

create_episode(
    'YLE_FJADERN_1',
    'Fjädern',
    perf_fjadern,
    year=1990,
    duration=3600,
    description='Prix Italia 1990 - Ett stilfullt och intellektuellt hörspel.'
)

# När göken gol vid Seine (1993) - Prix Futura winner
janina_jansson = create_person('Janina Jansson', nationality='Finnish-Swedish',
                                bio='Finlandssvensk dramatiker. Vinnare av Prix Futura 1993.')

play_goken = create_play(
    next_play_id,
    'När göken gol vid Seine',
    playwright_id=janina_jansson,
    year_written=1993,
    synopsis='En förtjusande berättelse om en finsk man, med många gamla finska schlagers. Drömlika känsloväxlingar genom historien. Vinnare av Prix Futura 1993.'
)
next_play_id += 1

perf_goken = create_performance(
    next_perf_id, play_goken, 'När göken gol vid Seine', 1993,
    duration=3600
)
next_perf_id += 1

create_episode(
    'YLE_GOKEN_1',
    'När göken gol vid Seine',
    perf_goken,
    year=1993,
    duration=3600,
    description='Prix Futura 1993 - En berättelse om en finsk man med gamla finska schlagers.'
)

# Inbjudan till resa (1998) - Nordic Radio Play Prize 2000
play_inbjudan = create_play(
    next_play_id,
    'Inbjudan till resa',
    playwright_id=petri_salin,  # Already created
    year_written=1998,
    synopsis='En mörk dystopisk berättelse om samhällskontroll och ojämlikhet. Ros och Simon försöker ta sig in i en muromgärdad stad. Vinnare av Nordiska radioteaterpriset 2000.'
)
next_play_id += 1

perf_inbjudan = create_performance(
    next_perf_id, play_inbjudan, 'Inbjudan till resa', 1998,
    credits=[
        {'person_id': petri_salin, 'role': 'director'},
    ],
    duration=3600
)
next_perf_id += 1

create_episode(
    'YLE_INBJUDAN_1',
    'Inbjudan till resa',
    perf_inbjudan,
    year=1998,
    duration=3600,
    description='Nordiska radioteaterpriset 2000 - Dystopisk berättelse om samhällskontroll.'
)

# ----------------------------------------------------------------------------
# 9. ETT STEG UTANFÖR (2012) - Jarno Kuosa
# ----------------------------------------------------------------------------
jarno_kuosa = create_person('Jarno Kuosa', nationality='Finnish',
                             bio='Finsk dramatiker och regissör.')

play_steg = create_play(
    next_play_id,
    'Ett steg utanför',
    playwright_id=jarno_kuosa,
    year_written=2012,
    synopsis='Ett svenskspråkigt radiodrama producerat av Svenska Yle.'
)
next_play_id += 1

perf_steg = create_performance(
    next_perf_id, play_steg, 'Ett steg utanför', 2012,
    credits=[
        {'person_id': jarno_kuosa, 'role': 'director'},
    ],
    duration=3000  # 50 min
)
next_perf_id += 1

create_episode(
    'YLE_STEG_1',
    'Ett steg utanför',
    perf_steg,
    year=2012,
    duration=3000,
    nrk_url='https://arenan.yle.fi/audio/1-1817844'
)

# ----------------------------------------------------------------------------
# Summary
# ----------------------------------------------------------------------------
print(f"\n=== Import Complete ===")
print(f"Created {next_person_id - 4758} persons")
print(f"Created {next_play_id - 3433} plays/works")
print(f"Created {next_perf_id - 3294} performances")
print(f"Created 28 episodes")
print(f"\nRun: python3 scripts/validate_data.py")
print(f"Then: python3 scripts/build_database.py")
