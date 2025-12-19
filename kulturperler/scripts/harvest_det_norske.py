#!/usr/bin/env python3
"""
Harvest theatre content from Det Norske Teatret digital programs.

The program.detnorsketeatret.no site contains digital programs that may
include embedded video content tied to productions.

Usage:
    python harvest_det_norske.py [--min-duration 900]
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

BASE_URL = "https://program.detnorsketeatret.no"


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
    """Extract video URLs from a page (YouTube, Vimeo, or direct)."""
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

    # Look for video elements
    for video in soup.find_all("video"):
        src = video.get("src") or video.find("source", src=True)
        if src:
            src_url = src if isinstance(src, str) else src.get("src")
            if src_url:
                videos.append({
                    "platform": "direct",
                    "video_id": None,
                    "url": src_url
                })

    return videos


def get_program_list() -> list[dict]:
    """Get list of all program pages from the main site."""
    print("Fetching program list...")
    soup = get_page(BASE_URL)
    if not soup:
        return []

    programs = []

    # Look for links to program pages
    for link in soup.find_all("a", href=True):
        href = link["href"]

        # Internal links that look like program pages
        if href.startswith("/") and len(href) > 2 and not href.startswith("/static"):
            full_url = f"{BASE_URL}{href}"
            title = link.get_text(strip=True) or href.strip("/")

            programs.append({
                "url": full_url,
                "slug": href.strip("/"),
                "title": title,
            })

        # Already full URLs on the same domain
        elif href.startswith(BASE_URL) and href != BASE_URL:
            slug = href.replace(BASE_URL, "").strip("/")
            title = link.get_text(strip=True) or slug

            programs.append({
                "url": href,
                "slug": slug,
                "title": title,
            })

    # Deduplicate by URL
    seen = set()
    unique = []
    for p in programs:
        if p["url"] not in seen:
            seen.add(p["url"])
            unique.append(p)

    print(f"Found {len(unique)} program pages")
    return unique


def get_video_metadata(video_info: dict) -> dict | None:
    """Get video metadata using yt-dlp."""
    url = video_info["url"]

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
        print(f"Error getting metadata for {url}: {e}")

    return None


def extract_year(upload_date: str | None) -> int | None:
    """Extract year from upload date."""
    if not upload_date or len(upload_date) < 4:
        return None
    try:
        return int(upload_date[:4])
    except ValueError:
        return None


def process_video(video_info: dict, metadata: dict, program: dict) -> dict:
    """Process a video into our standard format."""
    video_id = video_info.get("video_id") or metadata.get("id", "")

    return {
        "source": "det_norske_teatret",
        "source_id": f"dnt_{video_id}",
        "title": metadata.get("title", program.get("title", "")),
        "description": metadata.get("description", ""),
        "year": extract_year(metadata.get("upload_date")),
        "duration_seconds": metadata.get("duration"),
        "url": video_info["url"],
        "thumbnail_url": metadata.get("thumbnail"),
        "platform": video_info["platform"],
        "language": "no",
        "venue": "Det Norske Teatret",
        "content_type": "documentary",  # Programs are typically supplementary material
        "raw_metadata": {
            "program_url": program.get("url"),
            "program_title": program.get("title"),
            "upload_date": metadata.get("upload_date"),
        }
    }


def harvest(min_duration: int = 900, output_dir: Path | None = None) -> list[dict]:
    """
    Harvest theatre content from Det Norske Teatret programs.

    Args:
        min_duration: Minimum duration in seconds (default 15 minutes)
        output_dir: Directory to save results

    Returns:
        List of harvested videos
    """
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "data" / "raw" / "det_norske_teatret"

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Harvesting Det Norske Teatret digital programs")
    print(f"Minimum duration: {min_duration // 60} minutes")
    print("=" * 60)

    # Get program list
    programs = get_program_list()

    # Scrape each program page for videos
    all_videos = []

    for i, program in enumerate(programs):
        print(f"\r[{i+1}/{len(programs)}] Scraping {program['slug']}...", end="", flush=True)
        time.sleep(0.5)

        soup = get_page(program["url"])
        if not soup:
            continue

        videos = extract_video_urls(soup)
        for v in videos:
            v["program"] = program
            all_videos.append(v)

    print()
    print(f"Found {len(all_videos)} videos across all programs")

    # Get metadata and filter
    results = []
    skipped_short = 0
    skipped_error = 0

    for i, video_info in enumerate(all_videos):
        print(f"\rProcessing {i+1}/{len(all_videos)}...", end="", flush=True)

        metadata = get_video_metadata(video_info)
        if not metadata:
            skipped_error += 1
            continue

        time.sleep(0.3)

        duration = metadata.get("duration", 0)
        if duration < min_duration:
            skipped_short += 1
            continue

        processed = process_video(video_info, metadata, video_info.get("program", {}))
        results.append(processed)

    print()
    print(f"\nResults: {len(results)} videos (15+ min)")
    print(f"Skipped: {skipped_short} too short, {skipped_error} errors")

    # Save results
    items_file = output_dir / "programs.json"
    with open(items_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Saved to: {items_file}")

    # Save metadata
    harvest_metadata = {
        "harvested_at": datetime.now().isoformat(),
        "total_videos": len(results),
        "min_duration_seconds": min_duration,
        "programs_scraped": len(programs),
        "skipped_short": skipped_short,
        "skipped_error": skipped_error,
        "source_url": BASE_URL,
    }
    metadata_file = output_dir / "harvest_metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(harvest_metadata, f, ensure_ascii=False, indent=2)

    return results


def main():
    parser = argparse.ArgumentParser(description="Harvest Det Norske Teatret programs")
    parser.add_argument(
        "--min-duration",
        type=int,
        default=900,
        help="Minimum duration in seconds (default: 900 = 15 minutes)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output directory (default: data/raw/det_norske_teatret)",
    )

    args = parser.parse_args()

    output_dir = Path(args.output) if args.output else None
    harvest(min_duration=args.min_duration, output_dir=output_dir)


if __name__ == "__main__":
    main()
