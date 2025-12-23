#!/usr/bin/env python3
"""Import NRK drama series into Kulturperler archive."""

import requests
import yaml
import re
from pathlib import Path

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

def get_image_url(image_list, target_width=960):
    """Get image URL with specified width."""
    if not image_list:
        return None
    for img in image_list:
        if img.get('width') == target_width or img.get('pixelWidth') == target_width:
            return img.get('url') or img.get('imageUrl')
    return image_list[0].get('url') or image_list[0].get('imageUrl') if image_list else None

def fetch_series(series_id):
    """Fetch series from NRK API."""
    url = f"https://psapi.nrk.no/tv/catalog/series/{series_id}"
    print(f"\nFetching {series_id}...")
    r = requests.get(url)
    r.raise_for_status()
    return r.json()

def save_episode(episode, series_id, episodes_dir):
    """Save episode to YAML file."""
    prf_id = episode.get('prfId')
    if not prf_id:
        print(f"  WARNING: No prfId for episode")
        return False

    filepath = episodes_dir / f'{prf_id}.yaml'
    if filepath.exists():
        print(f"  Skipping {prf_id} - already exists")
        return False

    titles = episode.get('titles', {})
    title = titles.get('title', '')
    subtitle = titles.get('subtitle', '')

    # Use original release date for year
    year = None
    release_date = episode.get('releaseDateOnDemand', '')
    if release_date and len(release_date) >= 4:
        year = int(release_date[:4])

    duration = parse_duration(episode.get('duration'))
    image_url = get_image_url(episode.get('image', []))

    data = {
        'prf_id': prf_id,
        'title': title,
        'description': subtitle or '',
        'year': year,
        'duration_seconds': duration,
        'image_url': image_url,
        'nrk_url': f"https://tv.nrk.no/program/{prf_id}",
        'source': 'nrk',
        'medium': 'tv',
        'series_id': series_id
    }

    # Remove None values
    data = {k: v for k, v in data.items() if v is not None}

    with open(filepath, 'w') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"  Created {prf_id}: {title}")
    return True

def import_series(series_id, episodes_dir):
    """Import all episodes from a series."""
    print(f"\n{'='*60}")
    print(f"Processing: {series_id}")
    print(f"{'='*60}")

    data = fetch_series(series_id)
    seasons = data.get('_embedded', {}).get('seasons', [])

    if not seasons:
        print(f"No seasons found for {series_id}")
        return 0

    print(f"Found {len(seasons)} season(s)")
    count = 0

    for season in seasons:
        season_name = season.get('titles', {}).get('title', 'Unknown')
        print(f"\nSeason: {season_name}")

        episodes = season.get('_embedded', {}).get('episodes', [])
        if not episodes:
            episodes = season.get('_embedded', {}).get('instalments', [])

        print(f"  Found {len(episodes)} episodes")

        for ep in episodes:
            if save_episode(ep, series_id, episodes_dir):
                count += 1

    print(f"\n✓ Created {count} new episodes for {series_id}")
    return count

def main():
    """Main execution."""
    series_list = [
        'hverdagsjus',
        'wilhelm-tell-og-de-fredloese-ungene',
        'operasjon-kano',
        'rett-i-lomma',
        '17-mai'
    ]

    base_dir = Path(__file__).parent.parent
    episodes_dir = base_dir / 'data' / 'episodes'
    total = 0

    for series_id in series_list:
        try:
            total += import_series(series_id, episodes_dir)
        except Exception as e:
            print(f"ERROR: {series_id}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print(f"TOTAL: Created {total} episode files")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
