#!/usr/bin/env python3
"""
Import Bergen Philharmonic concerts from external_resources.yaml into proper
Work → Performance → Episode structure.

Uses Gemini 2.0 Flash with Google Search grounding to enrich metadata:
- Full composer name with birth/death years
- Opus/catalog numbers
- Work type (symphony, concerto, etc.)

Creates YAML files in data/ directory.
"""

import json
import yaml
import re
import os
import time
import requests
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data"
CACHE_FILE = Path(__file__).parent.parent / "output" / "bergenphil_enrichment_cache.json"

GEMINI_KEY = os.getenv('GEMINI_KEY')
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"


def load_yaml(path: Path) -> dict | list:
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


def load_cache() -> dict:
    """Load the enrichment cache."""
    if CACHE_FILE.exists():
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_cache(cache: dict):
    """Save the enrichment cache."""
    CACHE_FILE.parent.mkdir(exist_ok=True)
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def enrich_with_gemini(title: str, description: str, cache: dict) -> dict | None:
    """Use Gemini with Google Search to enrich concert metadata."""
    cache_key = f"{title}|{description}"
    if cache_key in cache:
        return cache[cache_key]

    prompt = f"""Given this concert recording:
Title: {title}
Description: {description}
Orchestra: Bergen Filharmoniske Orkester

Please provide structured information about this musical work. Return ONLY valid JSON (no markdown, no explanation):

{{
  "composer_full_name": "Full name like 'Antonín Dvořák' or null if unknown",
  "composer_birth_year": 1841,
  "composer_death_year": 1904,
  "work_title": "Full work title like 'Violin Concerto in A minor, Op. 53'",
  "work_title_norwegian": "Norwegian title if different, or null",
  "opus_number": "Op. 53 or similar, or null",
  "catalog_number": "BWV/K/D number if applicable, or null",
  "work_type": "symphony|concerto|orchestral|chamber|choral|opera",
  "is_compilation": false,
  "notes": "Any relevant notes about the work"
}}

Use web search to verify composer details and opus numbers. If multiple works are in the title, focus on the main/first one."""

    try:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}],
            "generationConfig": {"temperature": 0.1}
        }

        resp = requests.post(GEMINI_URL, json=payload, timeout=30)

        if not resp.ok:
            print(f"    Gemini API error: {resp.status_code}")
            return None

        result = resp.json()
        text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')

        # Clean up the response - remove markdown code blocks if present
        text = re.sub(r'^```json\s*', '', text.strip())
        text = re.sub(r'\s*```$', '', text)

        try:
            data = json.loads(text)
            # Handle case where Gemini returns a list instead of dict
            if isinstance(data, list):
                data = data[0] if data else {}
            if not isinstance(data, dict):
                print(f"    Unexpected data type: {type(data)}")
                return None
            cache[cache_key] = data
            save_cache(cache)
            return data
        except json.JSONDecodeError as e:
            print(f"    JSON parse error: {e}")
            print(f"    Raw response: {text[:200]}")
            return None

    except Exception as e:
        print(f"    Gemini error: {e}")
        return None


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
            persons[name.lower()] = data
    return persons


def load_existing_works() -> dict:
    """Load all existing works into a lookup dict."""
    works = {}
    plays_dir = DATA_DIR / "plays"
    for f in plays_dir.glob('*.yaml'):
        data = load_yaml(f)
        if data:
            title = data.get('title', '')
            works[title.lower()] = data
            orig = data.get('original_title', '')
            if orig:
                works[orig.lower()] = data
    return works


def parse_date_from_description(description: str) -> int | None:
    """Extract year from description like 'Innspilt: 2025-09-18'."""
    match = re.search(r'Innspilt:\s*(\d{4})', description)
    if match:
        return int(match.group(1))
    return None


def main():
    print("=" * 60)
    print("Import Bergen Philharmonic Concerts to YAML")
    print("=" * 60)

    if not GEMINI_KEY:
        print("ERROR: GEMINI_KEY not found in .env")
        return

    # Load external resources
    resources_path = DATA_DIR / "external_resources.yaml"
    all_resources = load_yaml(resources_path)

    # Filter for Bergen Phil concerts
    bergenphil = [r for r in all_resources if r.get('type') == 'bergenphilive']
    print(f"\nFound {len(bergenphil)} Bergen Phil concerts")

    # Load existing data
    existing_persons = load_existing_persons()
    existing_works = load_existing_works()
    cache = load_cache()

    print(f"Loaded {len(existing_persons)} existing persons")
    print(f"Loaded {len(existing_works)} existing works")
    print(f"Loaded {len(cache)} cached enrichments")

    # Get next IDs
    next_person_id = get_next_id(DATA_DIR / "persons")
    next_play_id = get_next_id(DATA_DIR / "plays")
    next_perf_id = get_next_id(DATA_DIR / "performances")

    print(f"Next IDs: person={next_person_id}, play={next_play_id}, performance={next_perf_id}")

    # Track new entities
    new_persons = {}
    new_works = {}
    stats = defaultdict(int)

    for i, concert in enumerate(bergenphil):
        title = concert.get('title', '')
        description = concert.get('description', '')
        url = concert.get('url', '')
        resource_id = concert.get('id')

        print(f"\n[{i+1}/{len(bergenphil)}] {title}")

        # Get year from description
        year = parse_date_from_description(description)

        # Enrich with Gemini
        enriched = enrich_with_gemini(title, description, cache)
        time.sleep(0.5)  # Rate limiting

        if enriched and isinstance(enriched, dict):
            print(f"    Enriched: {enriched.get('composer_full_name')} - {enriched.get('work_title')}")
        else:
            print(f"    No enrichment available")
            enriched = {}

        # 1. Find or create composer
        composer_id = None
        composer_name = enriched.get('composer_full_name')

        if composer_name:
            normalized = normalize_name(composer_name)

            if normalized in existing_persons:
                composer_id = existing_persons[normalized].get('id')
                print(f"    Found existing composer: {composer_id}")
            elif composer_name.lower() in existing_persons:
                composer_id = existing_persons[composer_name.lower()].get('id')
            elif normalized in new_persons:
                composer_id = new_persons[normalized]['id']
            else:
                # Create new composer
                composer_id = next_person_id
                next_person_id += 1

                person_data = {
                    'id': composer_id,
                    'name': composer_name,
                    'normalized_name': normalized,
                }

                if enriched.get('composer_birth_year'):
                    person_data['birth_year'] = enriched['composer_birth_year']
                if enriched.get('composer_death_year'):
                    person_data['death_year'] = enriched['composer_death_year']

                person_path = DATA_DIR / "persons" / f"{composer_id}.yaml"
                save_yaml(person_path, person_data)
                new_persons[normalized] = person_data
                existing_persons[normalized] = person_data
                stats['created_persons'] += 1
                print(f"    Created composer: {composer_id} ({composer_name})")

        # 2. Find or create work
        work_title = enriched.get('work_title') or title
        work_type = enriched.get('work_type', 'orchestral')

        # Map to our work types
        if work_type not in ('symphony', 'concerto', 'orchestral', 'chamber', 'choral', 'opera'):
            work_type = 'orchestral'

        work_key = (work_title.lower(), composer_id)
        work_id = None

        if work_title.lower() in existing_works:
            existing = existing_works[work_title.lower()]
            if composer_id is None or existing.get('composer_id') == composer_id:
                work_id = existing.get('id')
                print(f"    Found existing work: {work_id}")

        if work_id is None and work_key in new_works:
            work_id = new_works[work_key]['id']

        if work_id is None:
            work_id = next_play_id
            next_play_id += 1

            work_data = {
                'id': work_id,
                'title': work_title,
                'work_type': work_type,
                'category': 'konsert',
            }

            norwegian_title = enriched.get('work_title_norwegian')
            if norwegian_title and norwegian_title != work_title:
                work_data['original_title'] = norwegian_title

            if composer_id:
                work_data['composer_id'] = composer_id

            opus = enriched.get('opus_number') or enriched.get('catalog_number')
            if opus:
                # Store opus in synopsis for now
                work_data['synopsis'] = f"Opus: {opus}"

            work_path = DATA_DIR / "plays" / f"{work_id}.yaml"
            save_yaml(work_path, work_data)
            new_works[work_key] = work_data
            existing_works[work_title.lower()] = work_data
            stats['created_works'] += 1
            print(f"    Created work: {work_id}")

        # 3. Create performance
        performance_id = next_perf_id
        next_perf_id += 1

        perf_data = {
            'id': performance_id,
            'work_id': work_id,
            'source': 'bergenphilive',
            'title': title,
            'medium': 'stream',
            'venue': 'Bergen',
        }

        if year:
            perf_data['year'] = year

        if description:
            perf_data['description'] = description

        # Add Bergen Phil as institution/orchestra credit
        perf_data['credits'] = []

        perf_path = DATA_DIR / "performances" / f"{performance_id}.yaml"
        save_yaml(perf_path, perf_data)
        stats['created_performances'] += 1

        # 4. Create episode (the actual stream link)
        episode_id = f"BERGENPHIL_{resource_id}"
        episode_path = DATA_DIR / "episodes" / f"{episode_id}.yaml"

        if not episode_path.exists():
            episode_data = {
                'prf_id': episode_id,
                'title': title,
                'play_id': work_id,
                'performance_id': performance_id,
                'source': 'bergenphilive',
                'medium': 'stream',
                'nrk_url': url,  # Using nrk_url field for external URL
            }

            if year:
                episode_data['year'] = year
            if description:
                episode_data['description'] = description

            save_yaml(episode_path, episode_data)
            stats['created_episodes'] += 1

    print("\n" + "=" * 60)
    print("IMPORT COMPLETE")
    print("=" * 60)
    print(f"Created persons: {stats['created_persons']}")
    print(f"Created works: {stats['created_works']}")
    print(f"Created performances: {stats['created_performances']}")
    print(f"Created episodes: {stats['created_episodes']}")

    print("\nNext steps:")
    print("1. Run: python3 scripts/validate_data.py")
    print("2. Run: python3 scripts/build_database.py")
    print("3. Review: git diff data/")


if __name__ == "__main__":
    main()
