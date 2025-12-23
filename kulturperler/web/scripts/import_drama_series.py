#!/usr/bin/env python3
"""Import NRK drama series into Kulturperler archive."""

import json
import os
import re
import sqlite3
import subprocess
from pathlib import Path
from typing import Dict, List, Optional


def parse_duration(duration_str: str) -> int:
    """Parse ISO 8601 duration to seconds (PT30M -> 1800)."""
    if not duration_str:
        return 0

    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
    if not match:
        return 0

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)

    return hours * 3600 + minutes * 60 + seconds


def get_image_url(images: List[Dict], pixel_width: int = 960) -> Optional[str]:
    """Get image URL with specified pixel width."""
    if not images:
        return None

    # Handle both 'pixelWidth' and 'width' field names
    for img in images:
        width = img.get('pixelWidth') or img.get('width')
        if width == pixel_width:
            return img.get('url') or img.get('imageUrl')

    # Return first image if no exact match
    first_img = images[0] if images else None
    return first_img.get('url') or first_img.get('imageUrl') if first_img else None


def get_series_info(series_id: str) -> Dict:
    """Fetch series info from NRK API."""
    url = f"https://psapi.nrk.no/tv/catalog/series/{series_id}"
    result = subprocess.run(['curl', '-s', url], capture_output=True, text=True)
    return json.loads(result.stdout)


def get_existing_episodes(db_path: str, series_id: str) -> set:
    """Get existing episode IDs from database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT prf_id FROM episodes WHERE series_id = ?", (series_id,))
    existing = {row[0] for row in cursor.fetchall()}
    conn.close()
    return existing


def create_episode_yaml(episode: Dict, series_id: str, episodes_dir: Path) -> None:
    """Create episode YAML file."""
    prf_id = episode.get('prfId')
    if not prf_id:
        return

    title = episode.get('titles', {}).get('title', '')
    subtitle = episode.get('titles', {}).get('subtitle', '')
    if subtitle:
        title = f"{title}: {subtitle}"

    # Get description - try multiple field names
    description = episode.get('description', '') or episode.get('longDescription', '')

    # Parse year from production year or release date
    year = episode.get('productionYear')
    if not year:
        original_release = episode.get('originalReleaseDate') or episode.get('releaseDateOnDemand')
        if original_release:
            year = int(original_release[:4])

    # Get duration - prefer durationInSeconds if available
    duration = episode.get('durationInSeconds')
    if not duration:
        duration = parse_duration(episode.get('duration', ''))

    # Get image - handle both webImages and direct image array
    images = episode.get('image', {})
    if isinstance(images, dict):
        images = images.get('webImages', [])
    image_url = get_image_url(images)

    nrk_url = f"https://tv.nrk.no/program/{prf_id}"

    yaml_content = f'''prf_id: "{prf_id}"
title: "{title}"
description: |
  {description}
year: {year}
duration_seconds: {duration}
image_url: "{image_url}"
nrk_url: "{nrk_url}"
source: "nrk"
medium: "tv"
series_id: "{series_id}"
'''

    yaml_file = episodes_dir / f"{prf_id}.yaml"
    yaml_file.write_text(yaml_content)
    print(f"Created: {yaml_file.name}")


def get_season_data(series_id: str, season_num: str) -> Dict:
    """Fetch season data with episodes from NRK API."""
    url = f"https://psapi.nrk.no/tv/catalog/series/{series_id}/seasons/{season_num}"
    result = subprocess.run(['curl', '-s', url], capture_output=True, text=True)
    return json.loads(result.stdout)


def import_series(series_id: str, episodes_dir: Path, db_path: str) -> None:
    """Import all episodes for a series."""
    print(f"\n=== Importing {series_id} ===")

    # Get existing episodes
    existing = get_existing_episodes(db_path, series_id)
    print(f"Found {len(existing)} existing episodes in database")

    # Get series info
    series_data = get_series_info(series_id)

    # Get season links
    season_links = series_data.get('_links', {}).get('seasons', [])
    if not season_links:
        print(f"No seasons found for {series_id}")
        return

    print(f"Found {len(season_links)} season(s)")

    # Process each season
    new_count = 0
    for season_link in season_links:
        season_name = season_link.get('name', 'Unknown')

        # Fetch full season data with episodes
        season_data = get_season_data(series_id, season_name)

        # Try both 'episodes' and 'instalments' (NRK uses different names)
        episodes_list = season_data.get('_embedded', {}).get('episodes', [])
        if not episodes_list:
            episodes_list = season_data.get('_embedded', {}).get('instalments', [])

        print(f"  Season: {season_name} - {len(episodes_list)} episodes")

        for episode in episodes_list:
            prf_id = episode.get('prfId')
            if prf_id and prf_id not in existing:
                create_episode_yaml(episode, series_id, episodes_dir)
                new_count += 1

    print(f"Imported {new_count} new episodes for {series_id}")


def main():
    """Main import function."""
    # Setup paths
    base_dir = Path(__file__).parent.parent
    episodes_dir = base_dir / 'data' / 'episodes'
    db_path = base_dir / 'static' / 'kulturperler.db'

    # Series to import
    series_list = [
        'gass-og-stearinlys',
        'sommer-i-tyrol',
        'det-siste-kuppet',
        'kontorsjef-tangen',
        'fuglekongen',
        'prisgitt'
    ]

    # Import each series
    for series_id in series_list:
        try:
            import_series(series_id, episodes_dir, db_path)
        except Exception as e:
            print(f"Error importing {series_id}: {e}")

    print("\n=== Import complete ===")


if __name__ == '__main__':
    main()
