#!/usr/bin/env python3
"""
Extract conductor names from YouTube concert titles and add them to performance credits.

YouTube titles typically follow pattern: "Work / Composer / Conductor / Orchestra"
e.g., "Symphony No. 5 / Ralph Vaughan Williams / Vasily Petrenko / Oslo Philharmonic"
"""

import sqlite3
import yaml
import re
import os
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dotenv import load_dotenv
import requests
import time

load_dotenv()

DATA_DIR = Path('data')
DB_PATH = Path('static/kulturperler.db')
GEMINI_KEY = os.getenv('GEMINI_KEY')

def load_yaml(path: Path):
    with open(path) as f:
        return yaml.safe_load(f)

def save_yaml(path: Path, data):
    with open(path, 'w') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

def get_youtube_performances_without_conductor() -> List[Tuple[int, str]]:
    """Get YouTube performances without conductor credits."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.id, p.title
        FROM performances p
        WHERE p.source='youtube'
        AND NOT EXISTS (
            SELECT 1 FROM performance_persons pp
            WHERE pp.performance_id = p.id AND pp.role='conductor'
        )
        ORDER BY p.id
    """)

    results = cursor.fetchall()
    conn.close()
    return results

def extract_conductor_from_title(title: str) -> Optional[str]:
    """
    Extract conductor name from YouTube concert title.
    Pattern: Usually "Work / Composer / Conductor / Orchestra"
    """
    # Split by slash
    parts = [p.strip() for p in title.split('/')]

    if len(parts) < 3:
        return None

    # Orchestra keywords to identify orchestra position
    orchestra_keywords = ['Orchestra', 'Philharmonic', 'Symphony', 'Ensemble', 'Choir', 'Phil.', 'Phil']

    # Find the orchestra position (usually last part)
    orchestra_idx = None
    for i in range(len(parts) - 1, 0, -1):
        if any(kw in parts[i] for kw in orchestra_keywords):
            orchestra_idx = i
            break

    if orchestra_idx is None:
        # No orchestra found, conductor might be last part if there are 3+ parts
        if len(parts) >= 3:
            return parts[-1]
        return None

    # Conductor is likely the part before orchestra
    if orchestra_idx > 1:
        conductor_candidate = parts[orchestra_idx - 1]

        # Filter out common composer last names that might be confused
        common_composers = [
            'Mozart', 'Beethoven', 'Bach', 'Brahms', 'Wagner', 'Verdi',
            'Tchaikovsky', 'Mahler', 'Strauss', 'Debussy', 'Ravel',
            'Sibelius', 'Dvořák', 'Dvorak', 'Rachmaninoff',
            'Shostakovich', 'Stravinsky', 'Prokofiev', 'Bartók', 'Bartok',
            'Mendelssohn', 'Schumann', 'Chopin', 'Liszt', 'Vivaldi',
            'Handel', 'Haydn', 'Schubert', 'Berlioz', 'Saint-Saëns',
            'Britten', 'Copland',
            'Svendsen', 'Halvorsen', 'Valen', 'Nordheim', 'Sinding',
            'Lully', 'Berio', 'Glass', 'Mussorgsky',
            'Korngold', 'Purcell', 'Orff', 'Dessner', 'Chin', 'Zinovjev',
            'Henriette'  # Mette Henriette is a composer
        ]

        # Check if this looks like a person name (has space or hyphen)
        # This will match most conductor names like "Klaus Mäkelä", "Herbert Blomstedt", etc.
        if len(conductor_candidate) < 50:
            # Check if it contains a composer last name (exact match)
            is_composer = any(comp in conductor_candidate.split() for comp in common_composers)

            if not is_composer:
                # Additional check: if it has 2-3 parts and looks like a name, accept it
                name_parts = conductor_candidate.split()
                if 1 <= len(name_parts) <= 3:
                    return conductor_candidate

    return None

def find_person_by_name(name: str) -> Optional[int]:
    """Search for person by name in database (case-insensitive)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    normalized_search = name.lower().strip()

    # Try exact match first
    cursor.execute(
        "SELECT id, name FROM persons WHERE LOWER(name) = ? OR LOWER(normalized_name) = ?",
        (normalized_search, normalized_search)
    )
    row = cursor.fetchone()
    if row:
        conn.close()
        return row[0]

    # Try partial match (last name)
    last_name_search = normalized_search.split()[-1] if ' ' in normalized_search else normalized_search

    cursor.execute(
        "SELECT id, name FROM persons WHERE LOWER(name) LIKE ? OR LOWER(normalized_name) LIKE ?",
        (f'%{last_name_search}%', f'%{last_name_search}%')
    )
    rows = cursor.fetchall()
    conn.close()

    # If single match, return it
    if len(rows) == 1:
        return rows[0][0]

    # If multiple matches, print them for manual review
    if len(rows) > 1:
        print(f"    Multiple matches for '{name}':")
        for row in rows[:5]:
            print(f"      - {row[1]} (ID: {row[0]})")

    return None

def get_next_person_id() -> int:
    """Get next available person ID from filesystem (not database)."""
    person_files = list((DATA_DIR / 'persons').glob('*.yaml'))
    if not person_files:
        return 1
    max_id = max([int(f.stem) for f in person_files])
    return max_id + 1

def verify_conductor_with_gemini(name: str, title: str, skip_gemini: bool = False) -> Tuple[bool, Optional[Dict]]:
    """
    Use Gemini with Google Search to verify conductor and get basic info.
    Returns (is_conductor, info_dict)
    """
    if not GEMINI_KEY or skip_gemini:
        return True, None  # Skip verification if no key or skip flag

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={GEMINI_KEY}"

    prompt = f"""Search for "{name}" and determine if they are a conductor.
Context: This name was extracted from a concert video title: "{title}"

Reply with EXACTLY this format:
CONDUCTOR: yes/no
NAME: [full proper name if yes]
BIRTH_YEAR: [year or unknown]
DEATH_YEAR: [year or unknown]
NATIONALITY: [nationality or unknown]

If not a conductor, just reply "CONDUCTOR: no"."""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.1}
    }

    try:
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()

        response_text = r.json()['candidates'][0]['content']['parts'][0]['text']

        if 'CONDUCTOR: no' in response_text:
            return False, None

        # Parse response
        info = {}
        for line in response_text.split('\n'):
            line = line.strip()
            if line.startswith('NAME:'):
                info['name'] = line.split(':', 1)[1].strip()
            elif line.startswith('BIRTH_YEAR:'):
                year_str = line.split(':', 1)[1].strip()
                if year_str.isdigit():
                    info['birth_year'] = int(year_str)
            elif line.startswith('DEATH_YEAR:'):
                year_str = line.split(':', 1)[1].strip()
                if year_str.isdigit():
                    info['death_year'] = int(year_str)
            elif line.startswith('NATIONALITY:'):
                nat = line.split(':', 1)[1].strip()
                if nat.lower() != 'unknown':
                    info['nationality'] = nat

        return True, info if info else None

    except Exception as e:
        print(f"  Error verifying with Gemini: {e}")
        # If rate limited, skip verification and accept conductor
        if '429' in str(e) or 'Too Many Requests' in str(e):
            return True, None
        return False, None

def create_person(name: str, info: Optional[Dict] = None, dry_run: bool = True) -> int:
    """Create new person file."""
    person_id = get_next_person_id()

    person_data = {
        'id': person_id,
        'name': info.get('name', name) if info else name,
        'normalized_name': (info.get('name', name) if info else name).lower()
    }

    if info:
        if 'birth_year' in info:
            person_data['birth_year'] = info['birth_year']
        if 'death_year' in info:
            person_data['death_year'] = info['death_year']
        if 'nationality' in info:
            person_data['nationality'] = info['nationality']

    if dry_run:
        print(f"  [DRY RUN] Would create person {person_id}: {person_data['name']}")
    else:
        person_file = DATA_DIR / 'persons' / f'{person_id}.yaml'
        save_yaml(person_file, person_data)
        print(f"  Created person {person_id}: {person_data['name']}")

    return person_id

def add_conductor_credit(performance_id: int, person_id: int, dry_run: bool = True):
    """Add conductor credit to performance YAML file."""
    perf_file = DATA_DIR / 'performances' / f'{performance_id}.yaml'

    if not perf_file.exists():
        print(f"  Warning: Performance file {perf_file} not found")
        return

    perf = load_yaml(perf_file)

    # Initialize credits if not present
    if 'credits' not in perf or perf['credits'] is None:
        perf['credits'] = []

    # Check if conductor already exists
    for credit in perf['credits']:
        if credit.get('person_id') == person_id and credit.get('role') == 'conductor':
            print(f"  Conductor already exists in performance {performance_id}")
            return

    # Add conductor credit
    perf['credits'].append({
        'person_id': person_id,
        'role': 'conductor'
    })

    if dry_run:
        print(f"  [DRY RUN] Would add conductor credit to performance {performance_id}")
    else:
        save_yaml(perf_file, perf)
        print(f"  Added conductor credit to performance {performance_id}")

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Enrich YouTube concerts with conductor data')
    parser.add_argument('--live', action='store_true', help='Actually modify files (default is dry run)')
    parser.add_argument('--limit', type=int, default=50, help='Process only first N performances (default: 50)')
    parser.add_argument('--skip-gemini', action='store_true', help='Skip Gemini verification (faster but less accurate)')

    args = parser.parse_args()

    print("Enriching YouTube concerts with conductor data...")
    print(f"Mode: {'LIVE' if args.live else 'DRY RUN'}")
    print(f"Gemini verification: {'DISABLED' if args.skip_gemini else 'ENABLED'}")
    print()

    performances = get_youtube_performances_without_conductor()
    print(f"Found {len(performances)} YouTube performances without conductor credits")
    print(f"Processing first {args.limit} performances...")
    print()

    # Process in batches
    processed = 0
    added = 0
    skipped = 0

    for perf_id, title in performances[:args.limit]:
        processed += 1
        print(f"[{processed}/{min(args.limit, len(performances))}] {title[:80]}...")

        # Extract conductor name
        conductor_name = extract_conductor_from_title(title)

        if not conductor_name:
            print(f"  Could not extract conductor from title")
            skipped += 1
            continue

        print(f"  Extracted conductor: {conductor_name}")

        # Check if person already exists
        person_id = find_person_by_name(conductor_name)

        if person_id:
            print(f"  Found existing person: {person_id}")
        else:
            # Verify with Gemini if enabled
            if not args.skip_gemini:
                print(f"  Verifying with Gemini...")
                is_conductor, info = verify_conductor_with_gemini(conductor_name, title, skip_gemini=False)

                if not is_conductor:
                    print(f"  Not confirmed as conductor, skipping")
                    skipped += 1
                    time.sleep(2)  # Rate limiting
                    continue

                person_id = create_person(conductor_name, info, dry_run=not args.live)
                time.sleep(2)  # Rate limiting
            else:
                # Create without verification
                person_id = create_person(conductor_name, dry_run=not args.live)

        # Add conductor credit
        add_conductor_credit(perf_id, person_id, dry_run=not args.live)
        added += 1
        print()

    print()
    print("=" * 80)
    print(f"Summary:")
    print(f"  Processed: {processed}")
    print(f"  Added conductor credits: {added}")
    print(f"  Skipped: {skipped}")
    print()
    if not args.live:
        print("This was a DRY RUN. Use --live to actually modify files.")
        print()
    print("After running with --live:")
    print("  1. Run 'python3 scripts/validate_data.py' to validate changes")
    print("  2. Run 'python3 scripts/build_database.py' to rebuild database")

if __name__ == '__main__':
    main()
