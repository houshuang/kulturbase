#!/usr/bin/env python3
"""
Import NRK Hørespill (radio plays) into Kulturperler archive.

This script:
1. Fetches all hørespill series from NRK's category page
2. Checks for duplicates against existing data
3. Creates new works, performances, and episodes
4. Fetches author bios from Norwegian Wikipedia
"""

import requests
import yaml
import re
import time
from pathlib import Path
from collections import defaultdict
from difflib import SequenceMatcher

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
PLAYS_DIR = DATA_DIR / 'plays'
PERSONS_DIR = DATA_DIR / 'persons'
PERFORMANCES_DIR = DATA_DIR / 'performances'
EPISODES_DIR = DATA_DIR / 'episodes'

# NRK API
NRK_BASE = "https://psapi.nrk.no"
WIKI_BASE = "https://no.wikipedia.org/api/rest_v1"
WIKI_HEADERS = {'User-Agent': 'Kulturperler/1.0 (https://kulturbase.no)'}

# Rate limiting
REQUEST_DELAY = 0.3


def load_yaml(path):
    """Load YAML file."""
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_yaml(path, data):
    """Save data to YAML file."""
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def load_existing_data():
    """Load all existing data for deduplication."""
    print("Loading existing data...")

    plays = {}
    for f in PLAYS_DIR.glob('*.yaml'):
        p = load_yaml(f)
        plays[p['id']] = p

    persons = {}
    for f in PERSONS_DIR.glob('*.yaml'):
        p = load_yaml(f)
        persons[p['id']] = p

    performances = {}
    for f in PERFORMANCES_DIR.glob('*.yaml'):
        p = load_yaml(f)
        performances[p['id']] = p

    episodes = set()
    for f in EPISODES_DIR.glob('*.yaml'):
        e = load_yaml(f)
        episodes.add(e.get('prf_id'))

    print(f"  Loaded {len(plays)} plays, {len(persons)} persons, {len(performances)} performances, {len(episodes)} episodes")
    return plays, persons, performances, episodes


def get_next_id(directory, pattern='*.yaml'):
    """Get next available ID for a directory."""
    max_id = 0
    for f in directory.glob(pattern):
        try:
            name = f.stem
            if name.isdigit():
                max_id = max(max_id, int(name))
        except ValueError:
            pass
    return max_id + 1


def normalize_title(title):
    """Normalize title for comparison."""
    if not title:
        return ""
    # Remove common prefixes
    title = re.sub(r'^(Radioteatret\s*[-:]\s*)', '', title, flags=re.IGNORECASE)
    # Lowercase and strip
    return title.lower().strip()


def similar_titles(t1, t2, threshold=0.85):
    """Check if two titles are similar enough to be duplicates."""
    n1, n2 = normalize_title(t1), normalize_title(t2)
    if not n1 or not n2:
        return False
    return SequenceMatcher(None, n1, n2).ratio() >= threshold


def find_duplicate_play(title, existing_plays):
    """Find if a play with similar title already exists."""
    for play_id, play in existing_plays.items():
        if similar_titles(title, play.get('title', '')):
            return play_id
    return None


def find_person_by_name(name, existing_persons):
    """Find person by name (case-insensitive)."""
    name_lower = name.lower().strip()
    for person_id, person in existing_persons.items():
        if person.get('name', '').lower().strip() == name_lower:
            return person_id
        if person.get('normalized_name', '').lower().strip() == name_lower:
            return person_id
    return None


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


def get_image_url(data, target_width=960):
    """Extract image URL from NRK API response."""
    if not data:
        return None

    image = data.get('image', {})

    # Handle case where image is a list directly
    if isinstance(image, list):
        web_images = image
    elif isinstance(image, dict):
        web_images = image.get('webImages', [])
    else:
        return None

    if not web_images:
        return None

    for img in web_images:
        if isinstance(img, dict):
            width = img.get('width') or img.get('pixelWidth')
            if width == target_width:
                return img.get('uri') or img.get('url') or img.get('imageUrl')

    # Fallback to largest
    if web_images and isinstance(web_images[-1], dict):
        return web_images[-1].get('uri') or web_images[-1].get('url') or web_images[-1].get('imageUrl')

    return None


def fetch_wikipedia_bio(name):
    """Fetch bio from Norwegian Wikipedia."""
    try:
        # URL encode the name
        encoded_name = requests.utils.quote(name)
        url = f"{WIKI_BASE}/page/summary/{encoded_name}"
        r = requests.get(url, headers=WIKI_HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return {
                'bio': data.get('extract', ''),
                'wikipedia_url': data.get('content_urls', {}).get('desktop', {}).get('page', '')
            }
    except Exception as e:
        print(f"    Wikipedia fetch failed for {name}: {e}")
    return {}


def fetch_horespill_page():
    """Fetch the hørespill category page from NRK."""
    print("Fetching hørespill category page...")
    url = f"{NRK_BASE}/radio/pages/hoerespill"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()


def extract_series_from_page(page_data):
    """Extract all series from the category page."""
    series_list = []
    seen_ids = set()

    sections = page_data.get('sections', [])
    for section in sections:
        included = section.get('included', {})
        plugs = included.get('plugs', [])

        for plug in plugs:
            plug_type = plug.get('type')

            if plug_type == 'series':
                series_link = plug.get('_links', {}).get('series', '')
                if series_link:
                    series_id = series_link.split('/')[-1]
                    if series_id and series_id not in seen_ids:
                        series_list.append({
                            'type': 'series',
                            'id': series_id,
                            'title': plug.get('series', {}).get('titles', {}).get('title', ''),
                            'image_url': get_image_url(plug.get('series', {}))
                        })
                        seen_ids.add(series_id)

            elif plug_type == 'standaloneProgram':
                program_link = plug.get('_links', {}).get('program', '')
                if program_link:
                    prf_id = program_link.split('/')[-1]
                    if prf_id and prf_id not in seen_ids:
                        series_list.append({
                            'type': 'standalone',
                            'id': prf_id,
                            'title': plug.get('program', {}).get('titles', {}).get('title', ''),
                            'description': plug.get('program', {}).get('titles', {}).get('subtitle', ''),
                            'image_url': get_image_url(plug.get('program', {})),
                            'duration': plug.get('program', {}).get('duration')
                        })
                        seen_ids.add(prf_id)

    print(f"  Found {len(series_list)} unique series/programs")
    return series_list


def fetch_series_details(series_id):
    """Fetch series details from NRK API."""
    # Try series endpoint first
    url = f"{NRK_BASE}/radio/catalog/series/{series_id}"
    r = requests.get(url, timeout=30)
    if r.status_code == 200:
        return r.json()

    # Try podcast endpoint as fallback
    url = f"{NRK_BASE}/radio/catalog/podcast/{series_id}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_program_details(prf_id):
    """Fetch standalone program details."""
    url = f"{NRK_BASE}/programs/{prf_id}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()


def identify_author(data):
    """Identify the author/playwright from series or program data."""
    contributors = data.get('contributors', [])

    # Look for playwright, author, or writer roles
    author_roles = ['forfatter', 'manusforfatter', 'dramatiker', 'dramatisering', 'av']

    for contrib in contributors:
        role = (contrib.get('role') or '').lower()
        if any(ar in role for ar in author_roles):
            return contrib.get('name')

    return None


def create_person(name, existing_persons):
    """Create a new person entry."""
    next_id = get_next_id(PERSONS_DIR)

    # Fetch Wikipedia bio
    wiki_data = fetch_wikipedia_bio(name)

    person = {
        'id': next_id,
        'name': name,
        'normalized_name': name.lower(),
    }

    if wiki_data.get('bio'):
        person['bio'] = wiki_data['bio']
    if wiki_data.get('wikipedia_url'):
        person['wikipedia_url'] = wiki_data['wikipedia_url']

    filepath = PERSONS_DIR / f"{next_id}.yaml"
    save_yaml(filepath, person)
    print(f"    Created person {next_id}: {name}")

    existing_persons[next_id] = person
    return next_id


def create_play(title, playwright_id, existing_plays, description=None):
    """Create a new play/work entry."""
    next_id = get_next_id(PLAYS_DIR)

    play = {
        'id': next_id,
        'title': title,
        'work_type': 'horespill',
        'category': 'teater',
    }

    if playwright_id:
        play['playwright_id'] = playwright_id

    if description:
        play['synopsis'] = description

    filepath = PLAYS_DIR / f"{next_id}.yaml"
    save_yaml(filepath, play)
    print(f"    Created work {next_id}: {title}")

    existing_plays[next_id] = play
    return next_id


def create_performance(work_id, title, year, series_id, image_url, existing_performances):
    """Create a new performance entry."""
    next_id = get_next_id(PERFORMANCES_DIR)

    perf = {
        'id': next_id,
        'work_id': work_id,
        'source': 'nrk',
        'medium': 'radio',
    }

    if title:
        perf['title'] = title
    if year:
        perf['year'] = year
    if series_id:
        perf['series_id'] = series_id
    if image_url:
        perf['image_url'] = image_url

    filepath = PERFORMANCES_DIR / f"{next_id}.yaml"
    save_yaml(filepath, perf)
    print(f"    Created performance {next_id}")

    existing_performances[next_id] = perf
    return next_id


def create_episode(prf_id, title, description, year, duration, image_url, nrk_url,
                   performance_id, series_id, existing_episodes):
    """Create a new episode entry."""
    if prf_id in existing_episodes:
        return False

    episode = {
        'prf_id': prf_id,
        'title': title or prf_id,
        'source': 'nrk',
        'medium': 'radio',
    }

    if description:
        episode['description'] = description
    if year:
        episode['year'] = year
    if duration:
        episode['duration_seconds'] = duration
    if image_url:
        episode['image_url'] = image_url
    if nrk_url:
        episode['nrk_url'] = nrk_url
    if performance_id:
        episode['performance_id'] = performance_id
    if series_id:
        episode['series_id'] = series_id

    filepath = EPISODES_DIR / f"{prf_id}.yaml"
    save_yaml(filepath, episode)
    print(f"      Created episode: {prf_id}")

    existing_episodes.add(prf_id)
    return True


def process_series(series_info, existing_plays, existing_persons, existing_performances, existing_episodes):
    """Process a series and create all necessary entries."""
    series_id = series_info['id']
    series_title = series_info.get('title', '')

    print(f"\nProcessing series: {series_id} - {series_title}")

    # Check if performance already exists for this series - if so, use its work
    existing_perf_for_series = None
    existing_work_from_perf = None
    for perf_id, perf in existing_performances.items():
        if perf.get('series_id') == series_id:
            existing_perf_for_series = perf_id
            if perf.get('work_id'):
                existing_work_from_perf = perf['work_id']
            break

    # Check for duplicate play by title (fallback)
    existing_play_id = existing_work_from_perf or find_duplicate_play(series_title, existing_plays)
    if existing_play_id:
        print(f"  Found existing work {existing_play_id}: {existing_plays.get(existing_play_id, {}).get('title', 'unknown')}")

    # Fetch full series details
    try:
        time.sleep(REQUEST_DELAY)
        details = fetch_series_details(series_id)
    except Exception as e:
        print(f"  ERROR fetching series: {e}")
        return 0

    # Get series metadata
    series_data = details.get('series', {})
    titles = series_data.get('titles', {})
    title = titles.get('title', series_title) or series_title
    description = titles.get('subtitle', '')
    image_url = get_image_url(series_data) or series_info.get('image_url')

    # Get episodes from embedded data or seasons
    episodes = []
    embedded = details.get('_embedded', {})

    # Try episodes directly
    if 'episodes' in embedded:
        eps_data = embedded['episodes']
        # Handle nested podcast structure: _embedded.episodes._embedded.episodes
        if isinstance(eps_data, dict) and '_embedded' in eps_data:
            episodes = eps_data['_embedded'].get('episodes', [])
        elif isinstance(eps_data, list):
            episodes = eps_data
    # Try seasons
    elif 'seasons' in embedded:
        for season in embedded['seasons']:
            season_eps = season.get('_embedded', {}).get('episodes', [])
            if not season_eps:
                season_eps = season.get('_embedded', {}).get('instalments', [])
            episodes.extend(season_eps)

    # Also check _links for seasons
    if not episodes:
        seasons_links = details.get('_links', {}).get('seasons', [])
        for season_link in seasons_links:
            season_name = season_link.get('name')
            if season_name:
                try:
                    time.sleep(REQUEST_DELAY)
                    # Try both series and podcast endpoints
                    for endpoint in ['series', 'podcast']:
                        season_url = f"{NRK_BASE}/radio/catalog/{endpoint}/{series_id}/seasons/{season_name}"
                        sr = requests.get(season_url, timeout=30)
                        if sr.status_code == 200:
                            season_data = sr.json()
                            # Handle nested structure
                            eps_container = season_data.get('_embedded', {}).get('episodes', {})
                            if isinstance(eps_container, dict) and '_embedded' in eps_container:
                                season_eps = eps_container['_embedded'].get('episodes', [])
                            elif isinstance(eps_container, list):
                                season_eps = eps_container
                            else:
                                season_eps = season_data.get('_embedded', {}).get('instalments', [])
                            if season_eps:
                                episodes.extend(season_eps)
                                break
                except Exception as e:
                    print(f"  Warning: couldn't fetch season {season_name}: {e}")

    if not episodes:
        print(f"  No episodes found")
        return 0

    print(f"  Found {len(episodes)} episodes")

    # Identify author
    author_name = identify_author(series_data)
    playwright_id = None

    if author_name:
        playwright_id = find_person_by_name(author_name, existing_persons)
        if not playwright_id:
            playwright_id = create_person(author_name, existing_persons)
        else:
            print(f"    Found existing author {playwright_id}: {author_name}")

    # Create or use existing play
    if existing_play_id:
        play_id = existing_play_id
    else:
        play_id = create_play(title, playwright_id, existing_plays, description)

    # Get year from first episode
    year = None
    if episodes:
        first_ep = episodes[0]
        if isinstance(first_ep, dict):
            release_date = first_ep.get('releaseDateOnDemand', '') or first_ep.get('date', '')
            if release_date and len(str(release_date)) >= 4:
                year = int(str(release_date)[:4])

    # Use the performance we found earlier, or create new
    if existing_perf_for_series:
        perf_id = existing_perf_for_series
        print(f"    Using existing performance {perf_id}")
    else:
        perf_id = create_performance(play_id, title, year, series_id, image_url, existing_performances)

    # Create episodes
    created_count = 0
    for ep in episodes:
        # Skip non-dict episodes
        if not isinstance(ep, dict):
            continue

        ep_id = ep.get('episodeId') or ep.get('prfId') or ep.get('id')
        if not ep_id:
            continue
        # Listener IDs (l_...) are valid - use them as episode IDs

        ep_titles = ep.get('titles', {})
        if isinstance(ep_titles, dict):
            ep_title = ep_titles.get('title', '')
            ep_desc = ep_titles.get('subtitle', '')
        else:
            ep_title = ''
            ep_desc = ''

        ep_duration = parse_duration(ep.get('duration'))
        ep_image = get_image_url(ep)

        # Get year
        ep_year = None
        ep_date = ep.get('releaseDateOnDemand', '') or ep.get('date', '')
        if ep_date and len(str(ep_date)) >= 4:
            ep_year = int(str(ep_date)[:4])

        # Generate appropriate NRK URL based on ID type
        if ep_id.startswith('l_'):
            nrk_url = f"https://radio.nrk.no/podkast/{series_id}/{ep_id}"
        else:
            nrk_url = f"https://radio.nrk.no/serie/{series_id}/{ep_id}"

        if create_episode(ep_id, ep_title, ep_desc, ep_year, ep_duration,
                         ep_image, nrk_url, perf_id, series_id, existing_episodes):
            created_count += 1

    return created_count


def process_standalone(program_info, existing_plays, existing_persons, existing_performances, existing_episodes):
    """Process a standalone program."""
    prf_id = program_info['id']
    title = program_info.get('title', '')

    print(f"\nProcessing standalone: {prf_id} - {title}")

    # Skip if already exists
    if prf_id in existing_episodes:
        print(f"  Already exists, skipping")
        return 0

    # Check for duplicate play
    existing_play_id = find_duplicate_play(title, existing_plays)

    # Fetch program details
    try:
        time.sleep(REQUEST_DELAY)
        details = fetch_program_details(prf_id)
    except Exception as e:
        print(f"  ERROR fetching program: {e}")
        return 0

    # Get metadata
    title = details.get('title', title) or title
    description = details.get('shortDescription', program_info.get('description', ''))
    duration = parse_duration(details.get('duration'))
    image_url = get_image_url(details) or program_info.get('image_url')

    # Get year
    year = details.get('productionYear')
    if not year:
        release_date = details.get('originallyPublishedAt', '')
        if release_date and len(str(release_date)) >= 4:
            year = int(str(release_date)[:4])

    # Identify author
    author_name = identify_author(details)
    playwright_id = None

    if author_name:
        playwright_id = find_person_by_name(author_name, existing_persons)
        if not playwright_id:
            playwright_id = create_person(author_name, existing_persons)

    # Create or use existing play
    if existing_play_id:
        play_id = existing_play_id
        print(f"  Using existing work {play_id}")
    else:
        play_id = create_play(title, playwright_id, existing_plays, description)

    # Create performance
    perf_id = create_performance(play_id, title, year, None, image_url, existing_performances)

    # Create episode
    nrk_url = f"https://radio.nrk.no/program/{prf_id}"
    if create_episode(prf_id, title, description, year, duration,
                     image_url, nrk_url, perf_id, None, existing_episodes):
        return 1

    return 0


def main():
    """Main execution."""
    print("="*60)
    print("NRK Hørespill Import")
    print("="*60)

    # Load existing data
    existing_plays, existing_persons, existing_performances, existing_episodes = load_existing_data()

    # Fetch category page
    page_data = fetch_horespill_page()

    # Extract all series and programs
    items = extract_series_from_page(page_data)

    # Process each item
    total_created = 0
    for item in items:
        try:
            if item['type'] == 'series':
                count = process_series(item, existing_plays, existing_persons,
                                       existing_performances, existing_episodes)
            else:
                count = process_standalone(item, existing_plays, existing_persons,
                                          existing_performances, existing_episodes)
            total_created += count

        except Exception as e:
            print(f"  ERROR processing {item['id']}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print(f"TOTAL: Created {total_created} new episodes")
    print(f"{'='*60}")
    print("\nRemember to run:")
    print("  python3 scripts/validate_data.py")
    print("  python3 scripts/build_database.py")


if __name__ == '__main__':
    main()
