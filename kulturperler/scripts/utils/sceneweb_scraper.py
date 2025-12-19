"""Sceneweb scraper for fetching play and person metadata."""

import re
import time
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote, urljoin


BASE_URL = "https://sceneweb.no"


@dataclass
class ScenewebArtwork:
    """Original work (play) from Sceneweb."""
    sceneweb_id: int
    title: str
    url: str
    playwright_name: Optional[str] = None
    playwright_sceneweb_id: Optional[int] = None
    year_written: Optional[int] = None
    description: Optional[str] = None


@dataclass
class ScenewebPerson:
    """Person from Sceneweb."""
    sceneweb_id: int
    name: str
    url: str
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    roles: list[str] = None


def search_artworks(query: str, delay: float = 2.0) -> list[dict]:
    """Search Sceneweb for original works (plays)."""
    url = f"{BASE_URL}/sok"
    params = {
        "q": query,
        "o": "Originalverk",  # Filter to original works only
    }

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    # Find search result items - try multiple selectors
    items = soup.select(".search-result") or soup.select("a[href*='/nb/artwork/']")

    for item in items:
        # Get the link element
        if item.name == 'a':
            link = item
        else:
            link = item.select_one("a[href*='/nb/artwork/']")
        if not link:
            continue

        href = link.get("href", "")
        # Extract ID from URL like /nb/artwork/2890/Et_dukkehjem
        match = re.search(r"/nb/artwork/(\d+)/", href)
        if not match:
            continue

        sceneweb_id = int(match.group(1))

        # Get title - try to find heading element first
        title_elem = link.select_one("h1, h2, h3, h4, strong") or link
        title = title_elem.get_text(strip=True)
        # Clean up title - remove type labels and descriptions
        title = re.sub(r'Originalverk.*$', '', title).strip()
        title = re.sub(r'Person.*$', '', title).strip()

        results.append({
            "sceneweb_id": sceneweb_id,
            "title": title,
            "url": urljoin(BASE_URL, href),
        })

    time.sleep(delay)
    return results


def fetch_artwork_details(sceneweb_id: int, title_slug: str = "", delay: float = 2.0) -> Optional[ScenewebArtwork]:
    """Fetch detailed information about an artwork."""
    if title_slug:
        url = f"{BASE_URL}/nb/artwork/{sceneweb_id}/{quote(title_slug)}"
    else:
        url = f"{BASE_URL}/nb/artwork/{sceneweb_id}/"

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching artwork {sceneweb_id}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Get title
    title_elem = soup.select_one("h1, .page-title")
    title = title_elem.get_text(strip=True) if title_elem else ""

    # Get description
    desc_elem = soup.select_one(".description, .lead, p")
    description = desc_elem.get_text(strip=True) if desc_elem else ""

    # Try to find playwright from the page
    playwright_name = None
    playwright_id = None

    # Look for author link in table or metadata
    for link in soup.select("a[href*='/nb/artist/']"):
        href = link.get("href", "")
        # Check if this is in a context suggesting playwright/author
        parent_text = link.parent.get_text() if link.parent else ""
        if any(word in parent_text.lower() for word in ["forfatter", "dramatiker", "author", "skrevet av"]):
            playwright_name = link.get_text(strip=True)
            match = re.search(r"/nb/artist/(\d+)/", href)
            if match:
                playwright_id = int(match.group(1))
            break

    # If not found in specific context, look in table rows
    if not playwright_name:
        for row in soup.select("tr"):
            cells = row.select("td")
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True).lower()
                if any(word in label for word in ["forfatter", "dramatiker", "skrevet"]):
                    link = cells[1].select_one("a[href*='/nb/artist/']")
                    if link:
                        playwright_name = link.get_text(strip=True)
                        href = link.get("href", "")
                        match = re.search(r"/nb/artist/(\d+)/", href)
                        if match:
                            playwright_id = int(match.group(1))
                        break

    # Try to extract year from description
    year_written = None
    if description:
        year_match = re.search(r"\b(1[5-9]\d{2}|20[0-2]\d)\b", description)
        if year_match:
            year_written = int(year_match.group(1))

    time.sleep(delay)

    return ScenewebArtwork(
        sceneweb_id=sceneweb_id,
        title=title,
        url=url,
        playwright_name=playwright_name,
        playwright_sceneweb_id=playwright_id,
        year_written=year_written,
        description=description[:500] if description else None,
    )


def fetch_person_details(sceneweb_id: int, name_slug: str = "", delay: float = 2.0) -> Optional[ScenewebPerson]:
    """Fetch detailed information about a person."""
    if name_slug:
        url = f"{BASE_URL}/nb/artist/{sceneweb_id}/{quote(name_slug)}"
    else:
        url = f"{BASE_URL}/nb/artist/{sceneweb_id}/"

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching person {sceneweb_id}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Get name
    name_elem = soup.select_one("h1, .page-title")
    name = name_elem.get_text(strip=True) if name_elem else ""

    # Try to find birth/death years
    birth_year = None
    death_year = None

    # Look for dates in format like "20. mars 1828 – 23. mai 1906"
    for text in soup.stripped_strings:
        date_match = re.search(r"(\d{4})\s*[–-]\s*(\d{4})", text)
        if date_match:
            birth_year = int(date_match.group(1))
            death_year = int(date_match.group(2))
            break

        # Also check for just birth year
        birth_match = re.search(r"[Ff]ødt\s+.*?(\d{4})", text)
        if birth_match:
            birth_year = int(birth_match.group(1))

    time.sleep(delay)

    return ScenewebPerson(
        sceneweb_id=sceneweb_id,
        name=name,
        url=url,
        birth_year=birth_year,
        death_year=death_year,
        roles=[],
    )


def match_title_to_artwork(title: str, delay: float = 2.0) -> Optional[ScenewebArtwork]:
    """Search for a title and return the best matching artwork."""
    # Clean up title for search
    clean_title = re.sub(r"\s*\([^)]*\)\s*", "", title)  # Remove parenthetical
    clean_title = re.sub(r"\s*-\s*.*$", "", clean_title)  # Remove after dash
    clean_title = clean_title.strip()

    if not clean_title:
        return None

    results = search_artworks(clean_title, delay=delay)

    if not results:
        return None

    # Try to find exact match first
    for result in results:
        if result["title"].lower() == clean_title.lower():
            return fetch_artwork_details(
                result["sceneweb_id"],
                delay=delay
            )

    # Otherwise return first result
    if results:
        return fetch_artwork_details(results[0]["sceneweb_id"], delay=delay)

    return None


if __name__ == "__main__":
    # Quick test
    print("Testing Sceneweb scraper...")

    print("\n1. Searching for 'Et dukkehjem'...")
    results = search_artworks("Et dukkehjem")
    for r in results[:3]:
        print(f"   - {r['title']} (ID: {r['sceneweb_id']})")

    print("\n2. Fetching artwork details for ID 2890...")
    artwork = fetch_artwork_details(2890, "Et_dukkehjem")
    if artwork:
        print(f"   Title: {artwork.title}")
        print(f"   Playwright: {artwork.playwright_name} (ID: {artwork.playwright_sceneweb_id})")
        print(f"   Year: {artwork.year_written}")

    print("\n3. Fetching person details for Henrik Ibsen (ID 3317)...")
    person = fetch_person_details(3317, "Henrik_Ibsen")
    if person:
        print(f"   Name: {person.name}")
        print(f"   Years: {person.birth_year} - {person.death_year}")

    print("\nTest complete!")
