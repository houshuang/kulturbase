#!/usr/bin/env python3
"""Import programs from NRK screenshots - cultural programs and author portraits."""

import requests
import yaml
import re
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / 'data'

def get_image_url(data, size=960):
    """Extract image URL from NRK API response."""
    web_images = data.get('image', {}).get('webImages', [])
    for img in web_images:
        if img.get('pixelWidth') == size:
            return img.get('imageUrl')
    return web_images[-1].get('imageUrl') if web_images else None

def parse_duration(duration_str):
    """Parse ISO8601 duration to seconds."""
    if not duration_str:
        return None
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?', duration_str)
    if not match:
        return None
    h = int(match.group(1) or 0)
    m = int(match.group(2) or 0)
    s = float(match.group(3) or 0)
    return int(h * 3600 + m * 60 + s)

def save_yaml(path, data):
    """Save YAML file with proper formatting."""
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f"Saved: {path}")

def fetch_program(prf_id):
    """Fetch program details from NRK API."""
    url = f'https://psapi.nrk.no/programs/{prf_id}'
    r = requests.get(url)
    if r.status_code == 200:
        return r.json()
    return None

# Programs to import as nrk_about_programs (author/artist portraits)
ABOUT_PROGRAMS = [
    {
        'prf_id': 'FOLA02003373',
        'person_id': 442,  # Lise Fjeldstad
        'title': 'Lise Fjeldstad - i nærbilde',
    },
    {
        'prf_id': 'FOLA64003664',
        'person_id': 2154,  # Inger Hagerup
        'title': 'Vær utålmodig, menneske!',
    },
    {
        'prf_id': 'FSAM08008190',
        'person_id': 3989,  # Ferdinand Finne
        'title': 'Jesus er neppe medlem av statskirken',
    },
    {
        'prf_id': 'FOLA64008864',
        'person_id': 2376,  # Knut Hamsun
        'title': 'Nordiske kulturmiljøer - Nørholm',
    },
    {
        'prf_id': 'FOLA64001764',
        'person_id': 4019,  # Kitty L. Kielland
        'title': 'Kitty Kielland - Jærens malerinne',
    },
    {
        'prf_id': 'FSØR01003590',
        'person_id': 2375,  # Tore Hamsun
        'title': 'Tore Hamsun',
    },
    {
        'prf_id': 'FKUR02000595',
        'person_id': 2747,  # Stein Winge
        'title': 'Winge-spennet',
    },
    {
        'prf_id': 'FKUR02000194',
        'person_id': None,  # Erik Werenskiold - not in DB
        'title': 'De bygget Norge. Erik Werenskiold og Lysakerkretsen',
    },
    {
        'prf_id': 'FOLA68005368',
        'person_id': None,  # Edvard Munch - not in DB
        'title': '"Det var få som kjente Edvard Munch"',
    },
    {
        'prf_id': 'FUHA02004270',
        'person_id': None,  # Cabaret, no specific person
        'title': 'To må man være',
    },
    {
        'prf_id': 'FOLA63002063',
        'person_id': 3983,  # Camilla Collett
        'title': 'Camilla Collett til minne',
    },
    {
        'prf_id': 'OATF09000008',
        'person_id': 3998,  # Henrik Wergeland
        'title': 'Hva ville Wergeland?',
    },
    {
        'prf_id': 'FDRP28001492',
        'person_id': None,  # Per Aabel
        'title': 'Per Aabel - 90 år',
    },
    {
        'prf_id': 'FMRD09001694',
        'person_id': None,  # Ivar Aasen - needs person
        'title': 'Ivar Aasen - mannen og verket',
    },
]

# Series to import (for kulturprogrammer page)
SERIES = [
    {
        'series_id': 'forfatterinne-i-dag',
        'title': 'Forfatterinne i dag',
        'description': 'Nordisk serie om samtidens forfattere, alle kvinner. Gjennom forfatterportretter vises det at det ikke finnes noe entydig begrep som kvinnelitteratur.',
    },
    {
        'series_id': 'det-moderne-gjennombruddet',
        'title': 'Det moderne gjennombruddet',
        'description': 'Litteraturserie om det moderne gjennombruddet i nordisk litteratur. Nordisk samproduksjon.',
    },
    {
        'series_id': 'tre-reportere-soeker-en-forfatter',
        'title': 'Tre reportere søker en forfatter',
        'description': 'Litteraturprogram.',
    },
    {
        'series_id': 'arne-garborg-diktar-og-debattant',
        'title': 'Arne Garborg - diktar og debattant',
        'description': 'Dramatisering av forfattarskapen og livet til jærbuen og europearen Arne Garborg.',
        'person_id': 1117,  # Arne Garborg
    },
    {
        'series_id': 'lyrikeren-henrik-wergeland',
        'title': 'Lyrikeren Henrik Wergeland',
        'description': 'Litteraturprogram.',
        'person_id': 3998,  # Henrik Wergeland
    },
    {
        'series_id': 'norsk-lyrikk',
        'title': 'Norsk lyrikk',
        'description': 'Lyrikkprogram.',
    },
    {
        'series_id': 'takk-for-sist',
        'title': 'Takk for sist',
        'description': 'Møte mellom to mennesker som i karrieren har opptrådt på samme arena - som medspillere eller motstandere.',
    },
    {
        'series_id': 'teaterliv',
        'title': 'Teaterliv',
        'description': 'Serie om teater.',
    },
    {
        'series_id': 'bjoernson-forteller',
        'title': 'Bjørnson forteller',
        'description': 'Bjørnstjerne Bjørnson forteller.',
        'person_id': None,  # About Bjørnson
    },
    {
        'series_id': 'i-dagslys-og-rampelys',
        'title': 'I dagslys og rampelys',
        'description': 'Portrettserie om norske skuespillere.',
    },
]

def import_about_programs():
    """Import author/artist portrait programs."""
    print("\n=== Importing about programs ===")
    for prog in ABOUT_PROGRAMS:
        prf_id = prog['prf_id']
        out_path = DATA_DIR / 'nrk_about_programs' / f'{prf_id}.yaml'

        if out_path.exists():
            print(f"Skipping {prf_id} - already exists")
            continue

        data = fetch_program(prf_id)
        if not data:
            print(f"Failed to fetch {prf_id}")
            continue

        duration = parse_duration(data.get('duration'))
        image_url = get_image_url(data)

        yaml_data = {
            'id': prf_id,
            'title': prog['title'],
            'description': data.get('shortDescription') or data.get('longDescription', ''),
            'duration_seconds': duration,
            'nrk_url': f'https://tv.nrk.no/program/{prf_id}',
            'image_url': image_url,
            'program_type': 'program',
            'interest_score': 80,
        }

        if prog.get('person_id'):
            yaml_data['person_id'] = prog['person_id']

        save_yaml(out_path, yaml_data)

def get_series_info(series_id):
    """Fetch series info from NRK API."""
    url = f'https://psapi.nrk.no/tv/catalog/series/{series_id}'
    r = requests.get(url)
    if r.status_code == 200:
        return r.json()
    return None

def import_series_as_about_programs():
    """Import series metadata as about programs."""
    print("\n=== Importing series as about programs ===")
    for series in SERIES:
        series_id = series['series_id']
        out_path = DATA_DIR / 'nrk_about_programs' / f'{series_id}.yaml'

        if out_path.exists():
            print(f"Skipping {series_id} - already exists")
            continue

        data = get_series_info(series_id)
        if not data:
            print(f"Failed to fetch series {series_id}")
            # Create from local data
            yaml_data = {
                'id': series_id,
                'title': series['title'],
                'description': series['description'],
                'nrk_url': f'https://tv.nrk.no/serie/{series_id}',
                'program_type': 'serie',
                'interest_score': 75,
            }
        else:
            # Count episodes
            seasons = data.get('_embedded', {}).get('seasons', [])
            episode_count = 0
            for season in seasons:
                episodes = season.get('_embedded', {}).get('episodes', [])
                episode_count += len(episodes)

            image_url = None
            images = []
            # Try sequential.image.webImages
            try:
                sequential = data.get('sequential')
                if isinstance(sequential, dict):
                    img = sequential.get('image')
                    if isinstance(img, dict):
                        images = img.get('webImages', [])
            except:
                pass
            # Try standard.image.webImages
            if not images:
                try:
                    standard = data.get('standard')
                    if isinstance(standard, dict):
                        img = standard.get('image')
                        if isinstance(img, dict):
                            images = img.get('webImages', [])
                except:
                    pass
            # Try _links.image
            if not images:
                img_link = data.get('_links', {}).get('image', {})
                if isinstance(img_link, dict) and 'href' in img_link:
                    image_url = img_link['href'].replace('{width}', '960')
            for img in images:
                if isinstance(img, dict) and img.get('pixelWidth') == 960:
                    image_url = img.get('imageUrl')
                    break
            if not image_url and images and isinstance(images[-1], dict):
                image_url = images[-1].get('imageUrl')

            yaml_data = {
                'id': series_id,
                'title': series['title'],
                'description': data.get('titles', {}).get('subtitle') or series['description'],
                'nrk_url': f'https://tv.nrk.no/serie/{series_id}',
                'image_url': image_url,
                'program_type': 'serie',
                'episode_count': episode_count if episode_count > 0 else None,
                'interest_score': 75,
            }

        if series.get('person_id'):
            yaml_data['person_id'] = series['person_id']

        # Remove None values
        yaml_data = {k: v for k, v in yaml_data.items() if v is not None}

        save_yaml(out_path, yaml_data)

if __name__ == '__main__':
    import_about_programs()
    import_series_as_about_programs()
    print("\nDone! Run 'python3 scripts/build_database.py' to rebuild the database.")
