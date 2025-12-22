#!/usr/bin/env python3
"""
Import YouTube concert recordings from Norwegian orchestras.

For each concert:
1. Parse title and description to extract composer, work, performers
2. Link to existing composers/works or create new ones
3. Create performance and episode entries
4. Link to orchestra institution
"""

import yaml
import json
import re
import os
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / 'data'
GEMINI_KEY = os.getenv('GEMINI_KEY')
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={GEMINI_KEY}"

# Orchestra info with Wikipedia URLs
ORCHESTRAS = {
    'Kristiansand Symfoniorkester': {
        'short_name': 'KSO',
        'location': 'Kristiansand',
        'wikipedia_url': 'https://no.wikipedia.org/wiki/Kristiansand_Symfoniorkester',
    },
    'Oslo-Filharmonien': {
        'short_name': 'OFO',
        'location': 'Oslo',
        'wikipedia_url': 'https://no.wikipedia.org/wiki/Oslo-Filharmonien',
    },
    'Stavanger Symfoniorkester': {
        'short_name': 'SSO',
        'location': 'Stavanger',
        'wikipedia_url': 'https://no.wikipedia.org/wiki/Stavanger_symfoniorkester',
    },
    'Trondheim Symfoniorkester': {
        'short_name': 'TSO',
        'location': 'Trondheim',
        'wikipedia_url': 'https://no.wikipedia.org/wiki/Trondheim_Symfoniorkester',
    },
    'Arktisk Filharmoni': {
        'short_name': 'AF',
        'location': 'Tromsø/Bodø',
        'wikipedia_url': 'https://no.wikipedia.org/wiki/Arktisk_Filharmoni',
    },
    'Det Norske Kammerorkester': {
        'short_name': 'DNK',
        'location': 'Oslo',
        'wikipedia_url': 'https://no.wikipedia.org/wiki/Det_Norske_Kammerorkester',
    },
    'Den Norske Opera & Ballett': {
        'short_name': 'DNO',
        'location': 'Oslo',
        'wikipedia_url': 'https://no.wikipedia.org/wiki/Den_Norske_Opera_%26_Ballett',
        'type': 'opera_house',
    },
    'Telemark Symfoniorkester': {
        'short_name': 'TESO',
        'location': 'Skien',
        'wikipedia_url': None,
    },
    'Oslo Sinfonietta': {
        'short_name': 'OSIN',
        'location': 'Oslo',
        'wikipedia_url': 'https://no.wikipedia.org/wiki/Oslo_Sinfonietta',
    },
    'Trondheimsolistene': {
        'short_name': 'TS',
        'location': 'Trondheim',
        'wikipedia_url': 'https://no.wikipedia.org/wiki/TrondheimSolistene',
    },
    'Oslo Camerata': {
        'short_name': 'OC',
        'location': 'Oslo',
        'wikipedia_url': None,
    },
    'Ensemble Allegria': {
        'short_name': 'EA',
        'location': 'Oslo',
        'wikipedia_url': 'https://no.wikipedia.org/wiki/Ensemble_Allegria',
    },
}


def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_yaml(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def call_gemini(prompt):
    """Call Gemini 3 Flash API."""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1}
    }
    try:
        r = requests.post(GEMINI_URL, json=payload, timeout=30)
        if r.status_code == 200:
            data = r.json()
            return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"  Gemini error: {e}")
    return None


def get_next_id(directory):
    """Find next available ID in a directory."""
    max_id = 0
    for f in (DATA_DIR / directory).glob('*.yaml'):
        try:
            stem = f.stem
            if stem.isdigit():
                max_id = max(max_id, int(stem))
        except:
            pass
    return max_id + 1


def create_institutions():
    """Create institution entries for orchestras."""
    institutions_dir = DATA_DIR / 'institutions'
    institutions_dir.mkdir(exist_ok=True)

    # Load existing institutions
    existing = {}
    for f in institutions_dir.glob('*.yaml'):
        inst = load_yaml(f)
        if inst:
            existing[inst.get('name')] = inst['id']

    next_id = get_next_id('institutions')
    institution_ids = {}

    for name, info in ORCHESTRAS.items():
        if name in existing:
            institution_ids[name] = existing[name]
            print(f"  Existing institution: [{existing[name]}] {name}")
            continue

        inst = {
            'id': next_id,
            'name': name,
            'short_name': info['short_name'],
            'type': info.get('type', 'orchestra'),
            'location': info['location'],
        }
        if info.get('wikipedia_url'):
            inst['wikipedia_url'] = info['wikipedia_url']

        save_yaml(institutions_dir / f'{next_id}.yaml', inst)
        print(f"  Created institution: [{next_id}] {name}")
        institution_ids[name] = next_id
        next_id += 1

    return institution_ids


def normalize_name(name):
    """Normalize a name for matching."""
    if not name:
        return ''
    # Remove parenthetical info, clean up
    name = re.sub(r'\s*\([^)]*\)', '', name)
    name = re.sub(r'\s*\[[^\]]*\]', '', name)
    return name.strip().lower()


def find_person_by_name(name, persons_cache):
    """Find a person by name in the cache."""
    norm_name = normalize_name(name)
    if not norm_name:
        return None

    # Exact match
    if norm_name in persons_cache:
        return persons_cache[norm_name]

    # Try last name match for composers
    parts = norm_name.split()
    if len(parts) >= 1:
        last_name = parts[-1]
        for cached_name, pid in persons_cache.items():
            if cached_name.endswith(last_name) and len(cached_name.split()) > 1:
                # Verify first name initial matches if we have it
                if len(parts) >= 2:
                    first_initial = parts[0][0] if parts[0] else ''
                    cached_first = cached_name.split()[0][0] if cached_name.split()[0] else ''
                    if first_initial == cached_first:
                        return pid
                else:
                    return pid

    return None


def load_persons_cache():
    """Load all persons into a name->id cache."""
    cache = {}
    for f in (DATA_DIR / 'persons').glob('*.yaml'):
        p = load_yaml(f)
        if p:
            name = p.get('name', '')
            norm = normalize_name(name)
            if norm:
                cache[norm] = p['id']
            # Also add normalized_name if different
            norm2 = p.get('normalized_name', '')
            if norm2 and norm2 != norm:
                cache[norm2] = p['id']
    return cache


def load_works_cache():
    """Load works into a title->id cache."""
    cache = {}
    for f in (DATA_DIR / 'plays').glob('*.yaml'):
        w = load_yaml(f)
        if w:
            title = w.get('title', '').lower()
            if title:
                cache[title] = {'id': w['id'], 'composer_id': w.get('composer_id')}
            orig = w.get('original_title', '').lower()
            if orig and orig != title:
                cache[orig] = {'id': w['id'], 'composer_id': w.get('composer_id')}
    return cache


def parse_concert_info(concert):
    """Parse concert title and description to extract structured info."""
    title = concert.get('title', '')
    desc = concert.get('description', '')

    # Try to extract composer from title pattern "Composer: Work..."
    composer_match = re.match(r'^([^:]+):\s*(.+?)(?:\s*-\s*|\s*\|)', title)

    info = {
        'composer': None,
        'work_title': None,
        'conductor': None,
        'soloists': [],
        'concertmaster': None,
    }

    if composer_match:
        info['composer'] = composer_match.group(1).strip()
        info['work_title'] = composer_match.group(2).strip()

    # Parse description for more details
    lines = desc.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Match "Role: Name" patterns
        if line.startswith('Composer:'):
            info['composer'] = line.replace('Composer:', '').strip()
        elif line.startswith('Conductor:'):
            info['conductor'] = line.replace('Conductor:', '').strip()
        elif line.startswith('Concertmaster:'):
            info['concertmaster'] = line.replace('Concertmaster:', '').strip()
        elif any(line.startswith(f'{role}:') for role in ['Violin', 'Piano', 'Cello', 'Viola', 'Soprano', 'Alto', 'Tenor', 'Bass', 'Soloist', 'Flute', 'Clarinet', 'Oboe', 'Horn', 'Trumpet']):
            parts = line.split(':', 1)
            if len(parts) == 2:
                role = parts[0].strip()
                name = parts[1].strip()
                if name:
                    info['soloists'].append({'role': role, 'name': name})
        elif 'Solo' in line and ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2:
                role = parts[0].strip()
                name = parts[1].strip()
                if name:
                    info['soloists'].append({'role': role, 'name': name})

    return info


def create_or_find_person(name, persons_cache, next_person_id):
    """Find existing person or create new one."""
    if not name:
        return None, next_person_id, False

    # Clean up name
    name = re.sub(r'\s*\([^)]*\)', '', name).strip()
    name = re.sub(r'\s*\d+y\s*$', '', name).strip()  # Remove age like "17y"

    pid = find_person_by_name(name, persons_cache)
    if pid:
        return pid, next_person_id, False

    # Create new person
    person = {
        'id': next_person_id,
        'name': name,
        'normalized_name': name.lower(),
    }
    save_yaml(DATA_DIR / 'persons' / f'{next_person_id}.yaml', person)

    # Update cache
    persons_cache[name.lower()] = next_person_id

    return next_person_id, next_person_id + 1, True


def create_work(title, composer_id, work_type, next_work_id):
    """Create a new work entry."""
    work = {
        'id': next_work_id,
        'title': title,
        'category': 'konsert',
        'type': work_type,
    }
    if composer_id:
        work['composer_id'] = composer_id

    save_yaml(DATA_DIR / 'plays' / f'{next_work_id}.yaml', work)
    return next_work_id


def determine_work_type(title, description):
    """Determine the type of work from title/description."""
    text = (title + ' ' + description).lower()

    if 'symphony' in text or 'symfoni' in text or 'sinfonie' in text:
        return 'symphony'
    elif 'concerto' in text or 'konsert' in text:
        return 'concerto'
    elif 'opera' in text:
        return 'opera'
    elif 'ballet' in text or 'ballett' in text:
        return 'ballet'
    elif 'quartet' in text or 'quintet' in text or 'trio' in text or 'sonata' in text:
        return 'chamber'
    elif 'overture' in text or 'ouverture' in text:
        return 'orchestral'
    elif 'suite' in text:
        return 'orchestral'
    else:
        return 'orchestral'


def main():
    print("Importing YouTube concert recordings...")

    # Load concerts data
    with open('/tmp/norwegian_orchestras_concerts.yaml') as f:
        data = yaml.safe_load(f)

    concerts = data['concerts']
    print(f"Loaded {len(concerts)} concerts")

    # Create institutions
    print("\nCreating institutions...")
    institution_ids = create_institutions()

    # Load caches
    print("\nLoading existing data...")
    persons_cache = load_persons_cache()
    works_cache = load_works_cache()
    print(f"  {len(persons_cache)} persons, {len(works_cache)} works")

    # Get next IDs
    next_person_id = get_next_id('persons')
    next_work_id = get_next_id('plays')
    next_perf_id = get_next_id('performances')
    next_episode_id = get_next_id('episodes')

    # Track statistics
    stats = {
        'concerts_processed': 0,
        'persons_created': 0,
        'works_created': 0,
        'works_linked': 0,
        'performances_created': 0,
        'episodes_created': 0,
    }

    # Process concerts
    print("\nProcessing concerts...")
    for i, concert in enumerate(concerts):
        if i % 100 == 0:
            print(f"  Processing {i}/{len(concerts)}...")

        youtube_id = concert['youtube_id']
        orchestra = concert['orchestra']

        # Skip if already imported (check by youtube_id in episode prf_id)
        episode_file = DATA_DIR / 'episodes' / f'YT_{youtube_id}.yaml'
        if episode_file.exists():
            continue

        # Parse concert info
        info = parse_concert_info(concert)

        # Find or create composer
        composer_id = None
        if info['composer']:
            composer_id, next_person_id, created = create_or_find_person(
                info['composer'], persons_cache, next_person_id
            )
            if created:
                stats['persons_created'] += 1

        # Find or create work
        work_id = None
        work_title = info['work_title'] or concert['title'].split(' - ')[0]
        work_type = determine_work_type(work_title, concert.get('description', ''))

        # Try to find existing work
        work_key = work_title.lower()
        if work_key in works_cache:
            work_id = works_cache[work_key]['id']
            stats['works_linked'] += 1
        else:
            # Create new work
            work_id = create_work(work_title, composer_id, work_type, next_work_id)
            works_cache[work_key] = {'id': work_id, 'composer_id': composer_id}
            next_work_id += 1
            stats['works_created'] += 1

        # Create performance
        perf_credits = []

        # Add conductor
        if info['conductor']:
            cond_id, next_person_id, created = create_or_find_person(
                info['conductor'], persons_cache, next_person_id
            )
            if created:
                stats['persons_created'] += 1
            if cond_id:
                perf_credits.append({'person_id': cond_id, 'role': 'conductor'})

        # Add soloists
        for soloist in info['soloists']:
            sol_id, next_person_id, created = create_or_find_person(
                soloist['name'], persons_cache, next_person_id
            )
            if created:
                stats['persons_created'] += 1
            if sol_id:
                perf_credits.append({
                    'person_id': sol_id,
                    'role': 'soloist',
                    'instrument': soloist['role']
                })

        # Add composer credit
        if composer_id:
            perf_credits.append({'person_id': composer_id, 'role': 'composer'})

        performance = {
            'id': next_perf_id,
            'work_id': work_id,
            'source': 'youtube',
            'medium': 'stream',
            'title': concert['title'],
            'credits': perf_credits,
            'institutions': [{'institution_id': institution_ids[orchestra], 'role': 'orchestra'}],
        }

        # Extract year from upload date
        if concert.get('upload_date'):
            try:
                year = int(concert['upload_date'][:4])
                performance['year'] = year
            except:
                pass

        save_yaml(DATA_DIR / 'performances' / f'{next_perf_id}.yaml', performance)
        stats['performances_created'] += 1

        # Create episode
        episode = {
            'prf_id': f'YT_{youtube_id}',
            'title': concert['title'],
            'performance_id': next_perf_id,
            'source': 'youtube',
            'medium': 'stream',
            'duration_seconds': concert.get('duration_seconds'),
            'youtube_url': concert['url'],
            'image_url': concert.get('thumbnail'),
        }

        if concert.get('description'):
            episode['description'] = concert['description'][:500]  # Truncate long descriptions

        if concert.get('upload_date'):
            try:
                episode['year'] = int(concert['upload_date'][:4])
            except:
                pass

        save_yaml(DATA_DIR / 'episodes' / f'YT_{youtube_id}.yaml', episode)
        stats['episodes_created'] += 1

        next_perf_id += 1
        stats['concerts_processed'] += 1

    print("\n\nResults:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == '__main__':
    main()
