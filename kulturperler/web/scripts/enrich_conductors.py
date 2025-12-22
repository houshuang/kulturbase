#!/usr/bin/env python3
"""
Enrich NRK concert performances with conductor data.

Strategy:
1. Check NRK API contributors for role='Dirigent'
2. Check NRK API longDescription for "Dirigent: Name"
3. Check performance description for "dirigent" or "dirigeres av"
4. Use Gemini with web search as fallback for title/series

For found conductors:
- Look up existing person by name
- Create new person if not found
- Update performance YAML with conductor credit
"""

import sqlite3
import yaml
import re
import os
import requests
import time
from pathlib import Path
from typing import Optional, Dict, List
from dotenv import load_dotenv

load_dotenv()

DB_PATH = Path('static/kulturperler.db')
DATA_DIR = Path('data')
PERSONS_DIR = DATA_DIR / 'persons'
PERFORMANCES_DIR = DATA_DIR / 'performances'

GEMINI_KEY = os.getenv('GEMINI_KEY')
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={GEMINI_KEY}"

class ConductorEnricher:
    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.created_persons = {}  # Cache: normalized_name -> person_id
        self.next_person_id = self.get_next_person_id()
        self.stats = {
            'total': 0,
            'already_have_conductor': 0,
            'found_in_nrk_api': 0,
            'found_in_description': 0,
            'found_via_gemini': 0,
            'not_found': 0,
            'updated': 0,
            'errors': 0
        }

    def get_concert_performances(self) -> List[Dict]:
        """Get all NRK concert performances."""
        query = """
            SELECT p.id, p.title, p.description, p.series_id, p.year, e.prf_id,
                   COUNT(pp.person_id) as conductor_count
            FROM performances p
            JOIN works w ON p.work_id = w.id
            LEFT JOIN episodes e ON p.id = e.performance_id
            LEFT JOIN performance_persons pp ON p.id = pp.performance_id AND pp.role = 'conductor'
            WHERE w.category = 'konsert' AND p.source = 'nrk'
            GROUP BY p.id
            ORDER BY p.id
        """
        cursor = self.conn.execute(query)
        return [dict(row) for row in cursor.fetchall()]

    def names_similar(self, name1: str, name2: str) -> bool:
        """Check if two names are similar (handle spelling variations)."""
        parts1 = name1.lower().split()
        parts2 = name2.lower().split()

        if len(parts1) != len(parts2) or len(parts1) < 2:
            return False

        # First names must match exactly
        if parts1[0] != parts2[0]:
            return False

        # Last names can differ slightly
        last1 = parts1[-1]
        last2 = parts2[-1]

        if last1 == last2:
            return True

        # Allow 1-2 character differences for last name
        if len(last1) > 5 and len(last2) > 5 and abs(len(last1) - len(last2)) <= 1:
            diff_count = sum(1 for i in range(min(len(last1), len(last2)))
                           if last1[i] != last2[i])
            return diff_count <= 2

        return False

    def get_person_by_name(self, name: str) -> Optional[int]:
        """Find person ID by name (case-insensitive, handles variations)."""
        normalized = name.lower().strip()

        # Check if we created this person in current run (exact match)
        if normalized in self.created_persons:
            return self.created_persons[normalized]

        # Check created persons for fuzzy match
        for created_name, person_id in self.created_persons.items():
            if self.names_similar(normalized, created_name):
                print(f"    Matched '{name}' to previously created person (ID: {person_id})")
                # Cache this variation too
                self.created_persons[normalized] = person_id
                return person_id

        # Try exact match in database
        cursor = self.conn.execute(
            "SELECT id, name FROM persons WHERE LOWER(name) = ? OR LOWER(normalized_name) = ?",
            (normalized, normalized)
        )
        row = cursor.fetchone()
        if row:
            return row['id']

        # Try fuzzy match in database
        parts = normalized.split()
        if len(parts) >= 2:
            # Try "Lastname Firstname" if we have "Firstname Lastname"
            reversed_name = ' '.join(parts[::-1])
            cursor = self.conn.execute(
                "SELECT id, name FROM persons WHERE LOWER(name) = ? OR LOWER(normalized_name) = ?",
                (reversed_name, reversed_name)
            )
            row = cursor.fetchone()
            if row:
                print(f"    Matched '{name}' to existing person '{row['name']}' (ID: {row['id']})")
                return row['id']

            # Try fuzzy match for spelling variations
            first_name = parts[0]
            cursor = self.conn.execute(
                "SELECT id, name, normalized_name FROM persons WHERE LOWER(normalized_name) LIKE ?",
                (f"{first_name}%",)
            )
            for row in cursor.fetchall():
                if self.names_similar(normalized, row['normalized_name']):
                    print(f"    Fuzzy matched '{name}' to existing person '{row['name']}' (ID: {row['id']})")
                    return row['id']

        return None

    def get_next_person_id(self) -> int:
        """Get next available person ID."""
        cursor = self.conn.execute("SELECT MAX(id) as max_id FROM persons")
        return cursor.fetchone()['max_id'] + 1

    def normalize_conductor_name(self, name: str) -> str:
        """Normalize conductor name (title case, handle spacing issues)."""
        # Remove extra spaces
        name = ' '.join(name.split())
        # Fix spacing around hyphens
        name = re.sub(r'\s*-\s*', '-', name)
        # Title case each part
        parts = name.split()
        normalized_parts = []
        for part in parts:
            # Handle hyphenated names
            if '-' in part:
                sub_parts = part.split('-')
                part = '-'.join([sp.capitalize() for sp in sub_parts])
            else:
                part = part.capitalize()
            normalized_parts.append(part)

        return ' '.join(normalized_parts)

    def create_person(self, name: str) -> int:
        """Create new person YAML file."""
        # Normalize name first
        name = self.normalize_conductor_name(name)
        normalized = name.lower()

        # Check if we already created this person in this run
        if normalized in self.created_persons:
            person_id = self.created_persons[normalized]
            print(f"  Using previously created person: {name} (ID: {person_id})")
            return person_id

        person_id = self.next_person_id
        self.next_person_id += 1  # Increment for next person

        person_data = {
            'id': person_id,
            'name': name,
            'normalized_name': normalized
        }

        if not self.dry_run:
            person_file = PERSONS_DIR / f"{person_id}.yaml"
            with open(person_file, 'w') as f:
                yaml.dump(person_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            print(f"  Created new person: {name} (ID: {person_id})")
        else:
            print(f"  [DRY RUN] Would create person: {name} (ID: {person_id})")

        # Cache the created person
        self.created_persons[normalized] = person_id

        return person_id

    def fetch_nrk_program(self, prf_id: str) -> Optional[Dict]:
        """Fetch program data from NRK API."""
        if not prf_id:
            return None

        try:
            url = f"https://psapi.nrk.no/programs/{prf_id}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"  Error fetching NRK API for {prf_id}: {e}")
            return None

    def extract_conductor_from_nrk_api(self, nrk_data: Dict) -> Optional[str]:
        """Extract conductor name from NRK API data."""
        if not nrk_data:
            return None

        # Check contributors for role='Dirigent'
        contributors = nrk_data.get('contributors', [])
        for contrib in contributors:
            role = contrib.get('role', '').lower()
            if 'dirigent' in role:
                name = contrib.get('name', '').strip()
                if name and name != 'Arkivpublisering':
                    return name

        # Check longDescription for "Dirigent: Name"
        long_desc = nrk_data.get('longDescription', '')
        match = re.search(r'Dirigent:\s*([^.\n]+)', long_desc, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            # Clean up common suffixes
            name = re.sub(r'\s*\(.*?\)\s*$', '', name)  # Remove parentheses
            name = re.sub(r'\.$', '', name)  # Remove trailing period
            return name

        return None

    def extract_conductor_from_description(self, description: str) -> Optional[str]:
        """Extract conductor name from performance description."""
        if not description:
            return None

        patterns = [
            r'Dirigent:\s*([^.\n]+)',
            r'dirigeres av\s+([^.\n]+)',
            r'med dirigent\s+([^.\n]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Clean up
                name = re.sub(r'\s*\(.*?\)\s*$', '', name)  # Remove parentheses
                name = re.sub(r'\.$', '', name)  # Remove trailing period
                # Remove common noise words/phrases
                name = re.sub(r'\s+(og|med|i|fra|er|spiller|fremfører|tolker|på).*$', '', name, flags=re.IGNORECASE)
                name = re.sub(r'\s*[,;].*$', '', name)  # Remove comma/semicolon and rest

                # Validate: should have at least 2 parts (firstname lastname) and reasonable length
                parts = name.split()
                if len(parts) >= 2 and len(name) > 5 and len(name) < 50:
                    # Check if starts with capital letter
                    if name[0].isupper() or name[0] in 'ÆØÅÄÖ':
                        return name

        return None

    def search_conductor_with_gemini(self, title: str, series_id: str, year: int) -> Optional[str]:
        """Use Gemini with web search to find conductor."""
        if not GEMINI_KEY:
            return None

        try:
            prompt = f"""Find the conductor (dirigent) for this concert performance from NRK:
Title: {title}
Series: {series_id}
Year: {year}

Search for information about this performance and return ONLY the conductor's full name, or "UNKNOWN" if you cannot find it.
Reply with just the name, nothing else."""

            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "tools": [{"google_search": {}}],
                "generationConfig": {"temperature": 0.1}
            }

            response = requests.post(GEMINI_URL, json=payload, timeout=30)
            response.raise_for_status()

            result = response.json()
            text = result['candidates'][0]['content']['parts'][0]['text'].strip()

            if text and text.upper() != 'UNKNOWN' and len(text) < 100:
                return text

        except Exception as e:
            print(f"  Error using Gemini: {e}")

        return None

    def update_performance_yaml(self, performance_id: int, conductor_id: int):
        """Add conductor credit to performance YAML file."""
        perf_file = PERFORMANCES_DIR / f"{performance_id}.yaml"

        if not perf_file.exists():
            print(f"  ERROR: Performance file not found: {perf_file}")
            return

        with open(perf_file) as f:
            perf_data = yaml.safe_load(f)

        # Add conductor to credits
        if 'credits' not in perf_data:
            perf_data['credits'] = []

        # Check if conductor already exists
        for credit in perf_data['credits']:
            if credit.get('role') == 'conductor':
                print(f"  WARNING: Conductor credit already exists in YAML")
                return

        perf_data['credits'].append({
            'person_id': conductor_id,
            'role': 'conductor'
        })

        if not self.dry_run:
            with open(perf_file, 'w') as f:
                yaml.dump(perf_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            print(f"  Updated performance YAML with conductor (person_id: {conductor_id})")
        else:
            print(f"  [DRY RUN] Would update performance YAML with conductor (person_id: {conductor_id})")

    def process_performance(self, perf: Dict) -> bool:
        """Process a single performance to find and add conductor."""
        perf_id = perf['id']
        title = perf['title']

        print(f"\n[{perf_id}] {title}")

        # Skip if already has conductor
        if perf['conductor_count'] > 0:
            print("  Already has conductor, skipping")
            self.stats['already_have_conductor'] += 1
            return False

        conductor_name = None
        source = None

        # Try NRK API first
        if perf['prf_id']:
            nrk_data = self.fetch_nrk_program(perf['prf_id'])
            conductor_name = self.extract_conductor_from_nrk_api(nrk_data)
            if conductor_name:
                source = 'NRK API'
                self.stats['found_in_nrk_api'] += 1

        # Try performance description
        if not conductor_name and perf['description']:
            conductor_name = self.extract_conductor_from_description(perf['description'])
            if conductor_name:
                source = 'description'
                self.stats['found_in_description'] += 1

        # Try Gemini as fallback (commented out for initial run to save API calls)
        # if not conductor_name and perf['series_id'] and perf['year']:
        #     conductor_name = self.search_conductor_with_gemini(title, perf['series_id'], perf['year'])
        #     if conductor_name:
        #         source = 'Gemini'
        #         self.stats['found_via_gemini'] += 1

        if not conductor_name:
            print("  No conductor found")
            self.stats['not_found'] += 1
            return False

        print(f"  Found conductor: {conductor_name} (from {source})")

        # Look up or create person
        person_id = self.get_person_by_name(conductor_name)

        if not person_id:
            person_id = self.create_person(conductor_name)
        else:
            print(f"  Found existing person (ID: {person_id})")

        # Update performance YAML
        self.update_performance_yaml(perf_id, person_id)
        self.stats['updated'] += 1

        return True

    def run(self, limit: Optional[int] = None):
        """Run the enrichment process."""
        performances = self.get_concert_performances()
        self.stats['total'] = len(performances)

        print(f"Found {len(performances)} NRK concert performances")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print("=" * 80)

        if limit:
            performances = performances[:limit]
            print(f"Processing first {limit} performances...")

        for perf in performances:
            try:
                self.process_performance(perf)
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                print(f"  ERROR: {e}")
                self.stats['errors'] += 1

        print("\n" + "=" * 80)
        print("STATISTICS:")
        print(f"  Total performances: {self.stats['total']}")
        print(f"  Already have conductor: {self.stats['already_have_conductor']}")
        print(f"  Found in NRK API: {self.stats['found_in_nrk_api']}")
        print(f"  Found in description: {self.stats['found_in_description']}")
        print(f"  Found via Gemini: {self.stats['found_via_gemini']}")
        print(f"  Not found: {self.stats['not_found']}")
        print(f"  Updated: {self.stats['updated']}")
        print(f"  Errors: {self.stats['errors']}")

    def close(self):
        """Close database connection."""
        self.conn.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Enrich NRK concert performances with conductor data')
    parser.add_argument('--live', action='store_true', help='Actually modify files (default is dry run)')
    parser.add_argument('--limit', type=int, help='Process only first N performances')
    parser.add_argument('--with-gemini', action='store_true', help='Enable Gemini fallback (costs API credits)')

    args = parser.parse_args()

    enricher = ConductorEnricher(dry_run=not args.live)

    try:
        enricher.run(limit=args.limit)
    finally:
        enricher.close()
