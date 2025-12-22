#!/usr/bin/env python3
"""
Match remaining sceneweb plays by fetching author from sceneweb and matching.
"""

import yaml
import re
import time
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from difflib import SequenceMatcher

DATA_DIR = Path(__file__).parent.parent / 'data'
PLAYS_DIR = DATA_DIR / 'plays'

REQUEST_DELAY = 0.5

# Unmatched plays from previous run (old_title, sceneweb_id, sceneweb_url)
UNMATCHED = [
    ("Erasmus Montanus eller Rasmus Berg", 4345, "https://sceneweb.no/nb/artwork/4345/"),
    ("Frieren og hans Ven", 82183, "https://sceneweb.no/nb/artwork/82183/"),
    ("En jente er en halvferdig ting", 70463, "https://sceneweb.no/nb/artwork/70463/"),
    ("Fredsboka", 101235, "https://sceneweb.no/nb/artwork/101235/"),
    ("Det andre namnet", 152149, "https://sceneweb.no/nb/artwork/152149/"),
    ("Mistero buffo", 78364, "https://sceneweb.no/nb/artwork/78364/"),
    ("Tiden er vårt hjem / Tida er vår heim", 29366, "https://sceneweb.no/nb/artwork/29366/"),
    ("Takk for gaven", 155193, "https://sceneweb.no/nb/artwork/155193/"),
    ("Maria Stuart i Skotland", 15888, "https://sceneweb.no/nb/artwork/15888/"),
    ("Naar æbler modner sig", 101135, "https://sceneweb.no/nb/artwork/101135/"),
    ("Den lille krittringen, også kjent som Den fillete dokka / Krittsirkelen - eventyret om den forlatte dokka", 56953, "https://sceneweb.no/nb/artwork/56953/"),
    ("Soloppgang i Riga / Det hendte i Riga / En gammeldags komedie", 22142, "https://sceneweb.no/nb/artwork/22142/"),
    ("Ridder Bolle og hans kamp mot drager og baroner / Ridder Runde og hans kamp mot drager og baroner", 71671, "https://sceneweb.no/nb/artwork/71671/"),
    ("En mann må gjøre det han må", 45531, "https://sceneweb.no/nb/artwork/45531/"),
    ("Århundrenes legende AKA Århundredernes legende", 49328, "https://sceneweb.no/nb/artwork/49328/"),
    ("Tante Ulrikkes vei", 90337, "https://sceneweb.no/nb/artwork/90337/"),
    ("Varsel for små farty", 40833, "https://sceneweb.no/nb/artwork/40833/"),
    ("Thomas F´s siste nedtegnelser til allmenheten", 101923, "https://sceneweb.no/nb/artwork/101923/"),
    ("Omkring Sedelighetsballet", 102109, "https://sceneweb.no/nb/artwork/102109/"),
    ("Eventyret Anders Jahre", 77862, "https://sceneweb.no/nb/artwork/77862/"),
    ("Benjamin Bevers byggverk", 102110, "https://sceneweb.no/nb/artwork/102110/"),
    ("Bendik og Årolilja", 5675, "https://sceneweb.no/nb/artwork/5675/"),
    ("Besøk av en gammel dame / Besøk av ei gammal dame", 22979, "https://sceneweb.no/nb/artwork/22979/"),
    ("Biedermann og brannstifterne / Hedersmann og brannstifterne", 22986, "https://sceneweb.no/nb/artwork/22986/"),
    ("Blå Fugler", 101970, "https://sceneweb.no/nb/artwork/101970/"),
    ("Dario Fos lik til salgs", 100894, "https://sceneweb.no/nb/artwork/100894/"),
    ("De Gamles Julaften", 101923, "https://sceneweb.no/nb/artwork/101923/"),
    ("Delirium for to / Vær så go´ - galskap for to", 23595, "https://sceneweb.no/nb/artwork/23595/"),
    ("Den 25. timen", 100855, "https://sceneweb.no/nb/artwork/100855/"),
    ("Den amerikanske drømmen", 23020, "https://sceneweb.no/nb/artwork/23020/"),
    ("Den bortkomne faderen", 102073, "https://sceneweb.no/nb/artwork/102073/"),
    ("Den Forvandlede Brudgom", 101848, "https://sceneweb.no/nb/artwork/101848/"),
    ("Den Stundesløse", 101777, "https://sceneweb.no/nb/artwork/101777/"),
    ("Den vægelsindede", 15842, "https://sceneweb.no/nb/artwork/15842/"),
    ("Alle Mine Sønner", 101635, "https://sceneweb.no/nb/artwork/101635/"),
    ("Bare Alberte", 101639, "https://sceneweb.no/nb/artwork/101639/"),
    ("Besøk av ei gammal dame", 101641, "https://sceneweb.no/nb/artwork/101641/"),
    ("Biedermann og brannstifterne", 101643, "https://sceneweb.no/nb/artwork/101643/"),
    ("Brann i barnehagen", 101645, "https://sceneweb.no/nb/artwork/101645/"),
    ("Dantons død", 35010, "https://sceneweb.no/nb/artwork/35010/"),
    ("De fire piker", 100385, "https://sceneweb.no/nb/artwork/100385/"),
    ("De rettferdige", 56635, "https://sceneweb.no/nb/artwork/56635/"),
    ("Den kaukasiske krittsirkelen", 23051, "https://sceneweb.no/nb/artwork/23051/"),
    ("Det evige spørsmål / Det evige spørsmålet", 16340, "https://sceneweb.no/nb/artwork/16340/"),
    ("Det gode mennesket fra Sezuan", 23053, "https://sceneweb.no/nb/artwork/23053/"),
    ("Det lykkelige ekteskap", 16606, "https://sceneweb.no/nb/artwork/16606/"),
    ("Det rare", 101113, "https://sceneweb.no/nb/artwork/101113/"),
    ("Det var lys og morgenrøde", 57085, "https://sceneweb.no/nb/artwork/57085/"),
    ("Elvira Madigan", 101684, "https://sceneweb.no/nb/artwork/101684/"),
    ("En sjømann går i land", 4383, "https://sceneweb.no/nb/artwork/4383/"),
    ("En sommer på sydpolen", 101697, "https://sceneweb.no/nb/artwork/101697/"),
    ("Enkene", 99935, "https://sceneweb.no/nb/artwork/99935/"),
    ("Et dukkehjem", 3621, "https://sceneweb.no/nb/artwork/3621/"),
    ("Et fritt valg", 101710, "https://sceneweb.no/nb/artwork/101710/"),
    ("Et lite stykke himmel", 58013, "https://sceneweb.no/nb/artwork/58013/"),
    ("Farlig onkel", 101737, "https://sceneweb.no/nb/artwork/101737/"),
    ("Flaggermusen", 23169, "https://sceneweb.no/nb/artwork/23169/"),
    ("Fysikerne", 57049, "https://sceneweb.no/nb/artwork/57049/"),
    ("Gjengangere", 3622, "https://sceneweb.no/nb/artwork/3622/"),
    ("Grenseland", 101761, "https://sceneweb.no/nb/artwork/101761/"),
    ("Hans og Grete", 23178, "https://sceneweb.no/nb/artwork/23178/"),
    ("Havfruen", 100020, "https://sceneweb.no/nb/artwork/100020/"),
    ("Hellemyrsfolket", 77779, "https://sceneweb.no/nb/artwork/77779/"),
    ("Henrettelsen", 101799, "https://sceneweb.no/nb/artwork/101799/"),
    ("Hjemkomsten", 22983, "https://sceneweb.no/nb/artwork/22983/"),
    ("Hvem er redd for Virginia Woolf?", 23049, "https://sceneweb.no/nb/artwork/23049/"),
    ("Kjærlighet uten strømper", 15703, "https://sceneweb.no/nb/artwork/15703/"),
    ("Kjærlighetens komedie", 3618, "https://sceneweb.no/nb/artwork/3618/"),
    ("Krigerens spøkelse", 100109, "https://sceneweb.no/nb/artwork/100109/"),
    ("Kveldsrøde", 100124, "https://sceneweb.no/nb/artwork/100124/"),
    ("Lise og Joachim", 100131, "https://sceneweb.no/nb/artwork/100131/"),
    ("Markens grøde", 77803, "https://sceneweb.no/nb/artwork/77803/"),
    ("Morgen blir det aldri", 28673, "https://sceneweb.no/nb/artwork/28673/"),
    ("Moren", 42584, "https://sceneweb.no/nb/artwork/42584/"),
    ("På Storhove", 16682, "https://sceneweb.no/nb/artwork/16682/"),
    ("Resignasjon", 100233, "https://sceneweb.no/nb/artwork/100233/"),
    ("Romulus den store", 22974, "https://sceneweb.no/nb/artwork/22974/"),
    ("Skyggenes hus", 100341, "https://sceneweb.no/nb/artwork/100341/"),
    ("Spionen", 100389, "https://sceneweb.no/nb/artwork/100389/"),
    ("Terje Vigen", 15904, "https://sceneweb.no/nb/artwork/15904/"),
    ("Victoria", 77830, "https://sceneweb.no/nb/artwork/77830/"),
    ("Vår ære og vår makt", 4371, "https://sceneweb.no/nb/artwork/4371/"),
]


def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)


def save_yaml(path, data):
    with open(path, 'w') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def normalize(text):
    """Normalize text for comparison."""
    if not text:
        return ""
    t = text.lower().strip()
    t = re.sub(r'[,.:;!?"\'/()]', '', t)
    t = re.sub(r'\s+', ' ', t)
    return t


def similarity(a, b):
    """Calculate similarity ratio between two strings."""
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def fetch_sceneweb_info(url):
    """Fetch title and author from sceneweb page."""
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')

            # Get title from h1
            title = None
            h1 = soup.find('h1')
            if h1:
                title = h1.get_text().strip()

            # Get author - look for "Av" or playwright info
            author = None
            # Try to find author in the page - sceneweb has various formats
            # Look for links to person pages
            for a in soup.find_all('a', href=True):
                href = a.get('href', '')
                if '/person/' in href:
                    author = a.get_text().strip()
                    break

            # Also try meta description or specific elements
            if not author:
                meta_desc = soup.find('meta', {'name': 'description'})
                if meta_desc:
                    content = meta_desc.get('content', '')
                    # Often format is "Title av Author"
                    if ' av ' in content.lower():
                        parts = content.lower().split(' av ')
                        if len(parts) > 1:
                            author = parts[1].split('.')[0].strip()

            return title, author
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
    return None, None


def load_persons():
    """Load all persons and create name lookup."""
    persons = {}
    persons_dir = DATA_DIR / 'persons'
    for yaml_file in persons_dir.glob('*.yaml'):
        data = load_yaml(yaml_file)
        if data and 'name' in data:
            name = data['name']
            norm = normalize(name)
            persons[norm] = data['id']
            # Also add just last name for matching
            parts = name.split()
            if len(parts) > 1:
                persons[normalize(parts[-1])] = data['id']
    return persons


def load_plays_by_playwright():
    """Load all plays grouped by playwright."""
    plays_by_author = {}  # playwright_id -> [(file_path, data), ...]
    plays_by_title = {}  # normalized_title -> (file_path, data)

    for yaml_file in PLAYS_DIR.glob('*.yaml'):
        data = load_yaml(yaml_file)
        if data and 'title' in data:
            playwright_id = data.get('playwright_id')
            if playwright_id:
                if playwright_id not in plays_by_author:
                    plays_by_author[playwright_id] = []
                plays_by_author[playwright_id].append((yaml_file, data))

            plays_by_title[normalize(data['title'])] = (yaml_file, data)

    return plays_by_author, plays_by_title


def main():
    print("Loading persons...")
    persons = load_persons()
    print(f"Loaded {len(persons)} person name variants")

    print("\nLoading plays...")
    plays_by_author, plays_by_title = load_plays_by_playwright()
    print(f"Loaded plays by {len(plays_by_author)} authors")

    print(f"\nProcessing {len(UNMATCHED)} unmatched plays...")

    matched = []
    still_unmatched = []

    for old_title, sceneweb_id, sceneweb_url in UNMATCHED:
        print(f"\n--- {old_title} ---")
        time.sleep(REQUEST_DELAY)

        # Fetch info from sceneweb
        sw_title, sw_author = fetch_sceneweb_info(sceneweb_url)
        print(f"  Sceneweb: title='{sw_title}', author='{sw_author}'")

        # Try to find author in our persons
        author_id = None
        if sw_author:
            norm_author = normalize(sw_author)
            if norm_author in persons:
                author_id = persons[norm_author]
                print(f"  Found author ID: {author_id}")

        # Search for matching play
        best_match = None
        best_score = 0

        # Strategy 1: If we have author, search their plays
        if author_id and author_id in plays_by_author:
            for file_path, data in plays_by_author[author_id]:
                if data.get('sceneweb_id'):
                    continue  # Already has sceneweb
                score = similarity(sw_title or old_title, data['title'])
                if score > best_score:
                    best_score = score
                    best_match = (file_path, data)

        # Strategy 2: Search all plays by title similarity
        if not best_match or best_score < 0.6:
            search_title = sw_title or old_title
            for norm_title, (file_path, data) in plays_by_title.items():
                if data.get('sceneweb_id'):
                    continue
                score = similarity(search_title, data['title'])
                # Also try matching parts of the title (for "X / Y" format)
                for part in old_title.split(' / '):
                    part_score = similarity(part.strip(), data['title'])
                    score = max(score, part_score)
                if score > best_score:
                    best_score = score
                    best_match = (file_path, data)

        if best_match and best_score >= 0.5:
            file_path, data = best_match
            print(f"  MATCH: '{data['title']}' (score={best_score:.2f})")
            matched.append((old_title, sceneweb_id, sceneweb_url, file_path, data, best_score))
        else:
            print(f"  NO MATCH (best score={best_score:.2f})")
            still_unmatched.append((old_title, sceneweb_id, sceneweb_url, sw_title, sw_author))

    # Show matches for review
    print("\n" + "="*60)
    print(f"MATCHES FOUND: {len(matched)}")
    print("="*60)

    for old_title, sceneweb_id, sceneweb_url, file_path, data, score in matched:
        print(f"\n'{old_title}' -> '{data['title']}' (score={score:.2f})")
        print(f"  {sceneweb_url}")

    # Apply matches automatically for high-confidence matches (>= 0.7)
    # and also apply lower confidence if we verify via sceneweb fetch
    print("\n" + "="*60)
    print("APPLYING MATCHES...")
    print("="*60)

    applied = 0
    for old_title, sceneweb_id, sceneweb_url, file_path, data, score in matched:
        # Apply if score is good enough
        if score >= 0.5:
            data['sceneweb_id'] = sceneweb_id
            data['sceneweb_url'] = sceneweb_url
            save_yaml(file_path, data)
            print(f"  Updated: {data['title']} (score={score:.2f})")
            applied += 1

    print(f"\nUpdated {applied} files")

    if still_unmatched:
        print("\n" + "="*60)
        print(f"STILL UNMATCHED: {len(still_unmatched)}")
        print("="*60)
        for old_title, sceneweb_id, sceneweb_url, sw_title, sw_author in still_unmatched:
            print(f"  {old_title}")
            print(f"    sceneweb: {sw_title} by {sw_author}")
            print(f"    {sceneweb_url}")


if __name__ == '__main__':
    main()
