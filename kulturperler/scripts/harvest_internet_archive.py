#!/usr/bin/env python3
"""
Harvest theatre content from Internet Archive NRKTV collection.

The NRKTV collection contains Norwegian TV recordings, including
Fjernsynsteatret (Television Theatre) productions from the 1960s-1990s.

Usage:
    python harvest_internet_archive.py [--min-duration 900]
"""

import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path

import requests

SEARCH_API = "https://archive.org/advancedsearch.php"
METADATA_API = "https://archive.org/metadata"

# Search queries to find theatre content in the norwegian-television collection
SEARCH_QUERIES = [
    "collection:norwegian-television",
]


def parse_runtime(runtime_str: str) -> int | None:
    """Parse runtime string to seconds. Handles formats like '01:23:45' or '1:23:45'."""
    if not runtime_str:
        return None

    parts = runtime_str.split(":")
    try:
        if len(parts) == 3:
            hours, minutes, seconds = map(int, parts)
            return hours * 3600 + minutes * 60 + seconds
        elif len(parts) == 2:
            minutes, seconds = map(int, parts)
            return minutes * 60 + seconds
        elif len(parts) == 1:
            return int(parts[0])
    except (ValueError, TypeError):
        pass
    return None


def search_collection(query: str, fields: list[str] | None = None) -> list[dict]:
    """Search Internet Archive collection using the advanced search API."""
    if fields is None:
        fields = ["identifier", "title", "date", "description", "runtime", "creator"]

    items = []
    page = 1
    rows = 100

    while True:
        params = {
            "q": query,
            "fl[]": fields,
            "rows": rows,
            "page": page,
            "output": "json",
        }

        try:
            response = requests.get(SEARCH_API, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            print(f"Error fetching collection: {e}")
            break

        response_data = data.get("response", {})
        docs = response_data.get("docs", [])
        total = response_data.get("numFound", 0)

        items.extend(docs)
        print(f"  Fetched {len(docs)} items (total: {len(items)}/{total})")

        if len(items) >= total or not docs:
            break

        page += 1
        time.sleep(0.5)  # Rate limiting

    return items


def fetch_item_metadata(identifier: str) -> dict | None:
    """Fetch detailed metadata for a single item."""
    url = f"{METADATA_API}/{identifier}"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching metadata for {identifier}: {e}")
        return None


def extract_year(date_str: str | None) -> int | None:
    """Extract year from date string."""
    if not date_str:
        return None

    # Try to find a 4-digit year
    match = re.search(r"(19|20)\d{2}", str(date_str))
    if match:
        return int(match.group())
    return None


def extract_nrk_prf_id(identifier: str) -> str | None:
    """Extract NRK program ID from Internet Archive identifier."""
    # Pattern: NRKTV-FTRO003681-AR-199504039 -> FTRO003681
    # Pattern: NRKTV-FTEA005290-AR-199101002 -> FTEA005290
    match = re.search(r"NRKTV-([A-Za-z]+\d+)", identifier)
    if match:
        return match.group(1).upper()
    return None


def extract_nrk_url(metadata: dict) -> str | None:
    """Extract original NRK URL from metadata."""
    identifier = metadata.get("metadata", {}).get("identifier", "")

    prf_id = extract_nrk_prf_id(identifier)
    if prf_id:
        return f"https://tv.nrk.no/se?v={prf_id}"

    # Check for external-identifier field
    ext_ids = metadata.get("metadata", {}).get("external-identifier", [])
    if isinstance(ext_ids, str):
        ext_ids = [ext_ids]

    for ext_id in ext_ids:
        if "nrk.no" in ext_id:
            return ext_id

    return None


def process_item(item: dict, detailed_metadata: dict | None = None) -> dict:
    """Process an item into our standard format."""
    metadata = detailed_metadata.get("metadata", {}) if detailed_metadata else {}

    # Get runtime - try multiple sources
    runtime_str = item.get("runtime") or metadata.get("runtime")
    duration_seconds = parse_runtime(runtime_str)

    # Get thumbnail URL
    identifier = item.get("identifier", "")
    thumbnail_url = None
    if detailed_metadata:
        files = detailed_metadata.get("files", [])
        for f in files:
            if f.get("format") in ["JPEG Thumb", "Thumbnail", "PNG"]:
                thumbnail_url = f"https://archive.org/download/{identifier}/{f.get('name')}"
                break

    # Extract NRK program ID for deduplication
    nrk_prf_id = extract_nrk_prf_id(identifier)

    return {
        "source": "internet_archive",
        "source_id": identifier,
        "nrk_prf_id": nrk_prf_id,  # For deduplication with existing episodes
        "title": item.get("title", ""),
        "description": item.get("description") or metadata.get("description", ""),
        "year": extract_year(item.get("date") or metadata.get("date")),
        "duration_seconds": duration_seconds,
        "url": f"https://archive.org/details/{identifier}",
        "nrk_url": extract_nrk_url(detailed_metadata) if detailed_metadata else None,
        "thumbnail_url": thumbnail_url,
        "platform": "internet_archive",
        "language": "no",
        "content_type": "full_performance",  # Most NRKTV theatre content is full recordings
        "raw_metadata": {
            "creator": item.get("creator"),
            "runtime": runtime_str,
            "date": item.get("date"),
        }
    }


def is_theatre_content(item: dict, metadata: dict | None) -> bool:
    """Check if an item is likely theatre content."""
    title = (item.get("title") or "").lower()
    description = (item.get("description") or "").lower()

    # Check metadata if available
    if metadata:
        meta = metadata.get("metadata", {})
        subjects = meta.get("subject", [])
        if isinstance(subjects, str):
            subjects = [subjects]
        subjects_lower = [s.lower() for s in subjects]

        if any(kw in subjects_lower for kw in ["teater", "theatre", "drama", "fjernsynsteatret"]):
            return True

    # Keywords that indicate theatre content
    theatre_keywords = [
        "teater", "teatret", "theatre", "drama", "komedie",
        "forestilling", "premiere", "ibsen", "holberg",
        "akt", "scene", "skuespill"
    ]

    text = f"{title} {description}"
    return any(kw in text for kw in theatre_keywords)


def harvest(min_duration: int = 900, output_dir: Path | None = None) -> list[dict]:
    """
    Harvest theatre content from Internet Archive.

    Args:
        min_duration: Minimum duration in seconds (default 15 minutes)
        output_dir: Directory to save results

    Returns:
        List of harvested items
    """
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "data" / "raw" / "internet_archive"

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Harvesting Internet Archive NRKTV collection")
    print("=" * 60)

    all_items = {}  # Use dict to deduplicate by identifier

    for query in SEARCH_QUERIES:
        print(f"\nSearching: {query}")
        items = search_collection(query)

        for item in items:
            identifier = item.get("identifier")
            if identifier and identifier not in all_items:
                all_items[identifier] = item

    print(f"\nFound {len(all_items)} unique items")

    # Process items and fetch detailed metadata
    results = []
    skipped_short = 0
    skipped_non_theatre = 0

    for i, (identifier, item) in enumerate(all_items.items()):
        print(f"\rProcessing {i+1}/{len(all_items)}: {identifier[:50]}...", end="", flush=True)

        # Fetch detailed metadata
        detailed = fetch_item_metadata(identifier)
        time.sleep(0.3)  # Rate limiting

        # Check if it's theatre content
        if not is_theatre_content(item, detailed):
            skipped_non_theatre += 1
            continue

        # Process item
        processed = process_item(item, detailed)

        # Filter by duration
        duration = processed.get("duration_seconds")
        if duration and duration < min_duration:
            skipped_short += 1
            continue

        results.append(processed)

    print()
    print(f"\nResults: {len(results)} theatre items (15+ min)")
    print(f"Skipped: {skipped_short} too short, {skipped_non_theatre} non-theatre")

    # Save results
    items_file = output_dir / "items.json"
    with open(items_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Saved to: {items_file}")

    # Save metadata
    metadata = {
        "harvested_at": datetime.now().isoformat(),
        "total_items": len(results),
        "min_duration_seconds": min_duration,
        "queries": SEARCH_QUERIES,
        "skipped_short": skipped_short,
        "skipped_non_theatre": skipped_non_theatre,
    }
    metadata_file = output_dir / "harvest_metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    return results


def main():
    parser = argparse.ArgumentParser(description="Harvest Internet Archive NRKTV collection")
    parser.add_argument(
        "--min-duration",
        type=int,
        default=900,
        help="Minimum duration in seconds (default: 900 = 15 minutes)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output directory (default: data/raw/internet_archive)",
    )

    args = parser.parse_args()

    output_dir = Path(args.output) if args.output else None
    harvest(min_duration=args.min_duration, output_dir=output_dir)


if __name__ == "__main__":
    main()
