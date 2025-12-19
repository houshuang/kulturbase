#!/usr/bin/env python3
"""
Harvest all episodes from NRK Fjernsynsteatret.

This script fetches all episodes from the NRK PSAPI and saves them as JSON.
It also fetches detailed metadata for each episode.

Usage:
    python 01_harvest_nrk.py [--series SERIES_ID] [--delay SECONDS]

Example:
    python 01_harvest_nrk.py --series fjernsynsteatret --delay 1.0
"""

import argparse
import json
import time
from pathlib import Path
from datetime import datetime

from utils.nrk_api import (
    fetch_series_instalments,
    fetch_program_details,
    instalment_to_episode,
)


def harvest_series(series_id: str, output_dir: Path, delay: float = 1.0):
    """Harvest all episodes from a series."""
    print(f"\n{'='*60}")
    print(f"Harvesting series: {series_id}")
    print(f"Output directory: {output_dir}")
    print(f"Delay between requests: {delay}s")
    print(f"{'='*60}\n")

    # Create output directories
    series_dir = output_dir / series_id
    details_dir = series_dir / "details"
    series_dir.mkdir(parents=True, exist_ok=True)
    details_dir.mkdir(exist_ok=True)

    # Fetch all instalments
    episodes = []
    for inst in fetch_series_instalments(series_id, delay=delay):
        ep = instalment_to_episode(inst)
        episodes.append(ep)
        print(f"  [{len(episodes):3d}] {ep['year']} - {ep['title'][:50]}")

    # Save episodes list
    episodes_file = series_dir / "episodes.json"
    with open(episodes_file, "w", encoding="utf-8") as f:
        json.dump(episodes, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(episodes)} episodes to {episodes_file}")

    # Fetch detailed metadata for each episode
    print(f"\nFetching detailed metadata for {len(episodes)} episodes...")
    errors = []

    for i, ep in enumerate(episodes):
        prf_id = ep["prf_id"]
        detail_file = details_dir / f"{prf_id}.json"

        # Skip if already fetched
        if detail_file.exists():
            print(f"  [{i+1:3d}/{len(episodes)}] {prf_id} - already fetched")
            continue

        try:
            print(f"  [{i+1:3d}/{len(episodes)}] {prf_id} - fetching...")
            details = fetch_program_details(prf_id)

            with open(detail_file, "w", encoding="utf-8") as f:
                json.dump(details, f, ensure_ascii=False, indent=2)

            time.sleep(delay)

        except Exception as e:
            print(f"    ERROR: {e}")
            errors.append({"prf_id": prf_id, "error": str(e)})

    # Save harvest metadata
    metadata = {
        "series_id": series_id,
        "harvested_at": datetime.now().isoformat(),
        "total_episodes": len(episodes),
        "errors": errors,
    }
    metadata_file = series_dir / "harvest_metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"Harvest complete!")
    print(f"  Episodes: {len(episodes)}")
    print(f"  Errors: {len(errors)}")
    print(f"  Output: {series_dir}")
    print(f"{'='*60}\n")

    return episodes, errors


def main():
    parser = argparse.ArgumentParser(description="Harvest NRK series data")
    parser.add_argument(
        "--series",
        default="fjernsynsteatret",
        help="Series ID to harvest (default: fjernsynsteatret)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between API requests in seconds (default: 1.0)",
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

    harvest_series(args.series, output_dir, args.delay)


if __name__ == "__main__":
    main()
