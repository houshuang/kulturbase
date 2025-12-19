#!/usr/bin/env python3
"""
Harvest theatre content from Norwegian theatre YouTube channels.

Uses yt-dlp to extract video metadata from theatre YouTube channels.
Filters by duration (15+ minutes) to focus on substantial content.

Usage:
    python harvest_youtube_channels.py [--min-duration 900]
"""

import argparse
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path


# Norwegian theatre YouTube channels
THEATRE_CHANNELS = {
    "halogaland_teater": {
        "url": "https://www.youtube.com/@hteater",
        "name": "Hålogaland Teater",
        "venue": "Hålogaland Teater",
    },
    "den_norske_opera": {
        "url": "https://www.youtube.com/@operaen",
        "name": "Den Norske Opera & Ballett",
        "venue": "Den Norske Opera",
    },
    "nationaltheatret": {
        "url": "https://www.youtube.com/@nationaltheatret",
        "name": "Nationaltheatret",
        "venue": "Nationaltheatret",
    },
    "dns_bergen": {
        "url": "https://www.youtube.com/@dennationalescene",
        "name": "Den Nationale Scene",
        "venue": "Den Nationale Scene",
    },
    "oslo_nye": {
        "url": "https://www.youtube.com/@oslonye",
        "name": "Oslo Nye Teater",
        "venue": "Oslo Nye Teater",
    },
    "rogaland_teater": {
        "url": "https://www.youtube.com/@rogalandteater",
        "name": "Rogaland Teater",
        "venue": "Rogaland Teater",
    },
    "trondelag_teater": {
        "url": "https://www.youtube.com/@trondelagteater",
        "name": "Trøndelag Teater",
        "venue": "Trøndelag Teater",
    },
    "kilden": {
        "url": "https://www.youtube.com/@kildenteaterogkonserthus",
        "name": "Kilden Teater og Konserthus",
        "venue": "Kilden",
    },
}


def run_ytdlp(url: str, extra_args: list | None = None) -> dict | None:
    """Run yt-dlp and return JSON output."""
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--flat-playlist",
        "--no-download",
        "--ignore-errors",
        url,
    ]
    if extra_args:
        cmd.extend(extra_args)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        print(f"Timeout fetching {url}")
        return None
    except Exception as e:
        print(f"Error running yt-dlp: {e}")
        return None


def get_channel_videos(channel_url: str) -> list[dict]:
    """Get all videos from a YouTube channel."""
    # First get the playlist of all videos
    videos_url = f"{channel_url}/videos"

    output = run_ytdlp(videos_url)
    if not output:
        return []

    videos = []
    for line in output.strip().split("\n"):
        if not line:
            continue
        try:
            video = json.loads(line)
            videos.append(video)
        except json.JSONDecodeError:
            continue

    return videos


def get_video_details(video_id: str) -> dict | None:
    """Get detailed metadata for a single video."""
    url = f"https://www.youtube.com/watch?v={video_id}"

    cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-download",
        url,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.stdout:
            return json.loads(result.stdout)
    except Exception as e:
        print(f"Error getting details for {video_id}: {e}")

    return None


def extract_year(upload_date: str | None) -> int | None:
    """Extract year from upload date (format: YYYYMMDD)."""
    if not upload_date or len(upload_date) < 4:
        return None
    try:
        return int(upload_date[:4])
    except ValueError:
        return None


def classify_content_type(title: str, description: str) -> str:
    """Classify the type of content based on title and description."""
    text = f"{title} {description}".lower()

    if any(kw in text for kw in ["full forestilling", "hele forestillingen", "full performance"]):
        return "full_performance"
    if any(kw in text for kw in ["intervju", "samtale", "snakker om", "interview"]):
        return "discussion"
    if any(kw in text for kw in ["lesning", "opplesning", "reading"]):
        return "reading"
    if any(kw in text for kw in ["dokumentar", "documentary", "bak kulissene", "behind the scenes"]):
        return "documentary"
    if any(kw in text for kw in ["trailer", "teaser", "promo"]):
        return "trailer"

    # Default - could be performance excerpt or other
    return "other"


def process_video(video: dict, channel_info: dict) -> dict:
    """Process a video into our standard format."""
    video_id = video.get("id") or video.get("url", "").split("=")[-1]

    return {
        "source": "youtube",
        "source_id": video_id,
        "title": video.get("title", ""),
        "description": video.get("description", ""),
        "year": extract_year(video.get("upload_date")),
        "duration_seconds": video.get("duration"),
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "thumbnail_url": video.get("thumbnail"),
        "platform": "youtube",
        "language": "no",
        "venue": channel_info.get("venue"),
        "content_type": classify_content_type(
            video.get("title", ""),
            video.get("description", "")
        ),
        "raw_metadata": {
            "channel": channel_info.get("name"),
            "channel_id": video.get("channel_id"),
            "upload_date": video.get("upload_date"),
            "view_count": video.get("view_count"),
        }
    }


def harvest_channel(channel_id: str, channel_info: dict, min_duration: int) -> list[dict]:
    """Harvest videos from a single channel."""
    print(f"\n  Fetching videos from {channel_info['name']}...")

    videos = get_channel_videos(channel_info["url"])
    print(f"  Found {len(videos)} videos")

    results = []
    skipped = 0

    for i, video in enumerate(videos):
        # For flat playlist, we only have basic info
        # Duration might not be available in flat mode
        video_id = video.get("id") or video.get("url", "").split("/")[-1]

        # Get detailed info if duration not available
        duration = video.get("duration")
        if duration is None:
            details = get_video_details(video_id)
            if details:
                video = details
                duration = details.get("duration")

        # Skip if too short
        if duration is not None and duration < min_duration:
            skipped += 1
            continue

        # Skip explicit trailers (usually < 5 min anyway)
        title = video.get("title", "").lower()
        if "trailer" in title and (duration is None or duration < 300):
            skipped += 1
            continue

        processed = process_video(video, channel_info)
        results.append(processed)

        if (i + 1) % 10 == 0:
            print(f"    Processed {i + 1}/{len(videos)} videos...")

    print(f"  Kept {len(results)} substantial videos (skipped {skipped})")
    return results


def harvest(min_duration: int = 900, output_dir: Path | None = None) -> dict[str, list[dict]]:
    """
    Harvest theatre content from YouTube channels.

    Args:
        min_duration: Minimum duration in seconds (default 15 minutes)
        output_dir: Directory to save results

    Returns:
        Dictionary mapping channel IDs to lists of videos
    """
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "data" / "raw" / "youtube_channels"

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Harvesting Norwegian theatre YouTube channels")
    print(f"Minimum duration: {min_duration // 60} minutes")
    print("=" * 60)

    all_results = {}
    total_videos = 0

    for channel_id, channel_info in THEATRE_CHANNELS.items():
        results = harvest_channel(channel_id, channel_info, min_duration)
        all_results[channel_id] = results
        total_videos += len(results)

        # Save per-channel results
        channel_file = output_dir / f"{channel_id}.json"
        with open(channel_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"Total: {total_videos} substantial videos from {len(THEATRE_CHANNELS)} channels")
    print(f"{'=' * 60}")

    # Save combined results
    combined = []
    for channel_results in all_results.values():
        combined.extend(channel_results)

    combined_file = output_dir / "all_videos.json"
    with open(combined_file, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)
    print(f"\nSaved combined results to: {combined_file}")

    # Save metadata
    metadata = {
        "harvested_at": datetime.now().isoformat(),
        "total_videos": total_videos,
        "min_duration_seconds": min_duration,
        "channels": {
            cid: {
                "name": info["name"],
                "url": info["url"],
                "video_count": len(all_results.get(cid, [])),
            }
            for cid, info in THEATRE_CHANNELS.items()
        },
    }
    metadata_file = output_dir / "harvest_metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    return all_results


def main():
    parser = argparse.ArgumentParser(description="Harvest Norwegian theatre YouTube channels")
    parser.add_argument(
        "--min-duration",
        type=int,
        default=900,
        help="Minimum duration in seconds (default: 900 = 15 minutes)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output directory (default: data/raw/youtube_channels)",
    )
    parser.add_argument(
        "--channel",
        type=str,
        help="Only harvest specific channel (by ID)",
    )

    args = parser.parse_args()

    output_dir = Path(args.output) if args.output else None

    if args.channel:
        if args.channel not in THEATRE_CHANNELS:
            print(f"Unknown channel: {args.channel}")
            print(f"Available: {', '.join(THEATRE_CHANNELS.keys())}")
            return

        channel_info = THEATRE_CHANNELS[args.channel]
        results = harvest_channel(args.channel, channel_info, args.min_duration)
        print(f"\nFound {len(results)} videos")
    else:
        harvest(min_duration=args.min_duration, output_dir=output_dir)


if __name__ == "__main__":
    main()
