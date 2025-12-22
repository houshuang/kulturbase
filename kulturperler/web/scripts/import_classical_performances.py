#!/usr/bin/env python3
"""
Import 442 NRK classical performances from classified JSON into YAML files.

Creates:
- data/persons/{id}.yaml for composers
- data/plays/{id}.yaml for works (operas, ballets, symphonies, etc.)
- data/performances/{id}.yaml for recordings
- data/episodes/{prf_id}.yaml for individual files

YAML files are the source of truth. Run build_database.py after to compile SQLite.
"""

import json
import yaml
import re
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).parent.parent / "data"
JSON_PATH = Path(__file__).parent.parent / "output" / "classical_classified.json"

# Genre to work_type mapping
GENRE_TO_WORK_TYPE = {
    'ballet': 'ballet',
    'opera': 'opera',
    'operetta': 'operetta',
    'symphony': 'symphony',
    'concerto': 'concerto',
    'orchestral': 'orchestral',
    'chamber': 'chamber',
    'choral': 'choral',
    'other_classical': 'orchestral',
    'mixed': 'orchestral',
}

# Genre to category mapping for UI grouping
GENRE_TO_CATEGORY = {
    'ballet': 'opera',
    'opera': 'opera',
    'operetta': 'opera',
    'symphony': 'konsert',
    'concerto': 'konsert',
    'orchestral': 'konsert',
    'chamber': 'konsert',
    'choral': 'konsert',
    'other_classical': 'konsert',
    'mixed': 'konsert',
}


def load_yaml(path: Path) -> dict:
    """Load a YAML file."""
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def save_yaml(path: Path, data: dict):
    """Save data to a YAML file."""
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def normalize_name(name: str) -> str:
    """Normalize a name for matching."""
    if not name:
        return ""
    name = name.lower().strip()
    name = re.sub(r'^(av|by|von|van|de|der|du|la|le)\s+', '', name)
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name


def get_next_id(directory: Path) -> int:
    """Get the next available ID for a directory of YAML files."""
    max_id = 0
    for f in directory.glob('*.yaml'):
        try:
            file_id = int(f.stem)
            max_id = max(max_id, file_id)
        except ValueError:
            pass
    return max_id + 1


def load_existing_persons() -> dict:
    """Load all existing persons into a lookup dict by normalized name."""
    persons = {}
    persons_dir = DATA_DIR / "persons"
    for f in persons_dir.glob('*.yaml'):
        data = load_yaml(f)
        if data:
            name = data.get('name', '')
            normalized = data.get('normalized_name') or normalize_name(name)
            persons[normalized] = data
            # Also index by original name lowercase
            persons[name.lower()] = data
    return persons


def load_existing_plays() -> dict:
    """Load all existing plays into a lookup dict by title."""
    plays = {}
    plays_dir = DATA_DIR / "plays"
    for f in plays_dir.glob('*.yaml'):
        data = load_yaml(f)
        if data:
            title = data.get('title', '')
            plays[title.lower()] = data
            orig = data.get('original_title', '')
            if orig:
                plays[orig.lower()] = data
    return plays


def find_literary_source(existing_plays: dict, based_on: str) -> int | None:
    """Find a work that this is based on."""
    if not based_on:
        return None

    # Extract play title from "based on" text
    patterns = [
        r"(?:Henrik\s+)?Ibsen'?s?\s+(.+)",
        r"(?:William\s+)?Shakespeare'?s?\s+(.+)",
        r"(?:August\s+)?Strindberg'?s?\s+(.+)",
        r"based on (.+)",
    ]

    play_title = based_on
    for pattern in patterns:
        match = re.search(pattern, based_on, re.IGNORECASE)
        if match:
            play_title = match.group(1).strip()
            break

    play_title = re.sub(r'\s*\(.*\)', '', play_title).strip()

    # Search for matching work
    for title, play in existing_plays.items():
        if play_title.lower() in title:
            work_type = play.get('work_type', '')
            if work_type in ('teaterstykke', 'nrk_teaterstykke'):
                return play.get('id')

    return None


def main():
    print("=" * 60)
    print("Import NRK Classical Performances to YAML")
    print("=" * 60)

    # Load classified data
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    performances = data.get('classical_performances', [])
    print(f"\nFound {len(performances)} classical performances to import")
    print(f"By genre: {data.get('statistics', {}).get('by_genre', {})}")

    # Load existing data
    existing_persons = load_existing_persons()
    existing_plays = load_existing_plays()
    print(f"Loaded {len(existing_persons)} existing persons")
    print(f"Loaded {len(existing_plays)} existing plays")

    # Get next IDs
    next_person_id = get_next_id(DATA_DIR / "persons")
    next_play_id = get_next_id(DATA_DIR / "plays")
    next_perf_id = get_next_id(DATA_DIR / "performances")

    print(f"Next IDs: person={next_person_id}, play={next_play_id}, performance={next_perf_id}")

    # Track new entities to avoid duplicates within this import
    new_persons = {}  # normalized_name -> person data
    new_works = {}    # (title, composer_id) -> work data
    created_episodes = set()  # prf_ids we've created

    stats = defaultdict(int)

    for i, perf in enumerate(performances):
        prf_id = perf.get('prf_id')
        title = perf.get('title')
        classification = perf.get('classification', {})

        if not classification.get('is_classical'):
            stats['skipped_not_classical'] += 1
            continue

        # Check if episode already exists
        episode_path = DATA_DIR / "episodes" / f"{prf_id}.yaml"
        if episode_path.exists() or prf_id in created_episodes:
            stats['skipped_exists'] += 1
            continue

        genre = classification.get('genre', 'orchestral')
        # Handle compound genres like "concerto|symphony"
        if '|' in genre:
            genre = genre.split('|')[0]

        work_type = GENRE_TO_WORK_TYPE.get(genre, 'orchestral')
        category = GENRE_TO_CATEGORY.get(genre, 'konsert')

        work_title = classification.get('work_title') or title
        original_title = classification.get('work_title_original')
        composer_name = classification.get('composer')
        based_on = classification.get('based_on_literary_work')

        print(f"\n[{i+1}/{len(performances)}] {work_title}")
        print(f"    Genre: {genre}, Composer: {composer_name}")

        # 1. Find or create composer
        composer_id = None
        if composer_name and composer_name.lower() not in ['unknown', 'unknown composer', 'various', 'none', 'null']:
            normalized = normalize_name(composer_name)

            # Check existing persons
            if normalized in existing_persons:
                composer_id = existing_persons[normalized].get('id')
                print(f"    Found existing composer: {composer_id}")
            elif composer_name.lower() in existing_persons:
                composer_id = existing_persons[composer_name.lower()].get('id')
                print(f"    Found existing composer by name: {composer_id}")
            # Check new persons from this import
            elif normalized in new_persons:
                composer_id = new_persons[normalized]['id']
                print(f"    Using new composer from this import: {composer_id}")
            else:
                # Create new person
                composer_id = next_person_id
                next_person_id += 1

                person_data = {
                    'id': composer_id,
                    'name': composer_name,
                    'normalized_name': normalized,
                }

                # Save person YAML
                person_path = DATA_DIR / "persons" / f"{composer_id}.yaml"
                save_yaml(person_path, person_data)
                new_persons[normalized] = person_data
                stats['created_persons'] += 1
                print(f"    Created new composer: {composer_id}")

        # 2. Find literary source
        based_on_work_id = find_literary_source(existing_plays, based_on)
        if based_on_work_id:
            print(f"    Found literary source: {based_on} -> work {based_on_work_id}")

        # 3. Find or create work
        work_key = (work_title.lower(), composer_id)

        work_id = None
        # Check existing plays
        if work_title.lower() in existing_plays:
            existing = existing_plays[work_title.lower()]
            # Only reuse if same composer or no composer specified
            if composer_id is None or existing.get('composer_id') == composer_id:
                work_id = existing.get('id')
                print(f"    Found existing work: {work_id}")

        # Check new works from this import
        if work_id is None and work_key in new_works:
            work_id = new_works[work_key]['id']
            print(f"    Using new work from this import: {work_id}")

        if work_id is None:
            # Create new work
            work_id = next_play_id
            next_play_id += 1

            work_data = {
                'id': work_id,
                'title': work_title,
                'work_type': work_type,
                'category': category,
            }

            if original_title and original_title != work_title:
                work_data['original_title'] = original_title

            if composer_id:
                work_data['composer_id'] = composer_id

            if based_on_work_id:
                work_data['based_on_work_id'] = based_on_work_id

            # Save work YAML
            work_path = DATA_DIR / "plays" / f"{work_id}.yaml"
            save_yaml(work_path, work_data)
            new_works[work_key] = work_data
            existing_plays[work_title.lower()] = work_data
            stats['created_works'] += 1
            print(f"    Created new work: {work_id}")

        # 4. Create performance
        performance_id = next_perf_id
        next_perf_id += 1

        perf_data = {
            'id': performance_id,
            'work_id': work_id,
            'source': 'nrk',
            'title': title,
            'medium': perf.get('medium', 'tv'),
        }

        if perf.get('year'):
            perf_data['year'] = perf.get('year')

        description = perf.get('description') or perf.get('subtitle')
        if description:
            perf_data['description'] = description

        if perf.get('series_id'):
            perf_data['series_id'] = perf.get('series_id')

        if perf.get('duration_seconds'):
            perf_data['total_duration'] = perf.get('duration_seconds')

        if perf.get('image_url'):
            perf_data['image_url'] = perf.get('image_url')

        # Add credits from contributors
        contributors = perf.get('contributors', [])
        if contributors:
            credits = []
            for contrib in contributors:
                name = contrib.get('name')
                role = contrib.get('role', 'other')

                if not name:
                    continue

                # Find or create person for contributor
                contrib_normalized = normalize_name(name)
                contrib_id = None

                if contrib_normalized in existing_persons:
                    contrib_id = existing_persons[contrib_normalized].get('id')
                elif name.lower() in existing_persons:
                    contrib_id = existing_persons[name.lower()].get('id')
                elif contrib_normalized in new_persons:
                    contrib_id = new_persons[contrib_normalized]['id']
                else:
                    # Create new person
                    contrib_id = next_person_id
                    next_person_id += 1

                    contrib_person = {
                        'id': contrib_id,
                        'name': name,
                        'normalized_name': contrib_normalized,
                    }
                    person_path = DATA_DIR / "persons" / f"{contrib_id}.yaml"
                    save_yaml(person_path, contrib_person)
                    new_persons[contrib_normalized] = contrib_person
                    existing_persons[contrib_normalized] = contrib_person
                    stats['created_persons'] += 1

                credits.append({
                    'person_id': contrib_id,
                    'role': role.lower() if role else 'other',
                })

            if credits:
                perf_data['credits'] = credits

        # Save performance YAML
        perf_path = DATA_DIR / "performances" / f"{performance_id}.yaml"
        save_yaml(perf_path, perf_data)
        stats['created_performances'] += 1
        print(f"    Created performance: {performance_id}")

        # 5. Create episode
        episode_data = {
            'prf_id': prf_id,
            'title': title,
            'play_id': work_id,
            'performance_id': performance_id,
            'source': 'nrk',
            'medium': perf.get('medium', 'tv'),
        }

        if perf.get('year'):
            episode_data['year'] = perf.get('year')

        if description:
            episode_data['description'] = description

        if perf.get('duration_seconds'):
            episode_data['duration_seconds'] = perf.get('duration_seconds')

        if perf.get('image_url'):
            episode_data['image_url'] = perf.get('image_url')

        if perf.get('nrk_url'):
            episode_data['nrk_url'] = perf.get('nrk_url')

        if perf.get('series_id'):
            episode_data['series_id'] = perf.get('series_id')

        # Save episode YAML
        save_yaml(episode_path, episode_data)
        created_episodes.add(prf_id)
        stats['created_episodes'] += 1

    print("\n" + "=" * 60)
    print("IMPORT COMPLETE")
    print("=" * 60)
    print(f"Created persons: {stats['created_persons']}")
    print(f"Created works: {stats['created_works']}")
    print(f"Created performances: {stats['created_performances']}")
    print(f"Created episodes: {stats['created_episodes']}")
    print(f"Skipped (already exists): {stats['skipped_exists']}")
    print(f"Skipped (not classical): {stats['skipped_not_classical']}")

    print("\nNext steps:")
    print("1. Run: python3 scripts/validate_data.py")
    print("2. Run: python3 scripts/build_database.py")
    print("3. Review: git diff data/")


if __name__ == "__main__":
    main()
