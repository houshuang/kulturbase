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


def instalment_to_episode(inst: dict, medium: str = "tv") -> dict:
    """Convert API instalment format to our Episode format."""
    # Get best image URL (prefer larger)
    images = inst.get("image", [])
    image_url = ""
    if images:
        # Sort by width, get largest
        sorted_images = sorted(images, key=lambda x: x.get("width", 0), reverse=True)
        image_url = sorted_images[0].get("url", "")

    prf_id = inst.get("prfId", "") or inst.get("episodeId", "")

    # Build appropriate NRK URL based on medium
    if medium == "radio":
        nrk_url = f"https://radio.nrk.no/serie/radioteatret/{prf_id}"
    else:
        nrk_url = f"https://tv.nrk.no/se?v={prf_id}"

    return {
        "prf_id": prf_id,
        "title": inst.get("titles", {}).get("title", ""),
        "description": inst.get("titles", {}).get("subtitle", ""),
        "year": inst.get("productionYear"),
        "duration_seconds": parse_duration(inst.get("duration", "")) or inst.get("durationInSeconds", 0),
        "image_url": image_url,
        "nrk_url": nrk_url,
        "contributors": inst.get("contributors", []),
        "release_date": inst.get("releaseDateOnDemand", "") or inst.get("date", ""),
        "availability": inst.get("availability", {}),
        "medium": medium,
    }


def fetch_radio_series_seasons(series_id: str) -> list[dict]:
    """Fetch all seasons for a radio series with on-demand availability."""
    series_url = f"{BASE_URL}/series/{series_id}"
    resp = requests.get(series_url, timeout=30)
    resp.raise_for_status()
    series_data = resp.json()

    seasons = series_data.get("seasons", [])
    # Filter to seasons with available episodes
    return [s for s in seasons if s.get("hasOnDemandRightsEpisodes", True)]


def fetch_radio_season_episodes(series_id: str, season_id: str, delay: float = 0.5) -> Iterator[dict]:
    """Fetch all episodes for a radio series season using the series endpoint."""
    # Use the /series endpoint which has more complete data
    url = f"{BASE_URL}/series/{series_id}/seasons/{season_id}/episodes"

    resp = requests.get(url, timeout=30)
    if resp.status_code == 404:
        return

    resp.raise_for_status()
    episodes = resp.json()

    if isinstance(episodes, list):
        for ep in episodes:
            yield ep


def fetch_radio_series_instalments(series_id: str, delay: float = 1.0) -> Iterator[dict]:
    """Fetch all instalments for a radio series by iterating through seasons."""
    seasons = fetch_radio_series_seasons(series_id)
    print(f"Found {len(seasons)} seasons for radio series {series_id}")

    seen_ids = set()

    for season in seasons:
        season_id = season.get("id") or season.get("name")
        print(f"Fetching radio season {season_id}...")

        for ep in fetch_radio_season_episodes(series_id, season_id, delay=delay):
            ep_id = ep.get("id") or ep.get("prfId")
            if ep_id and ep_id not in seen_ids:
                seen_ids.add(ep_id)
                yield ep

        time.sleep(delay)

    print(f"Total unique radio episodes: {len(seen_ids)}")


def fetch_all_hoerespill_series() -> list[dict]:
    """Fetch all series from the hørespill (radio drama) page."""
    url = f"{BASE_URL}/radio/pages/hoerespill"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    series_list = []
    for section in data.get("sections", []):
        if "included" in section:
            for plug in section["included"].get("plugs", []):
                if plug.get("type") == "series" and "_links" in plug:
                    link = plug["_links"].get("series", "")
                    series_id = link.split("/")[-1] if link else ""
                    if series_id:
                        series_info = plug.get("series", {})
                        series_list.append({
                            "id": series_id,
                            "title": series_info.get("titles", {}).get("title", ""),
                            "subtitle": series_info.get("titles", {}).get("subtitle", ""),
                            "numberOfEpisodes": series_info.get("numberOfEpisodes", 0),
                        })

    # Remove duplicates (some series appear in multiple sections)
    seen_ids = set()
    unique_series = []
    for s in series_list:
        if s["id"] not in seen_ids:
            seen_ids.add(s["id"])
            unique_series.append(s)

    return unique_series


def series_episode_to_episode(ep: dict, series_id: str) -> dict:
    """Convert series endpoint episode format to our Episode format."""
    # Get best image URL (prefer larger)
    image_data = ep.get("image", {})
    images = image_data.get("webImages", [])
    image_url = ""
    if images:
        # Sort by width, get largest
        sorted_images = sorted(images, key=lambda x: x.get("pixelWidth", 0), reverse=True)
        image_url = sorted_images[0].get("imageUrl", "")

    prf_id = ep.get("id", "")

    # Extract year from release date or use production year
    year = None
    release_date = ep.get("releaseDateOnDemand", "")
    if release_date:
        try:
            year = int(release_date[:4])
        except (ValueError, IndexError):
            pass

    # Build radio NRK URL
    nrk_url = f"https://radio.nrk.no/serie/{series_id}/{prf_id.lower()}"

    # Extract contributors
    contributors = []
    for c in ep.get("programAndIndexPointsContributors", []):
        contributors.append({
            "name": c.get("name", ""),
            "role": c.get("role", ""),
        })

    return {
        "prf_id": prf_id,
        "title": ep.get("title", "") or ep.get("episodeTitle", ""),
        "description": ep.get("shortDescription", "") or ep.get("longDescription", ""),
        "year": year,
        "duration_seconds": parse_duration(ep.get("duration", "")),
        "image_url": image_url,
        "nrk_url": nrk_url,
        "contributors": contributors,
        "release_date": release_date,
        "availability": {},
        "medium": "radio",
        "series_id": series_id,
        "series_title": ep.get("seriesTitle", ""),
        "episode_number": ep.get("episodeNumber"),
        "total_episodes": ep.get("totalEpisodesInSeason"),
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
