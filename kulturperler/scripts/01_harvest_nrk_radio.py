#!/usr/bin/env python3
"""
Harvest all episodes from NRK Radio hørespill (radio dramas).

This script fetches all radio drama series from the NRK Radio PSAPI
hørespill page and saves them as JSON.

Usage:
    python 01_harvest_nrk_radio.py [--delay SECONDS] [--limit N]

Example:
    python 01_harvest_nrk_radio.py --delay 0.5
    python 01_harvest_nrk_radio.py --limit 10  # First 10 series only (for testing)
"""

import argparse
import json
import time
from pathlib import Path
from datetime import datetime

from utils.nrk_api import (
    fetch_all_hoerespill_series,
    fetch_radio_series_instalments,
    series_episode_to_episode,
)


def harvest_all_radio_series(output_dir: Path, delay: float = 0.5, limit: int = None):
    """Harvest all episodes from all hørespill series."""
    print(f"\n{'='*60}")
    print("Harvesting all NRK Radio hørespill (radio dramas)")
    print(f"Output directory: {output_dir}")
    print(f"Delay between requests: {delay}s")
    print(f"{'='*60}\n")

    # Fetch all series from hørespill page
    print("Fetching list of all hørespill series...")
    all_series = fetch_all_hoerespill_series()
    print(f"Found {len(all_series)} unique series\n")

    if limit:
        print(f"Limiting to first {limit} series (test mode)")
        all_series = all_series[:limit]

    # Create output directory for radio dramas
    radio_dir = output_dir / "hoerespill"
    radio_dir.mkdir(parents=True, exist_ok=True)

    all_episodes = []
    successful_series = 0
    failed_series = []

    for i, series_info in enumerate(all_series, 1):
        series_id = series_info["id"]
        series_title = series_info["title"]
        expected_eps = series_info.get("numberOfEpisodes", 0)

        print(f"\n[{i}/{len(all_series)}] {series_id}: {series_title} (expecting ~{expected_eps} eps)")

        try:
            episodes = []
            for ep in fetch_radio_series_instalments(series_id, delay=delay):
                episode_data = series_episode_to_episode(ep, series_id)
                episodes.append(episode_data)

            if episodes:
                all_episodes.extend(episodes)
                successful_series += 1
                print(f"  -> Got {len(episodes)} episodes")
            else:
                print(f"  -> No episodes available")

        except Exception as e:
            print(f"  -> ERROR: {e}")
            failed_series.append((series_id, str(e)))

        time.sleep(delay)

    # Save all episodes to a single file
    episodes_file = radio_dir / "all_episodes.json"
    with open(episodes_file, "w", encoding="utf-8") as f:
        json.dump(all_episodes, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(all_episodes)} episodes to {episodes_file}")

    # Save harvest metadata
    metadata = {
        "harvested_at": datetime.now().isoformat(),
        "total_series_found": len(all_series),
        "successful_series": successful_series,
        "total_episodes": len(all_episodes),
        "failed_series": failed_series,
    }
    metadata_file = radio_dir / "harvest_metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    # Save series list
    series_file = radio_dir / "series_list.json"
    with open(series_file, "w", encoding="utf-8") as f:
        json.dump(all_series, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print("Harvest complete!")
    print(f"  Series attempted: {len(all_series)}")
    print(f"  Series successful: {successful_series}")
    print(f"  Series failed: {len(failed_series)}")
    print(f"  Total episodes: {len(all_episodes)}")
    print(f"  Output: {radio_dir}")
    print(f"{'='*60}\n")

    if failed_series:
        print("Failed series:")
        for sid, err in failed_series[:10]:
            print(f"  - {sid}: {err}")
        if len(failed_series) > 10:
            print(f"  ... and {len(failed_series) - 10} more")

    return all_episodes


def main():
    parser = argparse.ArgumentParser(description="Harvest NRK radio drama data")
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between API requests in seconds (default: 0.5)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit to first N series (for testing)",
    )
    parser.add_argument(
        "--output",
        default="data/raw",
        help="Output directory (default: data/raw)",
    )

    args = parser.parse_args()

    # Resolve output directory relative to script location
    script_dir = Path(__file__).parent.parent
    output_dir = script_dir / args.output

    harvest_all_radio_series(output_dir, args.delay, args.limit)


if __name__ == "__main__":
    main()
