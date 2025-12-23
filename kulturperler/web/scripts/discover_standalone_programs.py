#!/usr/bin/env python3
"""
Discover standalone NRK programs (not part of series) that may be missing from Kulturperler.

This script searches the NRK API for:
- Opera performances
- Classical concerts
- Ballet performances
- Theatre/drama broadcasts

Programs are checked against existing episodes in data/episodes/ to find missing ones.

Output: output/standalone_programs_missing.json
"""

import requests
import json
import time
import re
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_FILE = OUTPUT_DIR / "standalone_programs_missing.json"

HEADERS = {'User-Agent': 'Kulturperler/1.0 (educational project)'}

# Search queries organized by category
SEARCH_QUERIES = {
    'opera': [
        # Opera titles
        'Rusalka', 'La Traviata', 'Tosca', 'Carmen', 'Rigoletto', 'Aida',
        'Madama Butterfly', 'La Bohème', 'Turandot', 'Norma', 'Fidelio',
        'Don Giovanni', 'Tryllefløyten', 'Così fan tutte', 'Figaros bryllup',
        'Der Rosenkavalier', 'Salome', 'Elektra', 'Tannhäuser', 'Lohengrin',
        'Tristan og Isolde', 'Parsifal', 'Valkyrien', 'Siegfried', 'Ragnarok',
        'Bajazzo', 'Cavalleria rusticana', 'Barberen i Sevilla', 'Askepott',
        'Eugen Onegin', 'Boris Godunov', 'Faust', 'Mefistofele', 'Otello',
        'Falstaff', 'Macbeth', 'Nabucco', 'Il trovatore', 'Don Carlos',
        'Lucia di Lammermoor', 'L\'elisir d\'amore', 'La fille du régiment',
        # Opera terms
        'operagalla', 'operahøydepunkter', 'direkte fra Operaen',
        'Den Norske Opera konsert', 'operakonsert',
    ],
    'classical': [
        # Classical terms
        'symfoni', 'symfonikonsert', 'filharmoni', 'orkesterkonsert',
        'kammermusikk', 'strykekvartett', 'klaverkonsert', 'fiolinkonsert',
        'cellokonsert', 'dirigent konsert', 'solistkonsert',
        'Kringkastingsorkestret', 'KORK konsert', 'Oslo Filharmonien',
        'Bergen Filharmoniske', 'Stavanger Symfoniorkester',
        'Trondheim Symfoniorkester', 'Kristiansand Symfoniorkester',
        # Festivals
        'Festspillene i Bergen', 'Ultima Oslo', 'Olavsfestdagene',
        'nyttårskonsert klassisk', 'Griegkonsert',
        # Composer names
        'Grieg konsert', 'Beethoven konsert', 'Mozart konsert',
        'Brahms konsert', 'Tsjajkovskij konsert', 'Sibelius konsert',
        'Dvořák konsert', 'Mahler konsert', 'Bruckner konsert',
    ],
    'ballet': [
        # Ballet titles
        'Svanesjøen', 'Nøtteknekkeren', 'Tornerose ballett', 'Giselle',
        'Romeo og Julie ballett', 'Don Quixote ballett', 'Coppélia',
        'La Sylphide', 'Peer Gynt ballett', 'Et folkesagn',
        # Ballet terms
        'ballettgalla', 'Nasjonalballetten', 'ballettkonsert',
        'Den Norske Opera ballett',
    ],
    'theatre': [
        # Theatre terms
        'Nationaltheatret', 'Det Norske Teatret', 'Rogaland Teater',
        'Den Nationale Scene', 'Trøndelag Teater', 'Hålogaland Teater',
        'teaterstykke', 'skuespill', 'drama teater',
        # Playwright names
        'Ibsen teater', 'Bjørnson teater', 'Holberg teater',
        'Strindberg teater', 'Fosse teater', 'Shakespeare teater',
        'Tsjekkov teater', 'Brecht teater',
        # Classic plays
        'Peer Gynt teater', 'Et dukkehjem', 'Hedda Gabler',
        'Vildanden', 'Gengangere', 'Brand', 'Rosmersholm',
        'Fruen fra havet', 'Byggmester Solness',
    ],
}

# Minimum duration in seconds for full performances (60 minutes)
MIN_DURATION_SECONDS = 3600


def load_existing_episodes():
    """Load all existing episode IDs and titles from data/episodes/"""
    existing_ids = set()
    existing_titles = {}  # title -> list of (id, year)
    episodes_dir = DATA_DIR / "episodes"

    for f in episodes_dir.glob("*.yaml"):
        existing_ids.add(f.stem)

        # Also parse title and year for duplicate detection
        with open(f) as fp:
            content = fp.read()
            title = None
            year = None
            for line in content.split('\n'):
                if line.startswith('title:'):
                    title = line.replace('title:', '').strip().strip('"').strip("'").lower()
                elif line.startswith('year:'):
                    try:
                        year = int(line.replace('year:', '').strip())
                    except:
                        pass
            if title:
                if title not in existing_titles:
                    existing_titles[title] = []
                existing_titles[title].append((f.stem, year))

    return existing_ids, existing_titles


def search_nrk(query, page_size=50):
    """Search NRK TV API for programs."""
    url = f"https://psapi.nrk.no/search"
    params = {'q': query, 'pageSize': page_size}
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if resp.ok:
            return resp.json()
    except Exception as e:
        print(f"  Error searching for '{query}': {e}")
    return None


def get_program_details(program_id):
    """Get full details for a program."""
    url = f"https://psapi.nrk.no/programs/{program_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.ok:
            return resp.json()
    except Exception as e:
        print(f"  Error fetching program '{program_id}': {e}")
    return None


def parse_duration(duration_str):
    """Parse ISO 8601 duration to seconds."""
    if not duration_str:
        return 0
    # Format: PT1H30M45S or PT30M or PT45S
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?', duration_str)
    if match:
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = float(match.group(3) or 0)
        return hours * 3600 + minutes * 60 + int(seconds)
    return 0


def parse_nrk_date(date_str):
    """Parse NRK date format /Date(timestamp+timezone)/ to year."""
    if not date_str:
        return None
    match = re.search(r'/Date\((\d+)', date_str)
    if match:
        ts = int(match.group(1)) / 1000
        return datetime.fromtimestamp(ts).year
    return None


def extract_program_info(hit, hit_data):
    """Extract relevant info from a search hit."""
    prog_id = hit_data.get('id', '')
    return {
        'id': prog_id,
        'title': hit_data.get('title', ''),
        'description': hit_data.get('description', ''),
        'duration': hit_data.get('duration', 0),
        'duration_seconds': parse_duration(hit_data.get('duration')) if isinstance(hit_data.get('duration'), str) else hit_data.get('duration', 0),
        'type': hit.get('type'),
        'available': hit_data.get('availability', {}).get('status') == 'available',
        'has_rights': hit_data.get('hasRights', False),
        'category': hit_data.get('category', {}).get('displayValue') if isinstance(hit_data.get('category'), dict) else None,
        'url': f"https://tv.nrk.no/program/{prog_id.lower()}" if prog_id else None,
    }


def discover_programs():
    """Search for standalone programs across all categories."""
    existing_ids, existing_titles = load_existing_episodes()
    print(f"Loaded {len(existing_ids)} existing episodes")

    all_programs = {}  # id -> program info

    for category, queries in SEARCH_QUERIES.items():
        print(f"\n=== Searching {category.upper()} ===")

        for query in queries:
            print(f"  Searching: {query}")
            result = search_nrk(query)

            if not result:
                continue

            hits = result.get('hits', [])
            for hit in hits:
                hit_type = hit.get('type')
                hit_data = hit.get('hit', {})

                # Only interested in standalone programs
                if hit_type != 'program':
                    continue

                prog_id = hit_data.get('id', '')
                if not prog_id:
                    continue

                # Skip if already in database by ID
                if prog_id in existing_ids:
                    continue

                # Skip if already found
                if prog_id in all_programs:
                    # Add category if not already there
                    if category not in all_programs[prog_id].get('categories', []):
                        all_programs[prog_id]['categories'].append(category)
                    continue

                # Check availability
                avail = hit_data.get('availability', {}).get('status')
                if avail != 'available':
                    continue

                info = extract_program_info(hit, hit_data)
                info['categories'] = [category]
                info['search_query'] = query
                all_programs[prog_id] = info

            time.sleep(0.2)  # Rate limiting

    return all_programs


def enrich_programs(programs):
    """Fetch additional details for discovered programs."""
    print(f"\n=== Enriching {len(programs)} programs ===")

    for i, (prog_id, info) in enumerate(programs.items()):
        if (i + 1) % 10 == 0:
            print(f"  Progress: {i + 1}/{len(programs)}")

        details = get_program_details(prog_id)
        if details:
            # Get transmission year
            first_tx = details.get('firstTimeTransmitted') or {}
            info['year'] = parse_nrk_date(first_tx.get('publicationDate')) if first_tx else None
            info['channel'] = first_tx.get('channelName')

            # Get duration
            duration = details.get('duration', '')
            info['duration'] = duration
            info['duration_seconds'] = parse_duration(duration)

            # Get image
            images = details.get('image', {}).get('webImages', [])
            if images:
                # Get largest image
                largest = max(images, key=lambda x: x.get('pixelWidth', 0))
                info['image_url'] = largest.get('imageUrl')

            # Get contributors
            contributors = details.get('programAndIndexPointsContributors', [])
            info['contributors'] = [
                {'name': c.get('name'), 'role': c.get('role')}
                for c in contributors[:20]  # Limit to first 20
            ]

            # Check if part of series
            links = details.get('_links', {})
            info['series'] = links.get('series', {}).get('name') if links.get('series') else None

            # Full description
            info['description'] = details.get('shortDescription', info.get('description', ''))

        time.sleep(0.1)

    return programs


def filter_and_classify(programs, existing_titles):
    """Filter programs and classify by likely type."""
    filtered = {}

    for prog_id, info in programs.items():
        # Check for potential title-based duplicates
        title_lower = info.get('title', '').lower()
        if title_lower in existing_titles:
            existing = existing_titles[title_lower]
            prog_year = info.get('year')
            # Mark as potential duplicate if same title and same year
            for ex_id, ex_year in existing:
                if ex_year == prog_year:
                    info['potential_duplicate'] = f"Same title/year as {ex_id}"
                    break
            else:
                info['similar_to'] = [ex_id for ex_id, _ in existing]
        # Skip very short programs (< 20 min)
        if info.get('duration_seconds', 0) < 1200:
            continue

        # Skip if part of a series (we should get those through series discovery)
        if info.get('series'):
            continue

        # Classify by duration and keywords
        duration = info.get('duration_seconds', 0)
        title = info.get('title', '').lower()
        desc = info.get('description', '').lower()
        combined = title + ' ' + desc

        # Determine likely type
        if duration >= 5400:  # > 90 min - likely full opera/theatre
            if any(kw in combined for kw in ['opera', 'operaen', 'akt']):
                info['likely_type'] = 'opera'
            elif any(kw in combined for kw in ['teater', 'teatret', 'skuespill']):
                info['likely_type'] = 'theatre'
            elif any(kw in combined for kw in ['ballett', 'dans']):
                info['likely_type'] = 'ballet'
            else:
                info['likely_type'] = 'long_performance'
        elif duration >= 3600:  # 60-90 min - likely concert or shorter production
            if any(kw in combined for kw in ['konsert', 'orkester', 'symfoni', 'filharmon']):
                info['likely_type'] = 'concert'
            elif any(kw in combined for kw in ['opera', 'akt']):
                info['likely_type'] = 'opera_excerpt'
            else:
                info['likely_type'] = 'medium_performance'
        else:  # 20-60 min
            info['likely_type'] = 'short_performance'

        filtered[prog_id] = info

    return filtered


def generate_report(programs):
    """Generate a human-readable report."""
    report_lines = [
        "# Standalone Programs Discovery Report",
        f"Generated: {datetime.now().isoformat()}",
        f"Total programs found: {len(programs)}",
        "",
    ]

    # Group by type
    by_type = {}
    for prog_id, info in programs.items():
        likely_type = info.get('likely_type', 'unknown')
        if likely_type not in by_type:
            by_type[likely_type] = []
        by_type[likely_type].append((prog_id, info))

    # Sort each group by duration (longest first)
    for likely_type, progs in sorted(by_type.items()):
        progs.sort(key=lambda x: x[1].get('duration_seconds', 0), reverse=True)

        report_lines.append(f"\n## {likely_type.upper()} ({len(progs)} programs)")
        report_lines.append("")

        for prog_id, info in progs:
            duration_min = info.get('duration_seconds', 0) // 60
            year = info.get('year', '?')
            title = info.get('title', 'Unknown')
            desc = info.get('description', '')[:100]
            url = info.get('url', '')

            report_lines.append(f"### {prog_id}: {title}")
            report_lines.append(f"- Duration: {duration_min} min")
            report_lines.append(f"- Year: {year}")
            report_lines.append(f"- Categories: {', '.join(info.get('categories', []))}")
            if info.get('potential_duplicate'):
                report_lines.append(f"- **POTENTIAL DUPLICATE**: {info['potential_duplicate']}")
            if info.get('similar_to'):
                report_lines.append(f"- Similar to existing: {', '.join(info['similar_to'])}")
            report_lines.append(f"- Description: {desc}...")
            report_lines.append(f"- URL: {url}")
            report_lines.append("")

    return "\n".join(report_lines)


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("=" * 60)
    print("Discovering standalone NRK programs")
    print("=" * 60)

    # Load existing for duplicate checking
    existing_ids, existing_titles = load_existing_episodes()

    # Discover programs
    programs = discover_programs()
    print(f"\nFound {len(programs)} unique standalone programs")

    # Enrich with details
    programs = enrich_programs(programs)

    # Filter and classify
    programs = filter_and_classify(programs, existing_titles)
    print(f"\nAfter filtering: {len(programs)} programs")

    # Save JSON
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(programs, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {OUTPUT_FILE}")

    # Generate report
    report = generate_report(programs)
    report_file = OUTPUT_DIR / "standalone_programs_report.md"
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"Report saved to {report_file}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    by_type = {}
    for prog_id, info in programs.items():
        likely_type = info.get('likely_type', 'unknown')
        by_type[likely_type] = by_type.get(likely_type, 0) + 1

    for likely_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {likely_type}: {count}")


if __name__ == "__main__":
    main()
