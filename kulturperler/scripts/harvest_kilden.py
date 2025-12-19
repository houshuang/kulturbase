#!/usr/bin/env python3
"""
Harvest theatre content from Kilden Teater og Konserthus.

Kilden has a digital archive and YouTube presence. This script
attempts to find substantial theatre content from their platforms.

Usage:
    python harvest_kilden.py [--min-duration 900]
"""

import argparse
import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.kilden.com"
YOUTUBE_CHANNEL = "https://www.youtube.com/@kildenteaterogkonserthus"


def get_page(url: str) -> BeautifulSoup | None:
    """Fetch a page and return parsed BeautifulSoup."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None


def extract_video_urls(soup: BeautifulSoup) -> list[dict]:
    """Extract video URLs from a page."""
    videos = []

    # YouTube iframes
    for iframe in soup.find_all("iframe"):
        src = iframe.get("src", "")
        match = re.search(r"youtube\.com/embed/([a-zA-Z0-9_-]{11})", src)
        if match:
            videos.append({
                "platform": "youtube",
                "video_id": match.group(1),
                "url": f"https://www.youtube.com/watch?v={match.group(1)}"
            })

    # Vimeo iframes
    for iframe in soup.find_all("iframe"):
        src = iframe.get("src", "")
        match = re.search(r"player\.vimeo\.com/video/(\d+)", src)
        if match:
            videos.append({
                "platform": "vimeo",
                "video_id": match.group(1),
                "url": f"https://vimeo.com/{match.group(1)}"
            })

    return videos


def get_youtube_videos() -> list[dict]:
    """Get videos from Kilden's YouTube channel using yt-dlp."""
    print("Fetching Kilden YouTube channel...")

    cmd = [
        "yt-dlp",
        "--dump-json",
        "--flat-playlist",
        "--no-download",
        "--ignore-errors",
        f"{YOUTUBE_CHANNEL}/videos",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        print("Timeout fetching YouTube channel")
        return []
    except Exception as e:
        print(f"Error: {e}")
        return []

    videos = []
    if result.stdout:
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                video = json.loads(line)
                video["source_page"] = YOUTUBE_CHANNEL
                videos.append(video)
            except json.JSONDecodeError:
                continue

    print(f"Found {len(videos)} videos on YouTube")
    return videos


def explore_website_videos() -> list[dict]:
    """Explore Kilden website for embedded videos."""
    print("Exploring Kilden website for videos...")

    videos = []
    pages_to_check = [
        f"{BASE_URL}/",
        f"{BASE_URL}/program/",
        f"{BASE_URL}/om-kilden/",
        f"{BASE_URL}/arkiv/",
    ]

    visited = set()

    for url in pages_to_check:
        if url in visited:
            continue
        visited.add(url)

        soup = get_page(url)
        if not soup:
            continue

        time.sleep(0.5)

        # Find videos on this page
        page_videos = extract_video_urls(soup)
        for v in page_videos:
            v["source_page"] = url
            videos.append(v)

        # Find more pages to explore
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if href.startswith("/"):
                full_url = f"{BASE_URL}{href}"
            elif href.startswith(BASE_URL):
                full_url = href
            else:
                continue

            # Only add pages that might have video content
            if any(kw in full_url.lower() for kw in ["video", "arkiv", "stream", "digital"]):
                if full_url not in visited and full_url not in pages_to_check:
                    pages_to_check.append(full_url)

    print(f"Found {len(videos)} videos on website")
    return videos


def get_video_metadata(video_info: dict) -> dict | None:
    """Get video metadata using yt-dlp."""
    url = video_info.get("url") or video_info.get("webpage_url")
    if not url:
        video_id = video_info.get("id") or video_info.get("video_id")
        if video_id:
            url = f"https://www.youtube.com/watch?v={video_id}"
        else:
            return None

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
        print(f"Error getting metadata: {e}")

    return None


def extract_year(upload_date: str | None) -> int | None:
    """Extract year from upload date."""
    if not upload_date or len(upload_date) < 4:
        return None
    try:
        return int(upload_date[:4])
    except ValueError:
        return None


def classify_content_type(title: str, description: str) -> str:
    """Classify the type of content."""
    text = f"{title} {description}".lower()

    if any(kw in text for kw in ["konsert", "concert", "live"]):
        return "full_performance"
    if any(kw in text for kw in ["teater", "theatre", "forestilling"]):
        return "full_performance"
    if any(kw in text for kw in ["intervju", "samtale", "interview"]):
        return "discussion"
    if any(kw in text for kw in ["bak kulissene", "behind"]):
        return "documentary"
    if any(kw in text for kw in ["trailer", "teaser"]):
        return "trailer"

    return "other"


def process_video(video_info: dict, metadata: dict) -> dict:
    """Process a video into our standard format."""
    video_id = video_info.get("video_id") or video_info.get("id") or metadata.get("id", "")
    platform = video_info.get("platform", "youtube")

    if platform == "youtube":
        url = f"https://www.youtube.com/watch?v={video_id}"
    elif platform == "vimeo":
        url = f"https://vimeo.com/{video_id}"
    else:
        url = video_info.get("url", metadata.get("webpage_url", ""))

    return {
        "source": "kilden",
        "source_id": f"kilden_{video_id}",
        "title": metadata.get("title", ""),
        "description": metadata.get("description", ""),
        "year": extract_year(metadata.get("upload_date")),
        "duration_seconds": metadata.get("duration"),
        "url": url,
        "thumbnail_url": metadata.get("thumbnail"),
        "platform": platform,
        "language": "no",
        "venue": "Kilden",
        "content_type": classify_content_type(
            metadata.get("title", ""),
            metadata.get("description", "")
        ),
        "raw_metadata": {
            "source_page": video_info.get("source_page"),
            "upload_date": metadata.get("upload_date"),
            "view_count": metadata.get("view_count"),
        }
    }


def harvest(min_duration: int = 900, output_dir: Path | None = None) -> list[dict]:
    """
    Harvest theatre content from Kilden.

    Args:
        min_duration: Minimum duration in seconds (default 15 minutes)
        output_dir: Directory to save results

    Returns:
        List of harvested videos
    """
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "data" / "raw" / "kilden"

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Harvesting Kilden Teater og Konserthus")
    print(f"Minimum duration: {min_duration // 60} minutes")
    print("=" * 60)

    # Get videos from YouTube and website
    youtube_videos = get_youtube_videos()
    website_videos = explore_website_videos()

    # Combine and deduplicate
    all_videos = []
    seen_ids = set()

    for v in youtube_videos + website_videos:
        vid = v.get("video_id") or v.get("id")
        if vid and vid not in seen_ids:
            seen_ids.add(vid)
            all_videos.append(v)

    print(f"\nTotal unique videos: {len(all_videos)}")

    # Get metadata and filter
    results = []
    skipped_short = 0
    skipped_error = 0

    for i, video_info in enumerate(all_videos):
        vid = video_info.get("video_id") or video_info.get("id", "unknown")
        print(f"\rProcessing {i+1}/{len(all_videos)}: {vid[:20]}...", end="", flush=True)

        metadata = get_video_metadata(video_info)
        if not metadata:
            skipped_error += 1
            continue

        time.sleep(0.3)

        duration = metadata.get("duration", 0)
        if duration < min_duration:
            skipped_short += 1
            continue

        processed = process_video(video_info, metadata)
        results.append(processed)

    print()
    print(f"\nResults: {len(results)} videos (15+ min)")
    print(f"Skipped: {skipped_short} too short, {skipped_error} errors")

    # Save results
    items_file = output_dir / "videos.json"
    with open(items_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Saved to: {items_file}")

    # Save metadata
    harvest_metadata = {
        "harvested_at": datetime.now().isoformat(),
        "total_videos": len(results),
        "min_duration_seconds": min_duration,
        "youtube_videos_found": len(youtube_videos),
        "website_videos_found": len(website_videos),
        "skipped_short": skipped_short,
        "skipped_error": skipped_error,
    }
    metadata_file = output_dir / "harvest_metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(harvest_metadata, f, ensure_ascii=False, indent=2)

    return results


def main():
    parser = argparse.ArgumentParser(description="Harvest Kilden theatre content")
    parser.add_argument(
        "--min-duration",
        type=int,
        default=900,
        help="Minimum duration in seconds (default: 900 = 15 minutes)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output directory (default: data/raw/kilden)",
    )

    args = parser.parse_args()

    output_dir = Path(args.output) if args.output else None
    harvest(min_duration=args.min_duration, output_dir=output_dir)


if __name__ == "__main__":
    main()
