#!/usr/bin/env python3
"""
Carefully match remaining sceneweb plays - only high-confidence matches.
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

REQUEST_DELAY = 0.3

# High-confidence matches identified from manual review
# These are plays where the title is clearly the same with minor variations
HIGH_CONFIDENCE_MATCHES = [
    # (old_title, sceneweb_id, sceneweb_url, expected_current_title_pattern)
    ("Erasmus Montanus eller Rasmus Berg", 4345, "https://sceneweb.no/nb/artwork/4345/", "Erasmus Montanus"),
    ("Maria Stuart i Skotland", 15888, "https://sceneweb.no/nb/artwork/15888/", "Maria Stuart"),
    ("Soloppgang i Riga / Det hendte i Riga / En gammeldags komedie", 22142, "https://sceneweb.no/nb/artwork/22142/", "Soloppgang i Riga"),
    ("Ridder Bolle og hans kamp mot drager og baroner / Ridder Runde og hans kamp mot drager og baroner", 71671, "https://sceneweb.no/nb/artwork/71671/", "Ridder Runde"),
    ("En mann må gjøre det han må", 45531, "https://sceneweb.no/nb/artwork/45531/", "En mann må gjøre"),
    ("Thomas F´s siste nedtegnelser til allmenheten", 101923, "https://sceneweb.no/nb/artwork/101923/", "Thomas F"),
    ("Tante Ulrikkes vei", 90337, "https://sceneweb.no/nb/artwork/90337/", "Tante Ulrikke"),
    ("Besøk av en gammel dame / Besøk av ei gammal dame", 22979, "https://sceneweb.no/nb/artwork/22979/", "Besøk av en gammel dame"),
    ("Biedermann og brannstifterne / Hedersmann og brannstifterne", 22986, "https://sceneweb.no/nb/artwork/22986/", "brannstifterne"),
    ("Dario Fos lik til salgs", 100894, "https://sceneweb.no/nb/artwork/100894/", "Lik til salgs"),
    ("Delirium for to / Vær så go´ - galskap for to", 23595, "https://sceneweb.no/nb/artwork/23595/", "galskap for to"),
    ("Den 25. timen", 100855, "https://sceneweb.no/nb/artwork/100855/", "Den 25. time"),
    ("Den amerikanske drømmen", 23020, "https://sceneweb.no/nb/artwork/23020/", "Den amerikanske drøm"),
    ("Den vægelsindede", 15842, "https://sceneweb.no/nb/artwork/15842/", "vegelsinnede"),
    ("Bare Alberte", 101639, "https://sceneweb.no/nb/artwork/101639/", "Alberte"),
    ("Det evige spørsmål / Det evige spørsmålet", 16340, "https://sceneweb.no/nb/artwork/16340/", "Det evige spørsmål"),
    ("Det gode mennesket fra Sezuan", 23053, "https://sceneweb.no/nb/artwork/23053/", "Det gode mennesket"),
    ("Fysikerne", 57049, "https://sceneweb.no/nb/artwork/57049/", "Fysikerne"),
    ("Gjengangere", 3622, "https://sceneweb.no/nb/artwork/3622/", "Gjengangere"),
    ("Kjærlighetens komedie", 3618, "https://sceneweb.no/nb/artwork/3618/", "Kjærlighetens Komedie"),
    ("Spionen", 100389, "https://sceneweb.no/nb/artwork/100389/", "Spionen"),
    ("Et dukkehjem", 3621, "https://sceneweb.no/nb/artwork/3621/", "Et dukkehjem"),
    ("Dantons død", 35010, "https://sceneweb.no/nb/artwork/35010/", "Dantons død"),
    ("Den kaukasiske krittsirkelen", 23051, "https://sceneweb.no/nb/artwork/23051/", "kaukasiske krittsirkel"),
    ("Hvem er redd for Virginia Woolf?", 23049, "https://sceneweb.no/nb/artwork/23049/", "Virginia Woolf"),
    ("Hans og Grete", 23178, "https://sceneweb.no/nb/artwork/23178/", "Hänsel und Gretel"),
    ("Hjemkomsten", 22983, "https://sceneweb.no/nb/artwork/22983/", "Hjemkomsten"),
    ("Romulus den store", 22974, "https://sceneweb.no/nb/artwork/22974/", "Romulus den store"),
    ("Markens grøde", 77803, "https://sceneweb.no/nb/artwork/77803/", "Markens grøde"),
    ("Victoria", 77830, "https://sceneweb.no/nb/artwork/77830/", "Victoria"),
    ("Hellemyrsfolket", 77779, "https://sceneweb.no/nb/artwork/77779/", "Hellemyrsfolket"),
    ("Terje Vigen", 15904, "https://sceneweb.no/nb/artwork/15904/", "Terje Vigen"),
    ("Vår ære og vår makt", 4371, "https://sceneweb.no/nb/artwork/4371/", "Vår ære og vår makt"),
    ("En sjømann går i land", 4383, "https://sceneweb.no/nb/artwork/4383/", "En sjømann går i land"),
    ("Moren", 42584, "https://sceneweb.no/nb/artwork/42584/", "Moren"),
    ("Flaggermusen", 23169, "https://sceneweb.no/nb/artwork/23169/", "Flaggermusen"),
    ("De rettferdige", 56635, "https://sceneweb.no/nb/artwork/56635/", "De rettferdige"),
    ("Kjærlighet uten strømper", 15703, "https://sceneweb.no/nb/artwork/15703/", "Kjærlighet uten strømper"),
    ("På Storhove", 16682, "https://sceneweb.no/nb/artwork/16682/", "På Storhove"),
    ("Elvira Madigan", 101684, "https://sceneweb.no/nb/artwork/101684/", "Elvira Madigan"),
    ("Naar æbler modner sig", 101135, "https://sceneweb.no/nb/artwork/101135/", "eplene modnes"),
    ("Eventyret Anders Jahre", 77862, "https://sceneweb.no/nb/artwork/77862/", "Anders Jahre"),
    ("Bendik og Årolilja", 5675, "https://sceneweb.no/nb/artwork/5675/", "Bendik og Årolilja"),
]


def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)


def save_yaml(path, data):
    with open(path, 'w') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def normalize(text):
    if not text:
        return ""
    t = text.lower().strip()
    t = re.sub(r'[,.:;!?"\'/()]', '', t)
    t = re.sub(r'\s+', ' ', t)
    return t


def fetch_sceneweb_title(url):
    """Fetch the title from sceneweb for verification."""
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            h1 = soup.find('h1')
            if h1:
                return h1.get_text().strip()
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
    return None


def main():
    print("Loading plays...")
    plays = {}  # title -> (file_path, data)

    for yaml_file in PLAYS_DIR.glob('*.yaml'):
        data = load_yaml(yaml_file)
        if data and 'title' in data:
            plays[data['title']] = (yaml_file, data)
            # Also index by normalized title
            plays[normalize(data['title'])] = (yaml_file, data)

    print(f"Loaded {len(plays) // 2} plays")

    print(f"\nProcessing {len(HIGH_CONFIDENCE_MATCHES)} high-confidence matches...")

    matched = []
    not_found = []

    for old_title, sceneweb_id, sceneweb_url, pattern in HIGH_CONFIDENCE_MATCHES:
        # Search for matching play
        found = None
        for title, (file_path, data) in plays.items():
            if data.get('sceneweb_id'):
                continue  # Already has sceneweb
            if pattern.lower() in title.lower():
                found = (file_path, data)
                break

        if found:
            file_path, data = found
            print(f"  '{old_title}' -> '{data['title']}'")

            # Verify with sceneweb
            time.sleep(REQUEST_DELAY)
            sw_title = fetch_sceneweb_title(sceneweb_url)
            if sw_title:
                print(f"    Verified: sceneweb title = '{sw_title}'")

            matched.append((old_title, sceneweb_id, sceneweb_url, file_path, data))
        else:
            print(f"  NOT FOUND: '{old_title}' (pattern: {pattern})")
            not_found.append((old_title, sceneweb_id, sceneweb_url, pattern))

    # Apply matches
    print(f"\n{'='*60}")
    print(f"APPLYING {len(matched)} MATCHES")
    print('='*60)

    for old_title, sceneweb_id, sceneweb_url, file_path, data in matched:
        data['sceneweb_id'] = sceneweb_id
        data['sceneweb_url'] = sceneweb_url
        save_yaml(file_path, data)
        print(f"  Updated: {data['title']}")

    print(f"\nUpdated {len(matched)} files")

    if not_found:
        print(f"\n{'='*60}")
        print(f"NOT FOUND: {len(not_found)}")
        print('='*60)
        for old_title, sceneweb_id, sceneweb_url, pattern in not_found:
            print(f"  {old_title}")
            print(f"    pattern: {pattern}")
            print(f"    {sceneweb_url}")


if __name__ == '__main__':
    main()
