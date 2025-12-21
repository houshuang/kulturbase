#!/usr/bin/env python3
"""
Phase 5: Link performances to existing plays in the database.

Matches classical performances (ballets, operas) to plays they're based on.
Outputs: output/classical_play_links.json
"""

import json
import re
import yaml
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher

OUTPUT_DIR = Path(__file__).parent.parent / "output"
DATA_DIR = Path(__file__).parent.parent / "data"
INPUT_FILE = OUTPUT_DIR / "classical_performances.json"
OUTPUT_FILE = OUTPUT_DIR / "classical_play_links.json"


def load_plays():
    """Load all plays from YAML files."""
    plays = {}
    plays_dir = DATA_DIR / "plays"

    if not plays_dir.exists():
        print(f"WARNING: Plays directory not found: {plays_dir}")
        return plays

    for yaml_file in plays_dir.glob("*.yaml"):
        try:
            with open(yaml_file) as f:
                play = yaml.safe_load(f)
                if play and play.get('id'):
                    plays[play['id']] = play
        except Exception as e:
            print(f"  Error loading {yaml_file}: {e}")

    return plays


def load_persons():
    """Load all persons from YAML files."""
    persons = {}
    persons_dir = DATA_DIR / "persons"

    if not persons_dir.exists():
        return persons

    for yaml_file in persons_dir.glob("*.yaml"):
        try:
            with open(yaml_file) as f:
                person = yaml.safe_load(f)
                if person and person.get('id'):
                    persons[person['id']] = person
        except:
            pass

    return persons


def normalize_title(title):
    """Normalize title for matching."""
    if not title:
        return ""

    # Lowercase
    title = title.lower()

    # Remove common suffixes/prefixes
    title = re.sub(r'\s*\(.*?\)\s*', ' ', title)  # Remove parenthetical
    title = re.sub(r'\s*-\s*.*$', '', title)  # Remove dash suffix

    # Remove articles
    title = re.sub(r'^(the|a|an|en|et|den|det|de)\s+', '', title)

    # Remove punctuation
    title = re.sub(r'[^\w\s]', '', title)
    title = re.sub(r'\s+', ' ', title).strip()

    return title


def similar(a, b):
    """Calculate similarity ratio between two strings."""
    return SequenceMatcher(None, normalize_title(a), normalize_title(b)).ratio()


# Known mappings: work titles to play titles
KNOWN_MAPPINGS = {
    # Ibsen
    "peer gynt": ["peer gynt"],
    "et dukkehjem": ["et dukkehjem", "a doll's house"],
    "gengangere": ["gengangere", "ghosts"],
    "hedda gabler": ["hedda gabler"],
    "vildanden": ["vildanden", "the wild duck"],
    "fruen fra havet": ["fruen fra havet", "the lady from the sea"],
    "rosmersholm": ["rosmersholm"],
    "bygmester solness": ["bygmester solness", "the master builder"],
    "john gabriel borkman": ["john gabriel borkman"],
    "når vi døde vågner": ["når vi døde vågner", "when we dead awaken"],
    "brand": ["brand"],
    "kejser og galilæer": ["kejser og galilæer", "emperor and galilean"],

    # Bjørnson
    "over ævne": ["over ævne"],

    # Shakespeare (Norwegian titles)
    "hamlet": ["hamlet"],
    "macbeth": ["macbeth"],
    "othello": ["othello"],
    "kong lear": ["kong lear", "king lear"],
    "romeo og julie": ["romeo og julie", "romeo and juliet"],
    "en midtsommernattsdrøm": ["en midtsommernattsdrøm", "a midsummer night's dream"],
    "stormen": ["stormen", "the tempest"],
    "kjøpmannen i venedig": ["kjøpmannen i venedig", "the merchant of venice"],

    # Chekhov
    "kirsebærhaven": ["kirsebærhaven", "the cherry orchard"],
    "måken": ["måken", "the seagull"],
    "tre søstre": ["tre søstre", "three sisters"],
    "onkel vanja": ["onkel vanja", "uncle vanya"],

    # Strindberg
    "frøken julie": ["frøken julie", "miss julie"],
    "fadren": ["fadren", "the father"],
    "dødsdansen": ["dødsdansen", "the dance of death"],
    "drømmespillet": ["drømmespillet", "a dream play"],
    "spøksonaten": ["spøksonaten", "the ghost sonata"],

    # Holberg
    "jeppe på bjerget": ["jeppe på bjerget"],
    "erasmus montanus": ["erasmus montanus"],
    "den politiske kandestøber": ["den politiske kandestøber"],
    "den stundesløse": ["den stundesløse"],
    "barselstuen": ["barselstuen"],
    "maskeraden": ["maskeraden"],
}

# Operas/ballets based on literary works
LITERARY_BASED_WORKS = {
    "carmen": "prosper mérimée",
    "la traviata": "alexandre dumas fils",
    "rigoletto": "victor hugo",
    "tosca": "victorien sardou",
    "madama butterfly": "john luther long",
    "la bohème": "henri murger",
    "otello": "william shakespeare",
    "falstaff": "william shakespeare",
    "macbeth": "william shakespeare",
    "romeo et juliette": "william shakespeare",
    "hamlet": "william shakespeare",
    "eugene onegin": "alexander pushkin",
    "boris godunov": "alexander pushkin",
    "the queen of spades": "alexander pushkin",
    "war and peace": "leo tolstoy",
    "swan lake": None,  # Not based on specific literary work
    "the nutcracker": "e.t.a. hoffmann",
    "sleeping beauty": "charles perrault",
    "giselle": None,
    "don quixote": "miguel de cervantes",
}


def find_play_matches(performance, plays, persons):
    """Find matching plays for a performance."""
    matches = []

    work_title = performance.get('work_title', '')
    based_on = performance.get('based_on_literary_work', '')
    composer = performance.get('composer', '')

    if not work_title:
        return matches

    normalized_work = normalize_title(work_title)

    # Check known mappings first
    for mapping_key, mapping_titles in KNOWN_MAPPINGS.items():
        if normalized_work == mapping_key or any(normalize_title(t) == normalized_work for t in mapping_titles):
            # Found in known mappings, search plays
            for play_id, play in plays.items():
                play_title = play.get('title', '')
                if normalize_title(play_title) in mapping_titles or mapping_key in normalize_title(play_title):
                    # Get playwright info
                    playwright_name = None
                    playwright_id = play.get('playwright_id')
                    if playwright_id and playwright_id in persons:
                        playwright_name = persons[playwright_id].get('name')

                    matches.append({
                        'play_id': play_id,
                        'play_title': play_title,
                        'playwright_id': playwright_id,
                        'playwright_name': playwright_name,
                        'match_type': 'known_mapping',
                        'confidence': 0.95,
                    })

    # Check based_on_literary_work
    if based_on and not matches:
        based_on_lower = based_on.lower()
        for play_id, play in plays.items():
            play_title = play.get('title', '')
            playwright_id = play.get('playwright_id')
            playwright_name = persons.get(playwright_id, {}).get('name', '') if playwright_id else ''

            # Check if author/playwright name appears in based_on
            if playwright_name and playwright_name.lower() in based_on_lower:
                similarity = similar(play_title, work_title)
                if similarity > 0.5:
                    matches.append({
                        'play_id': play_id,
                        'play_title': play_title,
                        'playwright_id': playwright_id,
                        'playwright_name': playwright_name,
                        'match_type': 'based_on_author',
                        'confidence': 0.7 + (similarity * 0.2),
                    })

    # Fuzzy title matching
    if not matches:
        for play_id, play in plays.items():
            play_title = play.get('title', '')
            similarity = similar(play_title, work_title)

            if similarity > 0.85:
                playwright_id = play.get('playwright_id')
                playwright_name = persons.get(playwright_id, {}).get('name') if playwright_id else None

                matches.append({
                    'play_id': play_id,
                    'play_title': play_title,
                    'playwright_id': playwright_id,
                    'playwright_name': playwright_name,
                    'match_type': 'fuzzy_title',
                    'confidence': similarity,
                })

    # Sort by confidence
    matches.sort(key=lambda x: -x.get('confidence', 0))

    return matches


def main():
    print("=" * 60)
    print("Phase 5: Linking Performances to Plays")
    print("=" * 60)

    # Load performances
    if not INPUT_FILE.exists():
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        print("Please run link_multipart.py first.")
        return

    with open(INPUT_FILE) as f:
        data = json.load(f)

    performances = data.get('performances', [])
    print(f"Found {len(performances)} performances")

    # Load plays and persons
    plays = load_plays()
    persons = load_persons()
    print(f"Loaded {len(plays)} plays and {len(persons)} persons")

    # Find links
    linked_performances = []
    unlinked_performances = []
    total_links = 0

    for perf in performances:
        matches = find_play_matches(perf, plays, persons)

        if matches:
            linked_performances.append({
                **perf,
                'play_links': matches,
            })
            total_links += len(matches)
        else:
            unlinked_performances.append(perf)

    # Deduplicate links by play_id
    unique_play_ids = set()
    for perf in linked_performances:
        for link in perf.get('play_links', []):
            unique_play_ids.add(link.get('play_id'))

    # Output
    output_data = {
        'linked_at': datetime.now().isoformat(),
        'statistics': {
            'total_performances': len(performances),
            'linked_performances': len(linked_performances),
            'unlinked_performances': len(unlinked_performances),
            'total_links': total_links,
            'unique_plays_linked': len(unique_play_ids),
        },
        'linked_performances': linked_performances,
        'unlinked_performances': unlinked_performances,
    }

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("LINKING COMPLETE")
    print("=" * 60)
    print(f"Total performances: {len(performances)}")
    print(f"Linked to plays: {len(linked_performances)}")
    print(f"Unlinked: {len(unlinked_performances)}")
    print(f"Unique plays linked: {len(unique_play_ids)}")
    print(f"\nOutput written to: {OUTPUT_FILE}")

    # Show some links
    if linked_performances:
        print("\n--- Sample Play Links ---")
        for perf in linked_performances[:10]:
            print(f"  {perf.get('work_title')} ({perf.get('genre')})")
            for link in perf.get('play_links', [])[:2]:
                print(f"    -> Play #{link.get('play_id')}: {link.get('play_title')}")
                print(f"       By: {link.get('playwright_name')}")
                print(f"       Match: {link.get('match_type')} ({link.get('confidence'):.2f})")


if __name__ == "__main__":
    main()
