#!/usr/bin/env python3
"""
Harvest theatre content from Nationaltheatret NTV (video hub).

The NTV section of nationaltheatret.no contains YouTube-embedded videos
organized by categories (interviews, behind the scenes, readings, etc.).

Usage:
    python harvest_nationaltheatret.py [--min-duration 900]
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

NTV_BASE_URL = "https://www.nationaltheatret.no/ntv/"
ARCHIVE_BASE_URL = "https://forest.nationaltheatret.no"


def get_page(url: str) -> BeautifulSoup | None:
    """Fetch a page and return parsed BeautifulSoup."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None


def extract_youtube_ids(soup: BeautifulSoup) -> list[str]:
    """Extract YouTube video IDs from embedded players on a page."""
    video_ids = []

    # Look for iframe embeds
    for iframe in soup.find_all("iframe"):
        src = iframe.get("src", "")
        # YouTube embed URLs: youtube.com/embed/VIDEO_ID
        match = re.search(r"youtube\.com/embed/([a-zA-Z0-9_-]{11})", src)
        if match:
            video_ids.append(match.group(1))

    # Look for data attributes with YouTube IDs
    for elem in soup.find_all(attrs={"data-video-id": True}):
        video_id = elem.get("data-video-id")
        if video_id and len(video_id) == 11:
            video_ids.append(video_id)

    # Look for YouTube URLs in links
    for link in soup.find_all("a", href=True):
        href = link["href"]
        match = re.search(r"(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})", href)
        if match:
            video_ids.append(match.group(1))

    return list(set(video_ids))  # Deduplicate


def get_video_metadata(video_id: str) -> dict | None:
    """Get video metadata using yt-dlp."""
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
        print(f"Error getting metadata for {video_id}: {e}")

    return None


def scrape_ntv_pages() -> list[dict]:
    """Scrape all NTV pages and extract video information."""
    print("Scraping NTV main page...")
    soup = get_page(NTV_BASE_URL)
    if not soup:
        return []

    videos = []
    video_ids_seen = set()

    # Extract videos from main page
    main_ids = extract_youtube_ids(soup)
    print(f"Found {len(main_ids)} videos on main page")

    for vid in main_ids:
        if vid not in video_ids_seen:
            video_ids_seen.add(vid)
            videos.append({"video_id": vid, "source_page": NTV_BASE_URL})

    # Find links to subpages
    subpage_links = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "/ntv/" in href and href != NTV_BASE_URL:
            if href.startswith("/"):
                href = f"https://www.nationaltheatret.no{href}"
            if href.startswith("https://www.nationaltheatret.no/ntv/"):
                subpage_links.append(href)

    subpage_links = list(set(subpage_links))
    print(f"Found {len(subpage_links)} NTV subpages")

    # Scrape subpages
    for url in subpage_links:
        time.sleep(0.5)
        print(f"  Scraping {url}...")
        page_soup = get_page(url)
        if page_soup:
            page_ids = extract_youtube_ids(page_soup)
            for vid in page_ids:
                if vid not in video_ids_seen:
                    video_ids_seen.add(vid)
                    videos.append({"video_id": vid, "source_page": url})

    print(f"Total unique videos found: {len(videos)}")
    return videos


def extract_year(upload_date: str | None) -> int | None:
    """Extract year from upload date (format: YYYYMMDD)."""
    if not upload_date or len(upload_date) < 4:
        return None
    try:
        return int(upload_date[:4])
    except ValueError:
        return None


def classify_content_type(title: str, description: str, source_page: str) -> str:
    """Classify the type of content based on title, description, and source."""
    text = f"{title} {description} {source_page}".lower()

    if any(kw in text for kw in ["intervju", "samtale", "snakker", "interview"]):
        return "discussion"
    if any(kw in text for kw in ["lesning", "opplesning", "dikt", "reading"]):
        return "reading"
    if any(kw in text for kw in ["kulissene", "behind", "dokumentar"]):
        return "documentary"
    if any(kw in text for kw in ["forestilling", "premiere", "performance"]):
        return "full_performance"
    if any(kw in text for kw in ["trailer", "teaser"]):
        return "trailer"

    return "other"


def process_video(video_info: dict, metadata: dict) -> dict:
    """Process a video into our standard format."""
    video_id = video_info["video_id"]

    return {
        "source": "nationaltheatret_ntv",
        "source_id": video_id,
        "title": metadata.get("title", ""),
        "description": metadata.get("description", ""),
        "year": extract_year(metadata.get("upload_date")),
        "duration_seconds": metadata.get("duration"),
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "thumbnail_url": metadata.get("thumbnail"),
        "platform": "youtube",
        "language": "no",
        "venue": "Nationaltheatret",
        "content_type": classify_content_type(
            metadata.get("title", ""),
            metadata.get("description", ""),
            video_info.get("source_page", "")
        ),
        "raw_metadata": {
            "source_page": video_info.get("source_page"),
            "channel": metadata.get("channel"),
            "upload_date": metadata.get("upload_date"),
            "view_count": metadata.get("view_count"),
        }
    }


def harvest(min_duration: int = 900, output_dir: Path | None = None) -> list[dict]:
    """
    Harvest theatre content from Nationaltheatret NTV.

    Args:
        min_duration: Minimum duration in seconds (default 15 minutes)
        output_dir: Directory to save results

    Returns:
        List of harvested videos
    """
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "data" / "raw" / "nationaltheatret"

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Harvesting Nationaltheatret NTV")
    print(f"Minimum duration: {min_duration // 60} minutes")
    print("=" * 60)

    # Scrape NTV pages for video IDs
    video_infos = scrape_ntv_pages()

    # Get metadata for each video
    results = []
    skipped_short = 0
    skipped_error = 0

    for i, video_info in enumerate(video_infos):
        video_id = video_info["video_id"]
        print(f"\rProcessing {i+1}/{len(video_infos)}: {video_id}...", end="", flush=True)

        metadata = get_video_metadata(video_id)
        if not metadata:
            skipped_error += 1
            continue

        time.sleep(0.3)  # Rate limiting

        # Filter by duration
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
    items_file = output_dir / "ntv_videos.json"
    with open(items_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Saved to: {items_file}")

    # Save metadata
    harvest_metadata = {
        "harvested_at": datetime.now().isoformat(),
        "total_videos": len(results),
        "min_duration_seconds": min_duration,
        "skipped_short": skipped_short,
        "skipped_error": skipped_error,
        "source_url": NTV_BASE_URL,
    }
    metadata_file = output_dir / "harvest_metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(harvest_metadata, f, ensure_ascii=False, indent=2)

    return results


def main():
    parser = argparse.ArgumentParser(description="Harvest Nationaltheatret NTV videos")
    parser.add_argument(
        "--min-duration",
        type=int,
        default=900,
        help="Minimum duration in seconds (default: 900 = 15 minutes)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output directory (default: data/raw/nationaltheatret)",
    )

    args = parser.parse_args()

    output_dir = Path(args.output) if args.output else None
    harvest(min_duration=args.min_duration, output_dir=output_dir)


if __name__ == "__main__":
    main()
