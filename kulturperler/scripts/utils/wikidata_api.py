"""Wikidata API client for fetching play and person metadata."""

import requests
from typing import Optional
from dataclasses import dataclass


WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKIPEDIA_API = "https://no.wikipedia.org/w/api.php"


# Wikidata property IDs
P_AUTHOR = "P50"
P_PUBLICATION_DATE = "P577"
P_ORIGINAL_TITLE = "P1476"
P_ORIGINAL_LANGUAGE = "P364"
P_INSTANCE_OF = "P31"
P_DATE_OF_BIRTH = "P569"
P_DATE_OF_DEATH = "P570"
P_COUNTRY_OF_CITIZENSHIP = "P27"


@dataclass
class WikidataPlay:
    """Play information from Wikidata."""
    wikidata_id: str
    title: str
    original_title: Optional[str] = None
    author_wikidata_id: Optional[str] = None
    author_name: Optional[str] = None
    year_written: Optional[int] = None
    wikipedia_url: Optional[str] = None


@dataclass
class WikidataPerson:
    """Person information from Wikidata."""
    wikidata_id: str
    name: str
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    nationality: Optional[str] = None
    wikipedia_url: Optional[str] = None


def search_plays(query: str, language: str = "no") -> list[dict]:
    """Search Wikidata for plays matching the query."""
    params = {
        "action": "wbsearchentities",
        "search": query,
        "language": language,
        "format": "json",
        "limit": 10,
    }

    resp = requests.get(WIKIDATA_API, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("search", []):
        results.append({
            "wikidata_id": item["id"],
            "title": item.get("label", ""),
            "description": item.get("description", ""),
            "aliases": item.get("aliases", []),
        })

    return results


def fetch_entity(wikidata_id: str) -> Optional[dict]:
    """Fetch full entity data from Wikidata."""
    params = {
        "action": "wbgetentities",
        "ids": wikidata_id,
        "props": "labels|descriptions|claims|sitelinks",
        "languages": "no|nb|en",
        "format": "json",
    }

    resp = requests.get(WIKIDATA_API, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    entities = data.get("entities", {})
    return entities.get(wikidata_id)


def extract_year_from_time(time_value: dict) -> Optional[int]:
    """Extract year from Wikidata time value."""
    time_str = time_value.get("value", {}).get("time", "")
    if time_str:
        # Format: +1879-12-04T00:00:00Z
        if time_str.startswith("+"):
            time_str = time_str[1:]
        parts = time_str.split("-")
        if parts:
            try:
                return int(parts[0])
            except ValueError:
                pass
    return None


def get_claim_value(entity: dict, property_id: str) -> Optional[dict]:
    """Get the first claim value for a property."""
    claims = entity.get("claims", {})
    prop_claims = claims.get(property_id, [])
    if prop_claims:
        return prop_claims[0].get("mainsnak", {}).get("datavalue")
    return None


def get_label(entity: dict, languages: list[str] = None) -> str:
    """Get label in preferred language order."""
    if languages is None:
        languages = ["no", "nb", "en"]

    labels = entity.get("labels", {})
    for lang in languages:
        if lang in labels:
            return labels[lang].get("value", "")
    return ""


def get_wikipedia_url(entity: dict, wiki: str = "nowiki") -> Optional[str]:
    """Get Wikipedia URL from sitelinks."""
    sitelinks = entity.get("sitelinks", {})
    if wiki in sitelinks:
        title = sitelinks[wiki].get("title", "")
        if title:
            return f"https://no.wikipedia.org/wiki/{title.replace(' ', '_')}"
    return None


def fetch_play_info(wikidata_id: str) -> Optional[WikidataPlay]:
    """Fetch play information from Wikidata."""
    entity = fetch_entity(wikidata_id)
    if not entity:
        return None

    title = get_label(entity)

    # Get original title
    original_title = None
    orig_title_value = get_claim_value(entity, P_ORIGINAL_TITLE)
    if orig_title_value and orig_title_value.get("type") == "monolingualtext":
        original_title = orig_title_value.get("value", {}).get("text")

    # Get author
    author_id = None
    author_name = None
    author_value = get_claim_value(entity, P_AUTHOR)
    if author_value and author_value.get("type") == "wikibase-entityid":
        author_id = author_value.get("value", {}).get("id")
        if author_id:
            author_entity = fetch_entity(author_id)
            if author_entity:
                author_name = get_label(author_entity)

    # Get publication year
    year_written = None
    pub_date_value = get_claim_value(entity, P_PUBLICATION_DATE)
    if pub_date_value and pub_date_value.get("type") == "time":
        year_written = extract_year_from_time(pub_date_value)

    # Get Wikipedia URL
    wikipedia_url = get_wikipedia_url(entity)

    return WikidataPlay(
        wikidata_id=wikidata_id,
        title=title,
        original_title=original_title,
        author_wikidata_id=author_id,
        author_name=author_name,
        year_written=year_written,
        wikipedia_url=wikipedia_url,
    )


def fetch_person_info(wikidata_id: str) -> Optional[WikidataPerson]:
    """Fetch person information from Wikidata."""
    entity = fetch_entity(wikidata_id)
    if not entity:
        return None

    name = get_label(entity)

    # Get birth year
    birth_year = None
    birth_value = get_claim_value(entity, P_DATE_OF_BIRTH)
    if birth_value and birth_value.get("type") == "time":
        birth_year = extract_year_from_time(birth_value)

    # Get death year
    death_year = None
    death_value = get_claim_value(entity, P_DATE_OF_DEATH)
    if death_value and death_value.get("type") == "time":
        death_year = extract_year_from_time(death_value)

    # Get nationality
    nationality = None
    nat_value = get_claim_value(entity, P_COUNTRY_OF_CITIZENSHIP)
    if nat_value and nat_value.get("type") == "wikibase-entityid":
        nat_id = nat_value.get("value", {}).get("id")
        if nat_id:
            nat_entity = fetch_entity(nat_id)
            if nat_entity:
                nationality = get_label(nat_entity)

    # Get Wikipedia URL
    wikipedia_url = get_wikipedia_url(entity)

    return WikidataPerson(
        wikidata_id=wikidata_id,
        name=name,
        birth_year=birth_year,
        death_year=death_year,
        nationality=nationality,
        wikipedia_url=wikipedia_url,
    )


def search_and_match_play(title: str) -> Optional[WikidataPlay]:
    """Search for a play by title and return best match."""
    results = search_plays(title)

    if not results:
        return None

    # Look for plays in description
    for result in results:
        desc = result.get("description", "").lower()
        if any(word in desc for word in ["play", "skuespill", "drama", "teater"]):
            return fetch_play_info(result["wikidata_id"])

    # Return first result if no play-specific match
    if results:
        return fetch_play_info(results[0]["wikidata_id"])

    return None


if __name__ == "__main__":
    # Quick test
    print("Testing Wikidata API...")

    print("\n1. Searching for 'Et dukkehjem'...")
    results = search_plays("Et dukkehjem")
    for r in results[:3]:
        print(f"   - {r['title']} ({r['wikidata_id']}): {r['description']}")

    print("\n2. Fetching play info for Q669694 (Et dukkehjem)...")
    play = fetch_play_info("Q669694")
    if play:
        print(f"   Title: {play.title}")
        print(f"   Original title: {play.original_title}")
        print(f"   Author: {play.author_name} ({play.author_wikidata_id})")
        print(f"   Year: {play.year_written}")
        print(f"   Wikipedia: {play.wikipedia_url}")

    print("\n3. Fetching person info for Q36661 (Henrik Ibsen)...")
    person = fetch_person_info("Q36661")
    if person:
        print(f"   Name: {person.name}")
        print(f"   Years: {person.birth_year} - {person.death_year}")
        print(f"   Nationality: {person.nationality}")
        print(f"   Wikipedia: {person.wikipedia_url}")

    print("\nTest complete!")
