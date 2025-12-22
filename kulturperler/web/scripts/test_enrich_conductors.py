#!/usr/bin/env python3
"""
Test script to enrich just a few bergenphilive performances with conductor data.
"""

import os
import sys
import yaml
import requests
import time
import re
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()
API_KEY = os.getenv('GEMINI_KEY')
if not API_KEY:
    print("Error: GEMINI_KEY not found in .env")
    sys.exit(1)

DATA_DIR = Path('data')
PERFORMANCES_DIR = DATA_DIR / 'performances'
PERSONS_DIR = DATA_DIR / 'persons'
EXTERNAL_RESOURCES_FILE = DATA_DIR / 'external_resources.yaml'

def load_yaml(path):
    """Load YAML file."""
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f)

def save_yaml(path, data):
    """Save YAML file."""
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

def get_external_resources():
    """Load external resources and create a lookup by title."""
    resources = load_yaml(EXTERNAL_RESOURCES_FILE)
    bergenphil_resources = {}

    for resource in resources:
        if resource.get('type') == 'bergenphilive':
            title = resource.get('title', '')
            bergenphil_resources[title] = resource

    return bergenphil_resources

def search_conductor_with_gemini(concert_url, title, year):
    """Use Gemini with Google Search to find conductor information."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={API_KEY}"

    query = f"""Find the conductor (dirigent) for this Bergen Philharmonic concert:
URL: {concert_url}
Title: {title}
Year: {year}

Search the URL or search for "Bergen Filharmoniske {title} {year} dirigent".
Provide ONLY the conductor's full name, or "NOT_FOUND" if you cannot find it.
Format: Just the name like "Edward Gardner" or "NOT_FOUND"
"""

    payload = {
        "contents": [{"parts": [{"text": query}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.1}
    }

    try:
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        result = r.json()

        if 'candidates' in result and len(result['candidates']) > 0:
            candidate = result['candidates'][0]
            if 'content' in candidate and 'parts' in candidate['content']:
                parts = candidate['content']['parts']
                text_parts = [p['text'] for p in parts if 'text' in p]
                return '\n'.join(text_parts) if text_parts else None
        return None
    except Exception as e:
        print(f"  Error calling Gemini: {e}")
        return None

def extract_conductor_from_response(response_text):
    """Extract conductor name from Gemini response."""
    if not response_text:
        return None

    response_text = response_text.strip()

    # Check for explicit NOT_FOUND
    if 'NOT_FOUND' in response_text.upper():
        return None

    # Common indicators that there's no conductor info
    response_lower = response_text.lower()
    if any(phrase in response_lower for phrase in [
        'could not find', 'no information', 'unable to find',
        'not available', 'no conductor', 'not specified', 'cannot find'
    ]):
        return None

    # If response is short and looks like a name, return it
    if len(response_text) < 50 and not '\n' in response_text:
        name = response_text.strip()
        name = re.sub(r'^(Conductor|Dirigent):\s*', '', name, flags=re.IGNORECASE)
        name = name.split('(')[0].strip()
        name = name.split(',')[0].strip()
        if name and len(name) > 2 and not name.lower().startswith('http'):
            return name

    # Look for conductor mentions in multi-line response
    lines = response_text.split('\n')
    for line in lines:
        line_lower = line.lower()
        if 'dirigent' in line_lower or 'conductor' in line_lower:
            for sep in [':', '-', '–']:
                if sep in line:
                    parts = line.split(sep, 1)
                    if len(parts) == 2:
                        name = parts[1].strip()
                        name = name.split('(')[0].strip()
                        name = name.split(',')[0].strip()
                        if name and len(name) > 2 and not name.lower().startswith('http'):
                            return name

    return None

def main():
    print("Testing conductor enrichment with first 3 performances...")
    print("=" * 70)

    # Load external resources
    external_resources = get_external_resources()
    print(f"Loaded {len(external_resources)} bergenphilive external resources\n")

    # Get first 3 bergenphilive performances
    performances = []
    for perf_file in sorted(PERFORMANCES_DIR.glob('*.yaml')):
        perf = load_yaml(perf_file)
        if perf.get('source') == 'bergenphilive':
            perf['_file'] = perf_file
            performances.append(perf)
            if len(performances) >= 3:
                break

    print(f"Testing with {len(performances)} performances:\n")

    for i, perf in enumerate(performances, 1):
        title = perf.get('title', '')
        year = perf.get('year', '')

        print(f"[{i}/{len(performances)}] {title} ({year})")

        # Find URL
        concert_url = ""
        if title in external_resources:
            concert_url = external_resources[title].get('url')
            print(f"  URL: {concert_url}")
        else:
            print(f"  Warning: No URL found")

        # Search for conductor
        print("  Searching...")
        response = search_conductor_with_gemini(concert_url, title, year)

        if response:
            print(f"  Raw response: {response}")
            conductor_name = extract_conductor_from_response(response)

            if conductor_name:
                print(f"  ✓ Found conductor: {conductor_name}")
            else:
                print(f"  ✗ Could not extract conductor name")
        else:
            print(f"  ✗ No response from Gemini")

        print()
        time.sleep(2)  # Rate limiting

    print("=" * 70)
    print("Test complete. Review results above.")
    print("If results look good, run: python3 scripts/enrich_bergenphilive_conductors.py")

if __name__ == '__main__':
    main()
