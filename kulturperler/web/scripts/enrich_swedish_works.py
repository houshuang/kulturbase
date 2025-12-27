#!/usr/bin/env python3
"""
Enrich Swedish works with playwright information from Swedish Wikipedia.

For works imported from Sveriges Radio that don't have playwright_id,
search Swedish Wikipedia to find the author and link them.
"""

import yaml
import requests
import time
import re
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / 'data'
WORKS_DIR = DATA_DIR / 'plays'
PERSONS_DIR = DATA_DIR / 'persons'

# User agent for Wikipedia API
HEADERS = {'User-Agent': 'Kulturperler/1.0 (https://kulturbase.no)'}

# Known work -> author mappings for Swedish plays
# These are well-known works that we can directly map
KNOWN_WORKS = {
    # Astrid Lindgren
    'bröderna lejonhjärta': 'Astrid Lindgren',
    'ronja rövardotter': 'Astrid Lindgren',
    'mio min mio': 'Astrid Lindgren',
    'pippi långstrump': 'Astrid Lindgren',
    'emil i lönneberga': 'Astrid Lindgren',
    'karlsson på taket': 'Astrid Lindgren',
    'brorsan är kung': 'Astrid Lindgren',

    # Carl Jonas Love Almqvist
    'amorina': 'Carl Jonas Love Almqvist',
    'drottningens juvelsmycke': 'Carl Jonas Love Almqvist',

    # Selma Lagerlöf
    'herr arnes pengar': 'Selma Lagerlöf',
    'gösta berlings saga': 'Selma Lagerlöf',
    'nils holgerssons underbara resa': 'Selma Lagerlöf',
    'kejsarn av portugallien': 'Selma Lagerlöf',
    "kejsar'n": 'Selma Lagerlöf',

    # Hjalmar Söderberg
    'gertrud': 'Hjalmar Söderberg',
    'doktor glas': 'Hjalmar Söderberg',
    'den allvarsamma leken': 'Hjalmar Söderberg',

    # French classics
    'kameliadamen': 'Alexandre Dumas den yngre',
    'en dörr skall vara öppen eller stängd': 'Alfred de Musset',
    'il ne faut jurer de rien': 'Alfred de Musset',
    'den avundsjuke': 'Molière',
    'frieriet': 'Anton Tjechov',
    'postkontoret': 'Rabindranath Tagore',

    # Swedish classics
    'bröllopet på ulfåsa': 'Frans Hedberg',
    'colombine': 'Victoria Benedictsson',
    'pengar': 'Victoria Benedictsson',
    'ferrando bruno': 'Oscar Levertin',

    # Strindberg
    'hemsöborna': 'August Strindberg',
    'inferno': 'August Strindberg',
    'röda rummet': 'August Strindberg',

    # Danish
    'hyrkuskens berättelser': 'Karen Blixen',
    'babettes gästabud': 'Karen Blixen',

    # International
    'häxorna': 'Roald Dahl',
    'matilda': 'Roald Dahl',
    'den besynnerliga händelsen med hunden om natten': 'Mark Haddon',

    # Per Olov Enquist
    'svenne': 'Per Olov Enquist',
    'tribadernas natt': 'Per Olov Enquist',
    'magnetisörens femte vinter': 'Per Olov Enquist',
    'livläkarens besök': 'Per Olov Enquist',
    'hamsun': 'Per Olov Enquist',
    'kapten nemos bibliotek': 'Per Olov Enquist',
    'nedstörtad ängel': 'Per Olov Enquist',

    # Ingmar Bergman
    'ett resande teatersällskap': 'Ingmar Bergman',

    # More Swedish children's literature
    'djupgraven': 'Katarina Mazetti',
    'ily': 'Moni Nilsson',
    'gräsmattan får ej beträdas': 'Stig Dagerman',
    'chans': 'Inger Edelfeldt',

    # More classics
    'konsert i ett hus': 'Hjalmar Bergman',
    'den ena för den andra – en komedi': 'Ludvig Holberg',

    # Chekhov
    'tre systrar': 'Anton Tjechov',
    'måsen': 'Anton Tjechov',
    'svanesång': 'Anton Tjechov',
    'onkel vanja': 'Anton Tjechov',
    'körsbärsträdgården': 'Anton Tjechov',

    # Shakespeare
    'romeo och julia': 'William Shakespeare',
    'macbeth': 'William Shakespeare',
    'hamlet': 'William Shakespeare',
    'en midsommarnattsdröm': 'William Shakespeare',
    'othello': 'William Shakespeare',
    'kung lear': 'William Shakespeare',

    # More Swedish classics
    'körkarlen': 'Selma Lagerlöf',
    'ullabella': 'Hjalmar Bergman',
    'svanevit': 'August Strindberg',
    'pojkar': 'Stig Dagerman',

    # More Astrid Lindgren
    'mio, min mio': 'Astrid Lindgren',

    # More French
    'lek ej med kärleken': 'Alfred de Musset',

    # Robert Louis Stevenson
    'skattkammarön': 'Robert Louis Stevenson',
    'dr jekyll och mr hyde': 'Robert Louis Stevenson',

    # Maria Gripe
    'tordyveln flyger i skymningen': 'Maria Gripe',
}

# Modern drama series - these don't have single authors, skip them
SKIP_WORK_TYPES = ['dramaserie']


def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_yaml(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def load_persons():
    """Load all persons and create name -> id mapping."""
    persons = {}
    for f in PERSONS_DIR.glob('*.yaml'):
        p = load_yaml(f)
        name_lower = p['name'].lower()
        persons[name_lower] = p
        if p.get('normalized_name'):
            persons[p['normalized_name']] = p
    return persons


def get_next_person_id():
    """Get next available person ID."""
    max_id = 0
    for f in PERSONS_DIR.glob('*.yaml'):
        try:
            id_val = int(f.stem)
            max_id = max(max_id, id_val)
        except ValueError:
            continue
    return max_id + 1


def search_wikipedia_sv(title):
    """Search Swedish Wikipedia for a work."""
    url = 'https://sv.wikipedia.org/w/api.php'
    params = {
        'action': 'query',
        'list': 'search',
        'srsearch': title,
        'format': 'json',
        'srlimit': 5
    }

    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        results = data.get('query', {}).get('search', [])
        return results
    except Exception as e:
        print(f"  Error searching Wikipedia: {e}")
        return []


def get_wikipedia_page(title):
    """Get Wikipedia page content."""
    url = f'https://sv.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(title)}'

    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  Error fetching page: {e}")
        return None


def extract_author_from_wikipedia(page_data):
    """Try to extract author from Wikipedia page extract."""
    if not page_data:
        return None

    extract = page_data.get('extract', '')

    # Common patterns in Swedish Wikipedia
    patterns = [
        r'är en (?:roman|pjäs|bok|novell|berättelse|teaterpjäs|drama|musikal) av (.+?)(?:\.|,| från)',
        r'skriven av (.+?)(?:\.|,| \d)',
        r'av författaren (.+?)(?:\.|,)',
        r'av den (?:svenske|svenska|norske|norska|danske|danska|engelske|engelska|franske|franska|tyske|tyska) (?:författaren|författarinnan|dramatikern) (.+?)(?:\.|,)',
        r'av (.+?) från (\d{4})',
    ]

    for pattern in patterns:
        match = re.search(pattern, extract, re.IGNORECASE)
        if match:
            author = match.group(1).strip()
            # Clean up common suffixes
            author = re.sub(r'\s*\(.*\)$', '', author)
            author = re.sub(r'\s*och\s+.*$', '', author)
            return author

    return None


def find_or_create_person(name, persons, next_id):
    """Find existing person or create new one."""
    name_lower = name.lower()

    # Check for existing person
    if name_lower in persons:
        return persons[name_lower]['id'], False

    # Check partial matches (last name)
    name_parts = name.split()
    if len(name_parts) > 1:
        last_name = name_parts[-1].lower()
        for pname, pdata in persons.items():
            if last_name in pname and len(pname.split()) > 1:
                # Verify it's likely the same person
                if name_parts[0][0].lower() == pname.split()[0][0]:
                    return pdata['id'], False

    # Create new person
    person_data = {
        'id': next_id,
        'name': name,
        'normalized_name': name.lower(),
    }

    # Try to get Wikipedia info
    wiki_page = get_wikipedia_page(name)
    if wiki_page:
        person_data['wikipedia_url'] = f"https://sv.wikipedia.org/wiki/{requests.utils.quote(name.replace(' ', '_'))}"

        # Try to extract birth/death years from extract
        extract = wiki_page.get('extract', '')
        year_match = re.search(r'född (?:den )?\d+ \w+ (\d{4})', extract)
        if year_match:
            person_data['birth_year'] = int(year_match.group(1))

        death_match = re.search(r'död (?:den )?\d+ \w+ (\d{4})', extract)
        if death_match:
            person_data['death_year'] = int(death_match.group(1))

        # Shorter pattern for just years
        if 'birth_year' not in person_data:
            year_match = re.search(r'\((\d{4})[-–](\d{4})\)', extract)
            if year_match:
                person_data['birth_year'] = int(year_match.group(1))
                person_data['death_year'] = int(year_match.group(2))

        # Get wikidata ID
        wikidata_url = wiki_page.get('content_urls', {}).get('desktop', {}).get('page', '')
        if wikidata_url:
            # Could fetch Wikidata ID here
            pass

    # Save person
    save_yaml(PERSONS_DIR / f'{next_id}.yaml', person_data)
    persons[name_lower] = person_data

    return next_id, True


def enrich_work(work_path, persons, next_person_id, skip_wikipedia=False):
    """Enrich a single work with playwright info."""
    work = load_yaml(work_path)

    # Skip if already has playwright
    if work.get('playwright_id'):
        return None, next_person_id

    # Skip drama series - these are modern productions without single authors
    if work.get('work_type') in SKIP_WORK_TYPES:
        print(f"  Skipping (drama series)")
        return None, next_person_id

    title = work['title']
    title_lower = title.lower()

    author_name = None

    # First check known works
    if title_lower in KNOWN_WORKS:
        author_name = KNOWN_WORKS[title_lower]
        print(f"  Found in known works: {author_name}")
    elif not skip_wikipedia:
        # Search Swedish Wikipedia - but be more careful
        print(f"  Searching Swedish Wikipedia for: {title}")
        results = search_wikipedia_sv(f'"{title}" pjäs OR roman OR bok')

        if results:
            # Try to find a matching page
            for result in results:
                page_title = result['title']
                # Must be a close match to the title
                if title_lower == page_title.lower() or f"({title_lower})" in page_title.lower():
                    page = get_wikipedia_page(page_title)
                    if page:
                        # Check that this is actually about a literary work
                        extract = page.get('extract', '').lower()
                        if any(word in extract for word in ['roman', 'pjäs', 'bok', 'novell', 'teaterpjäs', 'drama', 'skriven', 'författare']):
                            author_name = extract_author_from_wikipedia(page)
                            if author_name and len(author_name) < 50:  # Sanity check
                                print(f"  Found author from Wikipedia: {author_name}")

                                # Also update synopsis if we have it
                                if not work.get('synopsis') and page.get('extract'):
                                    work['synopsis'] = page['extract']

                                # Add Wikipedia URL
                                if not work.get('wikipedia_url'):
                                    work['wikipedia_url'] = page.get('content_urls', {}).get('desktop', {}).get('page')

                                break
                            else:
                                author_name = None  # Reset if extraction failed

        time.sleep(0.5)  # Be nice to Wikipedia

    if author_name:
        # Find or create person
        person_id, created = find_or_create_person(author_name, persons, next_person_id)
        if created:
            print(f"  Created new person: {author_name} (ID: {person_id})")
            next_person_id += 1
        else:
            print(f"  Linked to existing person ID: {person_id}")

        work['playwright_id'] = person_id
        save_yaml(work_path, work)
        return author_name, next_person_id
    else:
        print(f"  Could not find author for: {title}")
        return None, next_person_id


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Enrich Swedish works with playwright info')
    parser.add_argument('--limit', type=int, default=0, help='Limit number of works to process')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    parser.add_argument('--known-only', action='store_true', help='Only use known works mapping, skip Wikipedia')
    args = parser.parse_args()

    print("Loading persons...")
    persons = load_persons()
    print(f"  Loaded {len(persons)} person name mappings")

    next_person_id = get_next_person_id()
    print(f"  Next person ID: {next_person_id}")

    # Find Swedish works without playwright
    works_to_enrich = []
    for f in WORKS_DIR.glob('*.yaml'):
        work = load_yaml(f)
        if work.get('language') == 'sv' and not work.get('playwright_id'):
            # Skip drama series
            if work.get('work_type') not in SKIP_WORK_TYPES:
                works_to_enrich.append(f)

    print(f"\nFound {len(works_to_enrich)} Swedish works without playwright (excluding drama series)")

    if args.limit > 0:
        works_to_enrich = works_to_enrich[:args.limit]
        print(f"Processing first {args.limit} works")

    enriched = 0
    created_persons = 0

    for work_path in works_to_enrich:
        work = load_yaml(work_path)
        print(f"\n[{work['id']}] {work['title']} ({work.get('work_type', 'unknown')})")

        if args.dry_run:
            title_lower = work['title'].lower()
            if title_lower in KNOWN_WORKS:
                print(f"  Would link to: {KNOWN_WORKS[title_lower]}")
            continue

        author, next_person_id_new = enrich_work(work_path, persons, next_person_id, skip_wikipedia=args.known_only)
        if author:
            enriched += 1
            if next_person_id_new > next_person_id:
                created_persons += 1
                next_person_id = next_person_id_new

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"  Works enriched: {enriched}")
    print(f"  New persons created: {created_persons}")

    if not args.dry_run:
        print("\nDone! Remember to run: python3 scripts/build_database.py")


if __name__ == '__main__':
    main()
