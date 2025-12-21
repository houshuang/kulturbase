#!/usr/bin/env python3
"""
Phase 1: Discover classical music series from NRK APIs.

Searches TV and radio APIs using various keywords and fetches known series directly.
Outputs: output/classical_series_discovered.json
"""

import requests
import json
import time
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_FILE = OUTPUT_DIR / "classical_series_discovered.json"

HEADERS = {'User-Agent': 'Kulturperler/1.0 (educational project)'}

# Search queries to find classical music content
SEARCH_QUERIES = [
    # Norwegian terms
    "ballett", "ballet", "opera", "operetter", "symfoni", "symphony",
    "orkester", "konsert klassisk", "klassisk musikk", "filharmoni",
    "kammermusikk", "strykekvartett",
    # Composer names (Norwegian spellings)
    "Tsjajkovskij", "Grieg", "Mozart", "Beethoven", "Wagner", "Verdi",
    "Puccini", "Bizet", "Brahms", "Strauss", "Sibelius", "Svendsen",
    "Halvorsen", "Nordheim", "Sæverud",
    # Famous works
    "Svanesjøen", "Nøtteknekkeren", "Tornerose", "Carmen", "Tosca",
    "La Traviata", "Fidelio", "Peer Gynt suite", "Holberg-suiten",
    # Program types
    "operahøydepunkter", "ballettgalla", "nyttårskonsert",
]

# Known relevant series to fetch directly
KNOWN_TV_SERIES = [
    "opera-og-operetter",
    "ballett-og-dans",
    "klassiske-opplevelser",
    "norske-symfonier",
    "nrk-klassisk-oenskekonsert",
    "aapningsgalla-den-norske-opera-og-ballett",
    "ballettens-historie-og-estetikk",
    "solistgalla-med-stavanger-symfoniorkester",
    "filmmusikk-konserter",
    "nrk-musikk-konsert",
    "nordisk-konsert",
    "eventyret-om-tornerose",
    "klassisk-jul-2025",
    "musikk-musikk",
]

# Known radio series
KNOWN_RADIO_SERIES = [
    # Add radio series if discovered
]


def search_nrk(query, page_size=50):
    """Search NRK TV API for programs."""
    url = f"https://psapi.nrk.no/search?q={requests.utils.quote(query)}&pageSize={page_size}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.ok:
            return resp.json()
    except Exception as e:
        print(f"  Error searching for '{query}': {e}")
    return None


def get_tv_series(series_id):
    """Get TV series details."""
    url = f"https://psapi.nrk.no/tv/catalog/series/{series_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.ok:
            return resp.json()
    except Exception as e:
        print(f"  Error fetching TV series '{series_id}': {e}")
    return None


def get_radio_series(series_id):
    """Get radio series details."""
    url = f"https://psapi.nrk.no/radio/catalog/series/{series_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.ok:
            return resp.json()
    except Exception as e:
        print(f"  Error fetching radio series '{series_id}': {e}")
    return None


def extract_series_info(hit, hit_type):
    """Extract series info from a search hit."""
    return {
        'id': hit.get('id', ''),
        'title': hit.get('title', ''),
        'description': hit.get('description', ''),
        'type': hit_type,
        'source_medium': hit.get('sourceMedium', 'unknown'),
        'url': hit.get('url', ''),
        'has_rights': hit.get('hasRights', False),
    }


def extract_program_info(hit):
    """Extract program info from a search hit."""
    usage_rights = hit.get('usageRights', {})

    # Parse expiry date
    expiry_date = None
    available_to = usage_rights.get('availableTo', '')
    if available_to and 'Date(' in available_to:
        try:
            ms = int(available_to.split('(')[1].split('+')[0])
            expiry_date = datetime.fromtimestamp(ms / 1000).isoformat()
        except:
            pass

    return {
        'id': hit.get('id', ''),
        'title': hit.get('title', ''),
        'description': hit.get('description', ''),
        'type': 'program',
        'source_medium': hit.get('sourceMedium', 'unknown'),
        'url': hit.get('url', ''),
        'has_rights': hit.get('hasRights', False),
        'expiry_date': expiry_date,
        'duration': hit.get('duration', 0),
    }


def main():
    print("=" * 60)
    print("Phase 1: Discovering Classical Music Series from NRK")
    print("=" * 60)

    OUTPUT_DIR.mkdir(exist_ok=True)

    discovered_series = {}
    discovered_programs = {}

    # 1. Search with various keywords
    print("\n[1/3] Searching with keywords...")
    for query in SEARCH_QUERIES:
        print(f"  Searching: {query}")
        results = search_nrk(query)
        time.sleep(0.3)  # Rate limiting

        if not results:
            continue

        hits = results.get('hits', [])
        for hit_wrapper in hits:
            hit = hit_wrapper.get('hit', hit_wrapper)
            hit_type = hit_wrapper.get('type', '')
            hit_id = hit.get('id', '')

            if not hit_id:
                continue

            if hit_type == 'serie':
                if hit_id not in discovered_series:
                    discovered_series[hit_id] = extract_series_info(hit, 'serie')
                    discovered_series[hit_id]['discovered_via'] = query
            elif hit_type == 'program':
                if hit_id not in discovered_programs:
                    discovered_programs[hit_id] = extract_program_info(hit)
                    discovered_programs[hit_id]['discovered_via'] = query
            elif hit_type == 'episode':
                if hit_id not in discovered_programs:
                    discovered_programs[hit_id] = extract_program_info(hit)
                    discovered_programs[hit_id]['type'] = 'episode'
                    discovered_programs[hit_id]['discovered_via'] = query

    print(f"  Found {len(discovered_series)} series and {len(discovered_programs)} programs from search")

    # 2. Fetch known TV series directly
    print("\n[2/3] Fetching known TV series...")
    for series_id in KNOWN_TV_SERIES:
        if series_id in discovered_series:
            print(f"  Skipping {series_id} (already discovered)")
            continue

        print(f"  Fetching: {series_id}")
        series_data = get_tv_series(series_id)
        time.sleep(0.3)

        if series_data:
            standard = series_data.get('standard', {})
            titles = standard.get('titles', {})
            nav = series_data.get('navigation', {})

            # Extract seasons info
            seasons = []
            for section in nav.get('sections', []):
                if section.get('type') == 'subnavigation':
                    for sub in section.get('sections', []):
                        if sub.get('type') == 'season':
                            seasons.append({
                                'id': sub.get('id'),
                                'title': sub.get('title'),
                                'status': sub.get('status'),
                            })

            discovered_series[series_id] = {
                'id': series_id,
                'title': titles.get('title', series_id),
                'description': titles.get('subtitle', ''),
                'type': 'serie',
                'source_medium': 'tv',
                'discovered_via': 'known_series',
                'seasons': seasons,
                'season_count': len(seasons),
            }
            print(f"    Found {len(seasons)} seasons")
        else:
            print(f"    Not found or unavailable")

    # 3. Fetch known radio series directly
    print("\n[3/3] Fetching known radio series...")
    for series_id in KNOWN_RADIO_SERIES:
        if series_id in discovered_series:
            print(f"  Skipping {series_id} (already discovered)")
            continue

        print(f"  Fetching: {series_id}")
        series_data = get_radio_series(series_id)
        time.sleep(0.3)

        if series_data:
            series_info = series_data.get('series', {})
            titles = series_info.get('titles', {})
            embedded = series_data.get('_embedded', {})
            seasons = embedded.get('seasons', [])

            discovered_series[series_id] = {
                'id': series_id,
                'title': titles.get('title', series_id),
                'description': titles.get('subtitle', ''),
                'type': 'serie',
                'source_medium': 'radio',
                'discovered_via': 'known_series',
                'seasons': [{'id': s.get('id'), 'title': s.get('titles', {}).get('title')} for s in seasons],
                'season_count': len(seasons),
            }
            print(f"    Found {len(seasons)} seasons")
        else:
            print(f"    Not found or unavailable")

    # Output results
    output_data = {
        'discovered_at': datetime.now().isoformat(),
        'search_queries_used': SEARCH_QUERIES,
        'known_tv_series_checked': KNOWN_TV_SERIES,
        'known_radio_series_checked': KNOWN_RADIO_SERIES,
        'series': discovered_series,
        'programs': discovered_programs,
        'summary': {
            'total_series': len(discovered_series),
            'total_programs': len(discovered_programs),
            'tv_series': sum(1 for s in discovered_series.values() if s.get('source_medium') == 'tv'),
            'radio_series': sum(1 for s in discovered_series.values() if s.get('source_medium') == 'radio'),
        }
    }

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("DISCOVERY COMPLETE")
    print("=" * 60)
    print(f"Total series discovered: {len(discovered_series)}")
    print(f"Total standalone programs discovered: {len(discovered_programs)}")
    print(f"\nOutput written to: {OUTPUT_FILE}")

    # Print discovered series for review
    print("\n--- Discovered Series ---")
    for sid, sinfo in sorted(discovered_series.items(), key=lambda x: x[1].get('title', '')):
        seasons = sinfo.get('season_count', sinfo.get('seasons', []))
        if isinstance(seasons, list):
            seasons = len(seasons)
        medium = sinfo.get('source_medium', '?')
        print(f"  [{medium}] {sinfo.get('title', sid)} ({sid}) - {seasons} seasons")


if __name__ == "__main__":
    main()
