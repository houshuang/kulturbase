#!/usr/bin/env python3
"""Import theatre productions and cultural programs from NRK."""

import requests
import yaml
import re
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / 'data'

def parse_duration(duration_str):
    """Parse ISO8601 duration to seconds."""
    if not duration_str:
        return None
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?', duration_str)
    if not match:
        return None
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = float(match.group(3) or 0)
    return int(hours * 3600 + minutes * 60 + seconds)

def get_program(prf_id):
    """Fetch program details from NRK API."""
    url = f"https://psapi.nrk.no/programs/{prf_id}"
    r = requests.get(url)
    if r.status_code != 200:
        print(f"  Failed to fetch {prf_id}: {r.status_code}")
        return None
    return r.json()

def get_series_episodes(series_id):
    """Fetch all episodes from a series."""
    url = f"https://psapi.nrk.no/tv/catalog/series/{series_id}"
    r = requests.get(url)
    if r.status_code != 200:
        print(f"  Failed to fetch series {series_id}: {r.status_code}")
        return []

    data = r.json()
    seasons = data.get('_embedded', {}).get('seasons', [])

    all_episodes = []
    for season in seasons:
        season_id = season.get('name') or season.get('id', '1')
        season_url = f"https://psapi.nrk.no/tv/catalog/series/{series_id}/seasons/{season_id}/episodes"
        r2 = requests.get(season_url)
        if r2.status_code == 200:
            eps = r2.json().get('_embedded', {}).get('episodes', [])
            all_episodes.extend(eps)
        else:
            # Try embedded episodes
            eps = season.get('_embedded', {}).get('episodes', [])
            all_episodes.extend(eps)

    return all_episodes

def get_image_url(data):
    """Extract best image URL from program data."""
    image = data.get('image', {})
    web_images = image.get('webImages', [])
    if web_images:
        # Get 960px version if available
        for img in web_images:
            if img.get('pixelWidth') == 960:
                return img.get('imageUrl')
        return web_images[-1].get('imageUrl')
    return None

def save_episode(episode_data):
    """Save episode to YAML file."""
    prf_id = episode_data['prf_id']
    filepath = DATA_DIR / 'episodes' / f'{prf_id}.yaml'

    if filepath.exists():
        print(f"  Skipping {prf_id} - already exists")
        return False

    with open(filepath, 'w') as f:
        yaml.dump(episode_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f"  Created {prf_id}")
    return True

def save_about_program(program_data):
    """Save about program to YAML file."""
    prog_id = program_data['id']
    filepath = DATA_DIR / 'nrk_about_programs' / f'{prog_id}.yaml'

    if filepath.exists():
        print(f"  Skipping about program {prog_id} - already exists")
        return False

    with open(filepath, 'w') as f:
        yaml.dump(program_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f"  Created about program {prog_id}")
    return True

def import_standalone_program(prf_id, play_id=None, work_title=None):
    """Import a standalone theatre program."""
    print(f"\nImporting {prf_id}...")
    data = get_program(prf_id)
    if not data:
        return

    episode = {
        'prf_id': prf_id,
        'title': data.get('title'),
        'description': data.get('shortDescription') or data.get('longDescription'),
        'year': data.get('productionYear'),
        'duration_seconds': parse_duration(data.get('duration')),
        'image_url': get_image_url(data),
        'nrk_url': f"https://tv.nrk.no/program/{prf_id.lower()}",
        'source': 'nrk',
        'medium': 'tv',
    }

    if play_id:
        episode['play_id'] = play_id

    # Remove None values
    episode = {k: v for k, v in episode.items() if v is not None}

    save_episode(episode)

def import_series_as_episodes(series_id, link_person_id=None):
    """Import all episodes from a series."""
    print(f"\nImporting series {series_id}...")

    episodes = get_series_episodes(series_id)
    print(f"  Found {len(episodes)} episodes")

    for ep in episodes:
        prf_id = ep.get('prfId')
        if not prf_id:
            continue

        # Get full program details for better metadata
        full_data = get_program(prf_id)
        if full_data:
            data = full_data
        else:
            data = ep

        episode = {
            'prf_id': prf_id,
            'title': data.get('title') or ep.get('titles', {}).get('title'),
            'description': data.get('shortDescription') or ep.get('titles', {}).get('subtitle'),
            'year': data.get('productionYear') or ep.get('productionYear'),
            'duration_seconds': parse_duration(data.get('duration') or ep.get('duration')),
            'image_url': get_image_url(data) or get_image_url(ep),
            'nrk_url': f"https://tv.nrk.no/program/{prf_id.lower()}",
            'series_id': series_id,
            'source': 'nrk',
            'medium': 'tv',
        }

        # Remove None values
        episode = {k: v for k, v in episode.items() if v is not None}

        save_episode(episode)

def import_series_as_about_program(series_id, person_id=None, play_id=None):
    """Import a series as an about program (for linking to person/play pages)."""
    print(f"\nImporting series {series_id} as about program...")

    url = f"https://psapi.nrk.no/tv/catalog/series/{series_id}"
    r = requests.get(url)
    if r.status_code != 200:
        print(f"  Failed to fetch series {series_id}: {r.status_code}")
        return

    data = r.json()
    info = data.get('sequential', data.get('standard', {}))
    titles = info.get('titles', {})

    # Get episode count
    episodes = get_series_episodes(series_id)

    # Get total duration
    total_duration = 0
    for ep in episodes:
        dur = parse_duration(ep.get('duration'))
        if dur:
            total_duration += dur

    # Get image
    images = info.get('image', [])
    image_url = None
    for img in images:
        if img.get('width') == 960:
            image_url = img.get('url')
            break
    if not image_url and images:
        image_url = images[-1].get('url')

    program = {
        'id': series_id,
        'title': titles.get('title'),
        'description': titles.get('subtitle'),
        'duration_seconds': total_duration if total_duration > 0 else None,
        'nrk_url': f"https://tv.nrk.no/serie/{series_id}",
        'image_url': image_url,
        'program_type': 'serie',
        'episode_count': len(episodes),
        'interest_score': 100,
    }

    if person_id:
        program['person_id'] = person_id
    if play_id:
        program['play_id'] = play_id

    # Remove None values
    program = {k: v for k, v in program.items() if v is not None}

    save_about_program(program)

def main():
    print("=" * 60)
    print("Importing Theatre Productions and Cultural Programs")
    print("=" * 60)

    # 1. Standalone theatre productions
    print("\n--- Standalone Theatre Productions ---")

    # Lang dags ferd mot natt (Eugene O'Neill)
    import_standalone_program('MKDP52000010')

    # Hvem er redd for Virginia Woolf? (Edward Albee)
    import_standalone_program('ODRP20009502')

    # Albertine (Christian Krohg)
    import_standalone_program('FOLA01007387')

    # 2. Theatre series
    print("\n--- Theatre Series ---")

    # Genanse og verdighet (Dag Solstad)
    import_series_as_episodes('genanse-og-verdighet')

    # Vente på Godot (Samuel Beckett)
    import_series_as_episodes('vente-paa-godot')

    # 3. Cultural programs
    print("\n--- Cultural Programs ---")

    # Lesekunst
    import_series_as_episodes('lesekunst')

    # 4. About programs linked to Ibsen (person_id 879)
    print("\n--- Peer Gynt-kveld (linked to Ibsen) ---")

    # First import as episodes
    import_series_as_episodes('peer-gynt-kveld')

    # Also add as about program for Ibsen
    import_series_as_about_program('peer-gynt-kveld', person_id=879)

    print("\n" + "=" * 60)
    print("Import complete!")
    print("Run: python3 scripts/build_database.py")
    print("=" * 60)

if __name__ == '__main__':
    main()
