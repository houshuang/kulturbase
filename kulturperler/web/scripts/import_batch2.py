#!/usr/bin/env python3
"""Import batch 2 of programs from NRK."""

import requests
import yaml
import re
from pathlib import Path

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

def get_image_url(data):
    """Extract 960px image URL from program data."""
    image = data.get('image', {})
    web_images = image.get('webImages', [])
    if web_images:
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

def import_program(prf_id, series_id=None, play_id=None, performance_id=None):
    """Import a single program."""
    print(f"Importing {prf_id}...")
    data = get_program(prf_id)
    if not data:
        return False

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
    if series_id:
        episode['series_id'] = series_id
    if play_id:
        episode['play_id'] = play_id
    if performance_id:
        episode['performance_id'] = performance_id

    episode = {k: v for k, v in episode.items() if v is not None}
    return save_episode(episode)

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
        season_name = season.get('_links', {}).get('self', {}).get('name')
        if not season_name:
            continue
        season_url = f"https://psapi.nrk.no/tv/catalog/series/{series_id}/seasons/{season_name}"
        r2 = requests.get(season_url)
        if r2.status_code == 200:
            eps = r2.json().get('_embedded', {}).get('instalments', [])
            if not eps:
                eps = r2.json().get('_embedded', {}).get('episodes', [])
            all_episodes.extend(eps)

    return all_episodes

def import_series(series_id, category='kulturprogram', work_type='bokprogram'):
    """Import all episodes from a series and create work/performance if needed."""
    print(f"\nImporting series {series_id}...")

    # Get series info
    url = f"https://psapi.nrk.no/tv/catalog/series/{series_id}"
    r = requests.get(url)
    if r.status_code != 200:
        print(f"  Failed: {r.status_code}")
        return

    data = r.json()
    info = data.get('sequential', data.get('standard', {}))
    titles = info.get('titles', {})
    title = titles.get('title', series_id)
    description = titles.get('subtitle', '')

    # Get image
    images = info.get('image', [])
    image_url = None
    for img in images:
        if img.get('width') == 960:
            image_url = img.get('url')
            break
    if not image_url and images:
        image_url = images[-1].get('url')

    episodes = get_series_episodes(series_id)
    print(f"  Found {len(episodes)} episodes")

    if not episodes:
        return

    # Get first episode year
    first_year = None
    for ep in episodes:
        prf_id = ep.get('prfId')
        if prf_id:
            prog = get_program(prf_id)
            if prog and prog.get('productionYear'):
                first_year = prog.get('productionYear')
                break

    # Import episodes
    for ep in episodes:
        prf_id = ep.get('prfId')
        if not prf_id:
            continue
        import_program(prf_id, series_id=series_id)

    return {
        'series_id': series_id,
        'title': title,
        'description': description,
        'image_url': image_url,
        'year': first_year,
        'episode_count': len(episodes),
        'category': category,
        'work_type': work_type
    }

def main():
    print("=" * 60)
    print("Importing Batch 2 Programs")
    print("=" * 60)

    # 1. Theatre/Drama standalone programs
    print("\n--- Theatre/Drama Programs ---")
    theatre_programs = [
        'FFIL76000776',  # En midtsommernattsdrøm
        'MKMF17000014',  # Hypokonderen
        'FOLA04000877',  # Prisgitt part 1
        'FOLA03007279',  # Et farlig spørsmål
        'FBUA00008183',  # Gutten og nordavinden
        'KOID60007221',  # Accident
    ]
    for prf_id in theatre_programs:
        import_program(prf_id)

    # Check for Prisgitt part 2
    import_program('FOLA04000977')  # Prisgitt part 2 if exists

    # 2. Portrait/documentary programs
    print("\n--- Portrait Programs ---")
    portrait_programs = [
        'FTEA00007065',  # Møte med Tarjei Vesaas
        'FKUR21000194',  # Ernst Orvil - absolutt poet
        'FMUS12003291',  # Ingrid Lorentzen - ung norsk danser
    ]
    for prf_id in portrait_programs:
        import_program(prf_id)

    # 3. Other standalone programs
    print("\n--- Other Programs ---")
    other_programs = [
        'FUHA03004589',  # Jenter
        'FUHA01003072',  # Hvem er redd for den stygge ulv?
        'FUHA02000373',  # Sanger fra Tolvskillingsoperaen
    ]
    for prf_id in other_programs:
        import_program(prf_id)

    # 4. Series - Theatre related
    print("\n--- Theatre Series ---")
    import_series('eidem-noveller', category='teater', work_type='nrk_teaterstykke')
    import_series('lykkeland-musikkspill', category='teater', work_type='musikal')
    import_series('alke', category='dramaserie', work_type='dramaserie')
    import_series('ballett-blanding', category='kulturprogram', work_type='dokumentar')
    import_series('mia-en-komiserie', category='dramaserie', work_type='dramaserie')
    import_series('fire-hoeytider', category='kulturprogram', work_type='dokumentar')

    # 5. Kulturprogrammer series
    print("\n--- Kulturprogrammer Series ---")
    kultur_series = [
        ('ukens-lyriker', 'lyrikk'),
        ('om-poesi', 'lyrikk'),
        ('samtaler-i-natten', 'bokprogram'),
        ('tre-reportere-soeker-en-forfatter', 'bokprogram'),
        ('forfatterportrett', 'bokprogram'),
        ('ord-for-natten', 'lyrikk'),
        ('teaterliv', 'dokumentar'),
        ('filmredaksjonen', 'kulturmagasin'),
        ('agenda', 'kulturmagasin'),
    ]

    series_info = []
    for series_id, work_type in kultur_series:
        info = import_series(series_id, category='kulturprogram', work_type=work_type)
        if info:
            series_info.append(info)

    print("\n" + "=" * 60)
    print("Import complete!")
    print("=" * 60)

if __name__ == '__main__':
    main()
