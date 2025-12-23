#!/usr/bin/env python3
"""
Link kulturprogram episodes to authors.
- Identifies primary author from episode title/description using OpenAI
- Matches to existing persons or creates new ones
- Enriches new persons with Wikipedia data (bio, birth/death, image)
- Updates episode YAML files with about_person_id
"""

import json
import os
import re
import sqlite3
import time
import urllib.request
import urllib.parse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import yaml
from openai import OpenAI

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
EPISODES_DIR = DATA_DIR / "episodes"
PERSONS_DIR = DATA_DIR / "persons"
DB_PATH = BASE_DIR / "static" / "kulturperler.db"

# Load API key
from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")
client = OpenAI(api_key=os.getenv("OPENAI_KEY"))

# Track next person ID
NEXT_PERSON_ID = 4547


def load_kulturprogram_episodes():
    """Load all kulturprogram episodes without about_person_id."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    query = """
        SELECT e.prf_id, e.title, e.description, e.series_id, e.performance_id
        FROM episodes e
        JOIN performances p ON e.performance_id = p.id
        JOIN works w ON p.work_id = w.id
        WHERE w.category = 'kulturprogram'
        AND e.about_person_id IS NULL
    """

    episodes = [dict(row) for row in conn.execute(query).fetchall()]
    conn.close()

    print(f"Loaded {len(episodes)} kulturprogram episodes without about_person_id")
    return episodes


def load_persons():
    """Load all persons for matching."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    persons = {}
    for row in conn.execute("SELECT id, name, normalized_name FROM persons"):
        name_lower = (row['normalized_name'] or row['name'].lower()).strip()
        persons[name_lower] = {'id': row['id'], 'name': row['name']}

    conn.close()
    print(f"Loaded {len(persons)} persons for matching")
    return persons


def identify_authors_batch(episodes_batch):
    """Use OpenAI to identify primary author for a batch of episodes."""

    # Build episode list for prompt
    episode_texts = []
    for i, ep in enumerate(episodes_batch, 1):
        desc = (ep.get('description') or '')[:200]  # Truncate long descriptions
        desc = desc.replace('\n', ' ').strip()
        text = f'{i}. [{ep["prf_id"]}] "{ep["title"]}"'
        if desc:
            text += f' - "{desc}"'
        episode_texts.append(text)

    prompt = f"""Identify the PRIMARY author, writer, poet, or cultural figure each episode is about.
Return ONLY if there is ONE clear primary subject being discussed/interviewed/featured.
Return null if: unclear, multiple subjects equally featured, general topic, or not about a specific person.

Episodes:
{chr(10).join(episode_texts)}

Return a JSON array with objects containing:
- prf_id: the episode ID
- person_name: full name of the person (null if no clear subject)

Example: [{{"prf_id": "MKTF01002212", "person_name": "Ole Robert Sunde"}}, {{"prf_id": "RKUT01001100", "person_name": null}}]

Return ONLY the JSON array, no other text."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2000
        )

        content = response.choices[0].message.content.strip()
        # Clean up response - remove markdown code blocks if present
        if content.startswith("```"):
            content = re.sub(r'^```(?:json)?\n?', '', content)
            content = re.sub(r'\n?```$', '', content)

        return json.loads(content)
    except Exception as e:
        print(f"  Error in batch: {e}")
        return []


def fetch_wikipedia_data(name):
    """Fetch person data from Norwegian Wikipedia."""
    try:
        # URL encode the name
        encoded_name = urllib.parse.quote(name.replace(' ', '_'))
        url = f"https://no.wikipedia.org/api/rest_v1/page/summary/{encoded_name}"

        req = urllib.request.Request(url, headers={
            'User-Agent': 'Kulturperler/1.0 (https://kulturbase.no)'
        })

        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        result = {
            'bio': data.get('extract', ''),
            'wikipedia_url': data.get('content_urls', {}).get('desktop', {}).get('page'),
            'image_url': None,
            'birth_year': None,
            'death_year': None
        }

        # Try to get image
        if data.get('thumbnail', {}).get('source'):
            result['image_url'] = data['thumbnail']['source']

        # Try to extract birth/death years from description or extract
        desc = data.get('description', '') + ' ' + data.get('extract', '')

        # Pattern: (1920-1990) or (født 1920) or (1920-)
        year_match = re.search(r'\((\d{4})\s*[-–]\s*(\d{4})?\)', desc)
        if year_match:
            result['birth_year'] = int(year_match.group(1))
            if year_match.group(2):
                result['death_year'] = int(year_match.group(2))
        else:
            # Try "født X" pattern
            birth_match = re.search(r'født\s+(\d{4})', desc, re.IGNORECASE)
            if birth_match:
                result['birth_year'] = int(birth_match.group(1))

            death_match = re.search(r'død\s+(\d{4})', desc, re.IGNORECASE)
            if death_match:
                result['death_year'] = int(death_match.group(1))

        return result
    except Exception as e:
        print(f"    Wikipedia fetch failed for {name}: {e}")
        return None


def match_or_create_person(name, persons_dict):
    """Match name to existing person or create new one."""
    global NEXT_PERSON_ID

    if not name:
        return None

    name_lower = name.lower().strip()

    # Exact match
    if name_lower in persons_dict:
        return persons_dict[name_lower]['id']

    # Try without middle names (e.g., "Jon Olav Fosse" -> "Jon Fosse")
    parts = name.split()
    if len(parts) > 2:
        short_name = f"{parts[0]} {parts[-1]}".lower()
        if short_name in persons_dict:
            return persons_dict[short_name]['id']

    # Try common variations
    variations = [
        name_lower.replace('.', ''),
        name_lower.replace('-', ' '),
        re.sub(r'\s+', ' ', name_lower),
    ]
    for var in variations:
        if var in persons_dict:
            return persons_dict[var]['id']

    # No match - create new person
    print(f"  Creating new person: {name}")

    # Fetch Wikipedia data
    wiki_data = fetch_wikipedia_data(name)

    person_data = {
        'id': NEXT_PERSON_ID,
        'name': name,
        'normalized_name': name_lower,
    }

    if wiki_data:
        if wiki_data.get('bio'):
            # Truncate bio to first 2-3 sentences
            bio = wiki_data['bio']
            sentences = re.split(r'(?<=[.!?])\s+', bio)
            person_data['bio'] = ' '.join(sentences[:3])
        if wiki_data.get('birth_year'):
            person_data['birth_year'] = wiki_data['birth_year']
        if wiki_data.get('death_year'):
            person_data['death_year'] = wiki_data['death_year']
        if wiki_data.get('wikipedia_url'):
            person_data['wikipedia_url'] = wiki_data['wikipedia_url']

    # Write person YAML
    person_path = PERSONS_DIR / f"{NEXT_PERSON_ID}.yaml"
    with open(person_path, 'w', encoding='utf-8') as f:
        yaml.dump(person_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    # Add to dict for future matching
    persons_dict[name_lower] = {'id': NEXT_PERSON_ID, 'name': name}

    person_id = NEXT_PERSON_ID
    NEXT_PERSON_ID += 1

    return person_id


def update_episode_yaml(prf_id, about_person_id):
    """Add about_person_id to episode YAML file."""
    yaml_path = EPISODES_DIR / f"{prf_id}.yaml"

    if not yaml_path.exists():
        print(f"  Warning: Episode file not found: {yaml_path}")
        return False

    with open(yaml_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if already has about_person_id
    if 'about_person_id:' in content:
        return False

    # Add about_person_id after prf_id line or at end
    if '\nprf_id:' in content:
        # Add after the title line if exists, otherwise after prf_id
        lines = content.split('\n')
        new_lines = []
        added = False
        for i, line in enumerate(lines):
            new_lines.append(line)
            if not added and (line.startswith('title:') or (line.startswith('prf_id:') and i + 1 < len(lines) and not lines[i + 1].startswith('title:'))):
                new_lines.append(f'about_person_id: {about_person_id}')
                added = True
        if not added:
            new_lines.append(f'about_person_id: {about_person_id}')
        content = '\n'.join(new_lines)
    else:
        content += f'\nabout_person_id: {about_person_id}\n'

    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return True


def main():
    print("=" * 60)
    print("Link Kulturprogram Episodes to Authors")
    print("=" * 60)

    # Load data
    episodes = load_kulturprogram_episodes()
    persons = load_persons()

    if not episodes:
        print("No episodes to process!")
        return

    # Process in batches
    BATCH_SIZE = 15
    all_results = []

    print(f"\nProcessing {len(episodes)} episodes in batches of {BATCH_SIZE}...")

    for i in range(0, len(episodes), BATCH_SIZE):
        batch = episodes[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(episodes) + BATCH_SIZE - 1) // BATCH_SIZE

        print(f"  Batch {batch_num}/{total_batches}...", end=" ", flush=True)

        results = identify_authors_batch(batch)
        all_results.extend(results)

        print(f"got {len(results)} results")

        # Small delay to respect rate limits
        time.sleep(0.1)

    # Process results
    print(f"\nProcessing {len(all_results)} identified authors...")

    matched = 0
    created = 0
    skipped = 0
    updated_episodes = 0

    for result in all_results:
        prf_id = result.get('prf_id')
        person_name = result.get('person_name')

        if not prf_id:
            continue

        if not person_name:
            skipped += 1
            continue

        # Match or create person
        person_id = match_or_create_person(person_name, persons)

        if person_id:
            # Check if this was a new person (ID >= original NEXT_PERSON_ID)
            if person_id >= 4547:
                created += 1
            else:
                matched += 1

            # Update episode YAML
            if update_episode_yaml(prf_id, person_id):
                updated_episodes += 1

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Episodes processed: {len(episodes)}")
    print(f"Authors identified: {len(all_results) - skipped}")
    print(f"  - Matched to existing: {matched}")
    print(f"  - New persons created: {created}")
    print(f"Episodes skipped (no clear subject): {skipped}")
    print(f"Episode files updated: {updated_episodes}")
    print(f"\nNext steps:")
    print(f"  1. python3 scripts/validate_data.py")
    print(f"  2. python3 scripts/build_database.py")


if __name__ == "__main__":
    main()
