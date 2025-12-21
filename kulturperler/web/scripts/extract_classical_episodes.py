#!/usr/bin/env python3
"""
Phase 2: Extract all episodes from discovered classical music series.

Fetches all seasons and episodes, extracts full metadata, filters by expiry and duration.
Outputs: output/classical_episodes_raw.json
"""

import requests
import json
import time
import re
from pathlib import Path
from datetime import datetime, timedelta, timezone

OUTPUT_DIR = Path(__file__).parent.parent / "output"
INPUT_FILE = OUTPUT_DIR / "classical_series_discovered.json"
OUTPUT_FILE = OUTPUT_DIR / "classical_episodes_raw.json"

HEADERS = {'User-Agent': 'Kulturperler/1.0 (educational project)'}

# Minimum duration in seconds (25 minutes)
MIN_DURATION_SECONDS = 25 * 60

# Expiry threshold (1 year from now) - timezone aware
EXPIRY_THRESHOLD = datetime.now(timezone.utc) + timedelta(days=365)


def parse_iso_duration(duration_str):
    """Parse ISO 8601 duration (e.g., PT1H30M45S) to seconds."""
    if not duration_str:
        return 0

    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?', duration_str)
    if match:
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = float(match.group(3) or 0)
        return int(hours * 3600 + minutes * 60 + seconds)
    return 0


def parse_expiry_date(usage_rights):
    """Extract expiry date from usage rights."""
    if not usage_rights:
        return None, None

    # ISO8601 format in nested structure
    to_info = usage_rights.get('to', {})
    if isinstance(to_info, dict):
        to_date = to_info.get('date')
        if to_date:
            try:
                # Handle timezone offset
                to_date = to_date.replace('Z', '+00:00')
                expiry = datetime.fromisoformat(to_date)
                return expiry, to_info.get('displayValue', '')
            except:
                pass

    # Unix timestamp format /Date(1234567890000+0000)/
    available_to = usage_rights.get('availableTo', '')
    if available_to and 'Date(' in str(available_to):
        try:
            ms = int(str(available_to).split('(')[1].split('+')[0])
            expiry = datetime.fromtimestamp(ms / 1000)
            return expiry, available_to
        except:
            pass

    return None, None


def is_available_long_term(expiry_date):
    """Check if content is available for 1+ year."""
    if expiry_date is None:
        return True  # Assume available if no expiry info
    # Make timezone-aware if needed
    if expiry_date.tzinfo is None:
        expiry_date = expiry_date.replace(tzinfo=timezone.utc)
    return expiry_date > EXPIRY_THRESHOLD


def get_tv_series_seasons(series_id):
    """Get all seasons for a TV series."""
    url = f"https://psapi.nrk.no/tv/catalog/series/{series_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.ok:
            data = resp.json()
            nav = data.get('navigation', {})
            seasons = []
            for section in nav.get('sections', []):
                if section.get('type') == 'subnavigation':
                    for sub in section.get('sections', []):
                        if sub.get('type') == 'season':
                            seasons.append(sub.get('id'))
            return seasons
    except Exception as e:
        print(f"    Error fetching seasons for '{series_id}': {e}")
    return []


def get_tv_season_episodes(series_id, season_id):
    """Get all episodes from a TV series season."""
    url = f"https://psapi.nrk.no/tv/catalog/series/{series_id}/seasons/{season_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.ok:
            data = resp.json()
            embedded = data.get('_embedded', {})
            return embedded.get('instalments', [])
    except Exception as e:
        print(f"    Error fetching season '{season_id}': {e}")
    return []


def get_radio_series_seasons(series_id):
    """Get all seasons for a radio series."""
    url = f"https://psapi.nrk.no/radio/catalog/series/{series_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.ok:
            data = resp.json()
            embedded = data.get('_embedded', {})
            seasons = embedded.get('seasons', [])
            return [s.get('id') for s in seasons if s.get('id')]
    except Exception as e:
        print(f"    Error fetching radio seasons for '{series_id}': {e}")
    return []


def get_radio_season_episodes(series_id, season_id):
    """Get all episodes from a radio series season."""
    url = f"https://psapi.nrk.no/radio/catalog/series/{series_id}/seasons/{season_id}/episodes"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.ok:
            data = resp.json()
            embedded = data.get('_embedded', {})
            return embedded.get('episodes', [])
    except Exception as e:
        print(f"    Error fetching radio season '{season_id}': {e}")
    return []


def get_program_details(program_id):
    """Get detailed info for a single program."""
    url = f"https://psapi.nrk.no/programs/{program_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.ok:
            return resp.json()
    except:
        pass
    return None


def extract_episode_info(episode_data, series_id, series_title, medium='tv'):
    """Extract episode info from API response."""
    prf_id = episode_data.get('prfId') or episode_data.get('id', '')
    titles = episode_data.get('titles', {})
    if isinstance(titles, dict):
        title = titles.get('title', '')
        subtitle = titles.get('subtitle', '')
    else:
        title = episode_data.get('title', '')
        subtitle = episode_data.get('description', '')

    # Duration
    duration = episode_data.get('durationInSeconds', 0)
    if not duration:
        duration = parse_iso_duration(episode_data.get('duration', ''))

    # Expiry
    usage_rights = episode_data.get('usageRights', {})
    expiry_date, expiry_display = parse_expiry_date(usage_rights)

    # Year
    year = episode_data.get('productionYear')
    if not year:
        release_date = episode_data.get('releaseDateOnDemand', '')
        if release_date:
            match = re.search(r'(\d{4})', release_date)
            if match:
                year = int(match.group(1))

    # Image
    images = episode_data.get('image', [])
    if isinstance(images, list) and images:
        image_url = max(images, key=lambda x: x.get('width', 0)).get('url', '')
    elif isinstance(images, dict):
        web_images = images.get('webImages', [])
        if web_images:
            image_url = max(web_images, key=lambda x: x.get('pixelWidth', 0)).get('imageUrl', '')
        else:
            image_url = ''
    else:
        image_url = ''

    # Contributors
    contributors = []
    for c in episode_data.get('contributors', []):
        contributors.append({
            'name': c.get('name', ''),
            'role': c.get('role', ''),
        })

    # Availability
    availability = episode_data.get('availability', {})

    return {
        'prf_id': prf_id,
        'title': title,
        'subtitle': subtitle,
        'description': episode_data.get('description', subtitle),
        'series_id': series_id,
        'series_title': series_title,
        'season': episode_data.get('seasonNumber') or episode_data.get('seasonId'),
        'episode_number': episode_data.get('episodeNumber'),
        'duration_seconds': duration,
        'duration_display': episode_data.get('durationDisplayValue', ''),
        'year': year,
        'image_url': image_url,
        'medium': medium,
        'expiry_date': expiry_date.isoformat() if expiry_date else None,
        'expiry_display': expiry_display,
        'is_long_term': is_available_long_term(expiry_date),
        'availability_status': availability.get('status', ''),
        'contributors': contributors,
        'nrk_url': f"https://{'radio' if medium == 'radio' else 'tv'}.nrk.no/{'serie' if series_id else 'program'}/{series_id or prf_id.lower()}/{prf_id.lower()}" if series_id else f"https://tv.nrk.no/program/{prf_id}",
    }


def main():
    print("=" * 60)
    print("Phase 2: Extracting Classical Music Episodes")
    print("=" * 60)

    # Load discovered series
    if not INPUT_FILE.exists():
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        print("Please run discover_classical_series.py first.")
        return

    with open(INPUT_FILE) as f:
        discovery_data = json.load(f)

    series_list = discovery_data.get('series', {})
    standalone_programs = discovery_data.get('programs', {})

    print(f"Found {len(series_list)} series and {len(standalone_programs)} standalone programs")

    all_episodes = []
    skipped_short = 0
    skipped_expiring = 0
    skipped_unavailable = 0

    # Process each series
    print("\n[1/2] Processing series...")
    for idx, (series_id, series_info) in enumerate(series_list.items()):
        series_title = series_info.get('title', series_id)
        medium = series_info.get('source_medium', 'tv')

        # Skip non-classical series based on keywords
        skip_keywords = ['labyrint', 'larveskolen', 'langrenn', 'last:', 'landslag', 'serviceheft', 'carmen curlers']
        if any(kw in series_title.lower() for kw in skip_keywords):
            continue

        print(f"  [{idx+1}/{len(series_list)}] {series_title} ({series_id})")

        # Get seasons
        if medium == 'radio':
            seasons = get_radio_series_seasons(series_id)
        else:
            seasons = get_tv_series_seasons(series_id)

        if not seasons:
            # Try to get episodes directly for series without seasons
            seasons = ['']  # Empty season ID to try direct fetch

        time.sleep(0.2)

        for season_id in seasons:
            if medium == 'radio':
                episodes = get_radio_season_episodes(series_id, season_id) if season_id else []
            else:
                episodes = get_tv_season_episodes(series_id, season_id) if season_id else []

            if not episodes:
                continue

            time.sleep(0.2)

            for ep in episodes:
                ep_info = extract_episode_info(ep, series_id, series_title, medium)

                # Filter by availability
                if ep_info['availability_status'] not in ['available', '']:
                    skipped_unavailable += 1
                    continue

                # Filter by expiry (must be available for 1+ year)
                if not ep_info['is_long_term']:
                    skipped_expiring += 1
                    continue

                # Filter by duration (25+ minutes)
                if ep_info['duration_seconds'] < MIN_DURATION_SECONDS:
                    skipped_short += 1
                    continue

                all_episodes.append(ep_info)

        print(f"    Found {sum(1 for e in all_episodes if e['series_id'] == series_id)} episodes")

    # Process standalone programs
    print("\n[2/2] Processing standalone programs...")
    for idx, (prog_id, prog_info) in enumerate(standalone_programs.items()):
        if idx % 50 == 0:
            print(f"  Processing {idx}/{len(standalone_programs)}...")

        # Fetch detailed info
        details = get_program_details(prog_id)
        time.sleep(0.15)

        if not details:
            continue

        # Create episode info from program details
        ep_info = {
            'prf_id': prog_id,
            'title': prog_info.get('title', ''),
            'subtitle': '',
            'description': prog_info.get('description', ''),
            'series_id': details.get('seriesId', ''),
            'series_title': details.get('seriesTitle', ''),
            'season': details.get('seasonNumber'),
            'episode_number': details.get('episodeNumber'),
            'duration_seconds': parse_iso_duration(details.get('duration', '')),
            'duration_display': '',
            'year': details.get('productionYear'),
            'image_url': '',
            'medium': 'radio' if details.get('sourceMedium') == 2 else 'tv',
            'nrk_url': prog_info.get('url', ''),
            'contributors': [],
            'discovered_via': prog_info.get('discovered_via', ''),
        }

        # Parse expiry
        expiry_str = prog_info.get('expiry_date', '')
        if expiry_str:
            try:
                expiry_date = datetime.fromisoformat(expiry_str)
                ep_info['expiry_date'] = expiry_str
                ep_info['is_long_term'] = is_available_long_term(expiry_date)
            except:
                ep_info['expiry_date'] = None
                ep_info['is_long_term'] = True
        else:
            ep_info['expiry_date'] = None
            ep_info['is_long_term'] = True

        # Filter by expiry
        if not ep_info.get('is_long_term', True):
            skipped_expiring += 1
            continue

        # Filter by duration
        if ep_info['duration_seconds'] < MIN_DURATION_SECONDS:
            skipped_short += 1
            continue

        # Skip if we already have this episode from series processing
        if any(e['prf_id'] == prog_id for e in all_episodes):
            continue

        all_episodes.append(ep_info)

    # Deduplicate by prf_id
    seen_ids = set()
    unique_episodes = []
    for ep in all_episodes:
        if ep['prf_id'] not in seen_ids:
            seen_ids.add(ep['prf_id'])
            unique_episodes.append(ep)

    # Output
    output_data = {
        'extracted_at': datetime.now().isoformat(),
        'filters_applied': {
            'min_duration_seconds': MIN_DURATION_SECONDS,
            'expiry_threshold': EXPIRY_THRESHOLD.isoformat(),
        },
        'statistics': {
            'total_episodes': len(unique_episodes),
            'skipped_short': skipped_short,
            'skipped_expiring': skipped_expiring,
            'skipped_unavailable': skipped_unavailable,
            'by_medium': {
                'tv': sum(1 for e in unique_episodes if e.get('medium') == 'tv'),
                'radio': sum(1 for e in unique_episodes if e.get('medium') == 'radio'),
            }
        },
        'episodes': unique_episodes,
    }

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("EXTRACTION COMPLETE")
    print("=" * 60)
    print(f"Total episodes extracted: {len(unique_episodes)}")
    print(f"Skipped (too short <25min): {skipped_short}")
    print(f"Skipped (expiring <1 year): {skipped_expiring}")
    print(f"Skipped (unavailable): {skipped_unavailable}")
    print(f"\nBy medium:")
    print(f"  TV: {output_data['statistics']['by_medium']['tv']}")
    print(f"  Radio: {output_data['statistics']['by_medium']['radio']}")
    print(f"\nOutput written to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
