#!/usr/bin/env python3
"""
Import radio theatre from Sveriges Radio.

Uses the SR API to fetch drama programs and creates YAML files.
All content is in Swedish (language: sv).

SR Drama Programs:
- 4453: Dramaklassiker (111 episodes) - Classic radio theatre
- 3171: Drama för unga (164 episodes) - Children's drama
- 4976: Sveriges Radio Drama (19 episodes) - Contemporary drama
- 6605: Scenen – Shakespeare (19 episodes) - Shakespeare adaptations
- 4947: P3 Serie (60 episodes) - Crime/thriller series
"""

import requests
import yaml
import re
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict

DATA_DIR = Path(__file__).parent.parent / 'data'
EPISODES_DIR = DATA_DIR / 'episodes'
PERFORMANCES_DIR = DATA_DIR / 'performances'
WORKS_DIR = DATA_DIR / 'plays'  # Works are stored in plays/ directory

# SR API base URL
SR_API = 'https://api.sr.se/api/v2'

# Programs to import
SR_PROGRAMS = {
    4453: {'name': 'Dramaklassiker', 'category': 'teater', 'work_type': 'teaterstykke'},
    3171: {'name': 'Drama för unga', 'category': 'teater', 'work_type': 'barneteater'},
    4976: {'name': 'Sveriges Radio Drama', 'category': 'teater', 'work_type': 'teaterstykke'},
    6605: {'name': 'Scenen', 'category': 'teater', 'work_type': 'teaterstykke'},
    4947: {'name': 'P3 Serie', 'category': 'dramaserie', 'work_type': 'dramaserie'},
}

# Known playwrights to match (name -> person_id in our database)
# Will be populated from database
KNOWN_PLAYWRIGHTS = {}


def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_yaml(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def get_next_id(directory, prefix=''):
    """Get the next available ID from a directory of YAML files."""
    max_id = 0
    for f in directory.glob('*.yaml'):
        try:
            if prefix:
                # For episodes with prefix like SR_
                continue
            id_str = f.stem
            if id_str.isdigit():
                max_id = max(max_id, int(id_str))
        except ValueError:
            continue
    return max_id + 1


def load_existing_persons():
    """Load all persons from database to enable playwright matching."""
    persons = {}
    for f in (DATA_DIR / 'persons').glob('*.yaml'):
        p = load_yaml(f)
        name_lower = p['name'].lower()
        persons[name_lower] = p['id']
        # Also add normalized name
        if p.get('normalized_name'):
            persons[p['normalized_name']] = p['id']
    return persons


def load_existing_works():
    """Load all works to check for duplicates."""
    works = {}
    for f in WORKS_DIR.glob('*.yaml'):
        w = load_yaml(f)
        # Key by title (lowercase) and playwright_id
        key = (w['title'].lower(), w.get('playwright_id'))
        works[key] = w
        # Also key by just title
        works[w['title'].lower()] = w
    return works


def load_existing_episodes():
    """Load existing episode IDs."""
    episodes = set()
    for f in EPISODES_DIR.glob('*.yaml'):
        e = load_yaml(f)
        episodes.add(e['prf_id'])
    return episodes


def parse_sr_date(date_str):
    """Parse SR's weird /Date(timestamp)/ format."""
    if not date_str:
        return None
    match = re.search(r'/Date\((\d+)\)/', date_str)
    if match:
        timestamp = int(match.group(1)) / 1000
        return datetime.fromtimestamp(timestamp)
    return None


def parse_title_and_author(title):
    """
    Parse episode title to extract work title and author.

    Examples:
    - "Kronbruden av August Strindberg" -> ("Kronbruden", "August Strindberg")
    - "Hamlet, del 1" -> ("Hamlet", None)
    - "En dörr skall vara öppen eller stängd av Alfred de Musset" -> (...)
    - "Lysande utsikter av Charles Dickens. | Del 9" -> ("Lysande utsikter", "Charles Dickens")
    """
    # Clean up title - remove " | Del N" suffix
    title = re.sub(r'\s*\|\s*[Dd]el\s*\d+$', '', title)

    # Pattern: "Title av Author" with optional trailing punctuation
    match = re.match(r'^(.+?)\s+av\s+([^|]+?)\.?(?:\s*[,\-–]\s*[Dd]el\s*\d+)?$', title, re.IGNORECASE)
    if match:
        return match.group(1).strip(), match.group(2).strip().rstrip('.')

    # Pattern: "Title, del N" or "Title - del N" (no author)
    match = re.match(r'^(.+?)\s*[,\-–]\s*[Dd]el\s*\d+', title, re.IGNORECASE)
    if match:
        return match.group(1).strip(), None

    # Pattern: "Title del N" (no comma)
    match = re.match(r'^(.+?)\s+[Dd]el\s+\d+$', title, re.IGNORECASE)
    if match:
        return match.group(1).strip(), None

    return title, None


def parse_p3_serie_title(title):
    """
    Parse P3 Serie episode titles.

    Format: "Episode title – Series name" or "Episode title – Series name, del N"
    OR: "Series name, del N" (standalone series without episode titles)

    Examples:
    - "Mytens kraft – Barnmördarkorset, del 5" -> ("Barnmördarkorset", "Mytens kraft", 5)
    - "Sista natten – VOX, del 5" -> ("VOX", "Sista natten", 5)
    - "Cold Case: Mörkt hav, del 1" -> ("Cold Case: Mörkt hav", None, 1)
    - "Arvet, del 5" -> ("Arvet", None, 5)
    """
    # Pattern: "Episode – Series, del N"
    match = re.match(r'^(.+?)\s*[–-]\s*(.+?),?\s*[Dd]el\s*(\d+)$', title)
    if match:
        return match.group(2).strip(), match.group(1).strip(), int(match.group(3))

    # Pattern: "Episode – Series" (no part number)
    match = re.match(r'^(.+?)\s*[–-]\s*(.+?)$', title)
    if match:
        # Make sure it's not a subtitle pattern like "Cold Case: Mörkt hav"
        series = match.group(2).strip()
        episode = match.group(1).strip()
        # If series is very long or episode is very short, probably not a series pattern
        if len(series) < 40 and len(episode) > 3:
            return series, episode, None

    # Pattern: "Series, del N" (no episode title, just series with part number)
    match = re.match(r'^(.+?),?\s*[Dd]el\s*(\d+)$', title)
    if match:
        return match.group(1).strip(), None, int(match.group(2))

    # Pattern: "Series del N av M" (part N of M)
    match = re.match(r'^(.+?)\s+[Dd]el\s*(\d+)\s+av\s+\d+$', title)
    if match:
        return match.group(1).strip(), None, int(match.group(2))

    return title, None, None


def is_trailer_or_extra(title):
    """Check if this is a trailer or extra material that should be skipped."""
    lower = title.lower()
    skip_patterns = [
        'trailer:',
        'trailer ',
        'poddtips:',
        'extramaterial:',
        '| radioteatern 100 år',
        'radioteatern 100 år',
        'inledning till',
        'intervju med',
    ]
    return any(p in lower for p in skip_patterns)


def parse_episode_number(title):
    """Extract episode/part number from title."""
    match = re.search(r'del\s*(\d+)', title, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def find_playwright(author_name, persons):
    """Find playwright ID by name."""
    if not author_name:
        return None

    name_lower = author_name.lower()

    # Direct match
    if name_lower in persons:
        return persons[name_lower]

    # Try last name only (e.g., "Strindberg" for "August Strindberg")
    parts = author_name.split()
    if len(parts) > 1:
        last_name = parts[-1].lower()
        for pname, pid in persons.items():
            if last_name in pname:
                return pid

    return None


def fetch_sr_episodes(program_id):
    """Fetch all episodes for a program from SR API."""
    url = f'{SR_API}/episodes/index'
    params = {
        'programid': program_id,
        'format': 'json',
        'pagination': 'false'
    }

    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()

    episodes = data.get('episodes', [])
    if isinstance(episodes, dict):
        episodes = episodes.get('episode', [])

    return episodes


def group_episodes_by_work(episodes, is_p3_serie=False):
    """
    Group episodes that belong to the same work (multi-part productions).

    Returns dict: work_title -> list of episodes
    """
    groups = defaultdict(list)

    for ep in episodes:
        title = ep.get('title', '')

        # Skip trailers and extras
        if is_trailer_or_extra(title):
            continue

        if is_p3_serie:
            # P3 Serie has different format: "Episode – Series"
            series_name, episode_title, part_num = parse_p3_serie_title(title)
            work_title = series_name
            author = None
            part_number = part_num
        else:
            work_title, author = parse_title_and_author(title)
            part_number = parse_episode_number(title)

        # Create a group key
        key = work_title.lower()
        groups[key].append({
            'episode': ep,
            'work_title': work_title,
            'author': author,
            'part_number': part_number,
            'episode_title': episode_title if is_p3_serie else None,
        })

    return groups


def import_program(program_id, program_info, persons, existing_works, existing_episodes, dry_run=False):
    """Import a single SR program."""
    print(f"\n{'='*60}")
    print(f"Importing: {program_info['name']} (ID: {program_id})")
    print(f"{'='*60}")

    episodes = fetch_sr_episodes(program_id)
    print(f"Found {len(episodes)} episodes")

    # Group by work
    # P3 Serie and Drama för unga have similar "Episode – Series" title format
    uses_series_format = program_id in (4947, 3171)
    groups = group_episodes_by_work(episodes, is_p3_serie=uses_series_format)
    print(f"Grouped into {len(groups)} distinct works (after filtering trailers/extras)")

    # Get next IDs
    next_work_id = get_next_id(WORKS_DIR)
    next_perf_id = get_next_id(PERFORMANCES_DIR)

    stats = {
        'works_created': 0,
        'works_linked': 0,
        'performances_created': 0,
        'episodes_created': 0,
        'episodes_skipped': 0,
    }

    for work_key, group_episodes in groups.items():
        # Get work info from first episode
        first_ep = group_episodes[0]
        work_title = first_ep['work_title']
        author = first_ep['author']

        # Sort by part number
        group_episodes.sort(key=lambda x: x['part_number'] or 0)

        # Try to find existing work
        playwright_id = find_playwright(author, persons)
        existing_work = None

        # Check by title + playwright
        work_lookup_key = (work_title.lower(), playwright_id)
        if work_lookup_key in existing_works:
            existing_work = existing_works[work_lookup_key]
            stats['works_linked'] += 1
            print(f"  Linked to existing work: {existing_work['title']} (ID: {existing_work['id']})")
        elif work_title.lower() in existing_works:
            existing_work = existing_works[work_title.lower()]
            stats['works_linked'] += 1
            print(f"  Linked to existing work by title: {existing_work['title']} (ID: {existing_work['id']})")

        # Create work if needed
        if existing_work:
            work_id = existing_work['id']
        else:
            work_id = next_work_id
            next_work_id += 1

            work_data = {
                'id': work_id,
                'title': work_title,
                'language': 'sv',
                'category': program_info['category'],
                'work_type': program_info['work_type'],
            }
            if playwright_id:
                work_data['playwright_id'] = playwright_id

            if not dry_run:
                save_yaml(WORKS_DIR / f'{work_id}.yaml', work_data)

            stats['works_created'] += 1
            author_str = f" by {author}" if author else ""
            print(f"  Created work: {work_title}{author_str} (ID: {work_id})")

        # Create performance (groups all episodes of this work from SR)
        perf_id = next_perf_id
        next_perf_id += 1

        # Calculate total duration
        total_duration = 0
        for ge in group_episodes:
            ep = ge['episode']
            pod = ep.get('listenpodfile') or ep.get('downloadpodfile') or {}
            total_duration += pod.get('duration', 0)

        # Get year from first episode
        first_raw_ep = group_episodes[0]['episode']
        pub_date = parse_sr_date(first_raw_ep.get('publishdateutc'))
        year = pub_date.year if pub_date else None

        perf_data = {
            'id': perf_id,
            'work_id': work_id,
            'source': 'sr',
            'language': 'sv',
            'medium': 'radio',
            'year': year,
            'title': f"{work_title} - {program_info['name']}",
            'image_url': first_raw_ep.get('imageurl'),
        }
        if total_duration > 0:
            perf_data['total_duration'] = total_duration

        if not dry_run:
            save_yaml(PERFORMANCES_DIR / f'{perf_id}.yaml', perf_data)

        stats['performances_created'] += 1

        # Create episodes
        for i, ge in enumerate(group_episodes):
            ep = ge['episode']
            ep_id = f"SR_{ep['id']}"

            # Skip if already exists
            if ep_id in existing_episodes:
                stats['episodes_skipped'] += 1
                continue

            pod = ep.get('listenpodfile') or ep.get('downloadpodfile') or {}
            pub_date = parse_sr_date(ep.get('publishdateutc'))

            ep_data = {
                'prf_id': ep_id,
                'title': ep.get('title', ''),
                'description': ep.get('description'),
                'performance_id': perf_id,
                'work_id': work_id,
                'source': 'sr',
                'language': 'sv',
                'medium': 'radio',
                'year': pub_date.year if pub_date else None,
                'duration_seconds': pod.get('duration'),
                'image_url': ep.get('imageurl'),
                'sr_url': ep.get('url'),
            }

            # Add episode number if multi-part
            if len(group_episodes) > 1:
                ep_data['episode_number'] = ge['part_number'] or (i + 1)

            if not dry_run:
                save_yaml(EPISODES_DIR / f'{ep_id}.yaml', ep_data)

            stats['episodes_created'] += 1
            existing_episodes.add(ep_id)

    return stats


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Import Sveriges Radio drama programs')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be imported without writing files')
    parser.add_argument('--program', type=int, help='Import only specific program ID')
    args = parser.parse_args()

    print("Loading existing data...")
    persons = load_existing_persons()
    print(f"  Loaded {len(persons)} person name mappings")

    existing_works = load_existing_works()
    print(f"  Loaded {len(existing_works)} existing works")

    existing_episodes = load_existing_episodes()
    print(f"  Loaded {len(existing_episodes)} existing episodes")

    # Select programs to import
    programs = SR_PROGRAMS
    if args.program:
        if args.program not in SR_PROGRAMS:
            print(f"Unknown program ID: {args.program}")
            print(f"Available: {list(SR_PROGRAMS.keys())}")
            return
        programs = {args.program: SR_PROGRAMS[args.program]}

    total_stats = defaultdict(int)

    for prog_id, prog_info in programs.items():
        stats = import_program(prog_id, prog_info, persons, existing_works, existing_episodes, dry_run=args.dry_run)
        for k, v in stats.items():
            total_stats[k] += v
        time.sleep(1)  # Be nice to the API

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for k, v in total_stats.items():
        print(f"  {k}: {v}")

    if args.dry_run:
        print("\n[DRY RUN - no files written]")
    else:
        print("\nDone! Remember to run: python3 scripts/build_database.py")


if __name__ == '__main__':
    main()
