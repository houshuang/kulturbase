"""NRK PSAPI client for fetching program metadata."""

import requests
import time
from typing import Iterator
from dataclasses import dataclass


BASE_URL = "https://psapi.nrk.no"


@dataclass
class Episode:
    prf_id: str
    title: str
    description: str
    year: int
    duration_seconds: int
    image_url: str
    nrk_url: str
    contributors: list[dict]
    release_date: str


def fetch_series_instalments(series_id: str, delay: float = 1.0) -> Iterator[dict]:
    """Fetch all instalments for a series, handling pagination by year."""
    # First, get series info to find all seasons
    series_url = f"{BASE_URL}/series/{series_id}"
    resp = requests.get(series_url, timeout=30)
    resp.raise_for_status()
    series_data = resp.json()

    seasons = series_data.get("seasons", [])
    print(f"Found {len(seasons)} seasons for {series_id}")

    # Fetch instalments starting from newest year
    page = None
    seen_ids = set()

    # Start from the newest season
    if seasons:
        page = seasons[0]["name"]  # Usually the year like "1999"

    while True:
        url = f"{BASE_URL}/tv/catalog/series/{series_id}/instalments"
        params = {"pageSize": 50}
        if page:
            params["page"] = page

        print(f"Fetching instalments page={page}...")
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        instalments = data.get("_embedded", {}).get("instalments", [])

        for inst in instalments:
            inst_id = inst.get("prfId")
            if inst_id and inst_id not in seen_ids:
                seen_ids.add(inst_id)
                yield inst

        # Check for next page
        links = data.get("_links", {})
        if "next" not in links:
            break

        # Extract next page from URL
        next_href = links["next"]["href"]
        if "page=" in next_href:
            page = next_href.split("page=")[1].split("&")[0]
        else:
            break

        time.sleep(delay)

    print(f"Total unique instalments: {len(seen_ids)}")


def fetch_program_details(prf_id: str) -> dict:
    """Fetch detailed metadata for a program."""
    url = f"{BASE_URL}/programs/{prf_id}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_playback_metadata(prf_id: str) -> dict:
    """Fetch playback metadata including availability."""
    url = f"{BASE_URL}/playback/metadata/program/{prf_id}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def parse_duration(duration_str: str) -> int:
    """Parse ISO 8601 duration to seconds. E.g., 'PT1H18M14.56S' -> 4694"""
    if not duration_str or not duration_str.startswith("PT"):
        return 0

    duration_str = duration_str[2:]  # Remove 'PT'
    seconds = 0

    # Hours
    if "H" in duration_str:
        hours, duration_str = duration_str.split("H")
        seconds += int(hours) * 3600

    # Minutes
    if "M" in duration_str:
        minutes, duration_str = duration_str.split("M")
        seconds += int(minutes) * 60

    # Seconds
    if "S" in duration_str:
        secs = duration_str.rstrip("S")
        seconds += int(float(secs))

    return seconds


def instalment_to_episode(inst: dict) -> dict:
    """Convert API instalment format to our Episode format."""
    # Get best image URL (prefer larger)
    images = inst.get("image", [])
    image_url = ""
    if images:
        # Sort by width, get largest
        sorted_images = sorted(images, key=lambda x: x.get("width", 0), reverse=True)
        image_url = sorted_images[0].get("url", "")

    prf_id = inst.get("prfId", "")

    return {
        "prf_id": prf_id,
        "title": inst.get("titles", {}).get("title", ""),
        "description": inst.get("titles", {}).get("subtitle", ""),
        "year": inst.get("productionYear"),
        "duration_seconds": parse_duration(inst.get("duration", "")),
        "image_url": image_url,
        "nrk_url": f"https://tv.nrk.no/se?v={prf_id}",
        "contributors": inst.get("contributors", []),
        "release_date": inst.get("releaseDateOnDemand", ""),
        "availability": inst.get("availability", {}),
    }


if __name__ == "__main__":
    # Quick test
    print("Testing NRK API...")

    count = 0
    for inst in fetch_series_instalments("fjernsynsteatret", delay=0.5):
        ep = instalment_to_episode(inst)
        print(f"  {ep['year']} - {ep['title'][:50]}")
        count += 1
        if count >= 5:
            break

    print(f"\nTest complete. Found {count} episodes.")
