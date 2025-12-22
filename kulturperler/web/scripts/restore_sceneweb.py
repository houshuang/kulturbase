#!/usr/bin/env python3
"""
Restore sceneweb links from old database to YAML files.

This script matches plays by title (not ID) and verifies each match
by fetching the sceneweb URL to confirm the title.
"""

import yaml
import re
import time
import requests
from pathlib import Path
from bs4 import BeautifulSoup

DATA_DIR = Path(__file__).parent.parent / 'data'
PLAYS_DIR = DATA_DIR / 'plays'

# Rate limit for sceneweb requests
REQUEST_DELAY = 0.5  # seconds between requests


def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)


def save_yaml(path, data):
    with open(path, 'w') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def normalize_title(title):
    """Normalize title for matching."""
    if not title:
        return ""
    # Lowercase, remove extra spaces
    t = title.lower().strip()
    # Remove common punctuation variations
    t = re.sub(r'[,.:;!?"\']', '', t)
    t = re.sub(r'\s+', ' ', t)
    return t


def fetch_sceneweb_title(url):
    """Fetch the title from a sceneweb URL for verification."""
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Try to find the title - it's usually in h1
            h1 = soup.find('h1')
            if h1:
                return h1.get_text().strip()
            # Fallback to title tag
            title_tag = soup.find('title')
            if title_tag:
                return title_tag.get_text().split('|')[0].strip()
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
    return None


def titles_match(title1, title2):
    """Check if two titles match (allowing for minor variations)."""
    if not title1 or not title2:
        return False
    n1 = normalize_title(title1)
    n2 = normalize_title(title2)
    # Exact normalized match
    if n1 == n2:
        return True
    # One contains the other (for cases like "Hedda Gabler" vs "Hedda Gabler - sceneweb")
    if n1 in n2 or n2 in n1:
        return True
    return False


def main():
    # Load old sceneweb data from extracted file
    print("Loading old sceneweb data...")
    old_sceneweb = {}  # title -> (sceneweb_id, sceneweb_url)

    with open('/tmp/sceneweb_full.txt') as f:
        for line in f:
            parts = line.strip().split('|')
            if len(parts) >= 4:
                old_id, title, sceneweb_id, sceneweb_url = parts[0], parts[1], parts[2], parts[3]
                old_sceneweb[title] = (int(sceneweb_id), sceneweb_url)

    print(f"Loaded {len(old_sceneweb)} plays with sceneweb data")

    # Build normalized title index
    old_normalized = {}
    for title, data in old_sceneweb.items():
        norm = normalize_title(title)
        old_normalized[norm] = (title, data)

    # Load current play YAML files
    print("\nLoading current play YAML files...")
    current_plays = {}  # title -> (file_path, data)
    current_normalized = {}  # normalized_title -> original_title

    for yaml_file in PLAYS_DIR.glob('*.yaml'):
        data = load_yaml(yaml_file)
        if data and 'title' in data:
            title = data['title']
            current_plays[title] = (yaml_file, data)
            norm = normalize_title(title)
            current_normalized[norm] = title

    print(f"Loaded {len(current_plays)} current plays")

    # Match and verify
    print("\nMatching plays...")
    matched = []
    unmatched_old = []
    verification_failed = []

    for old_title, (sceneweb_id, sceneweb_url) in old_sceneweb.items():
        # Try exact match first
        if old_title in current_plays:
            matched.append((old_title, old_title, sceneweb_id, sceneweb_url))
            continue

        # Try normalized match
        norm = normalize_title(old_title)
        if norm in current_normalized:
            current_title = current_normalized[norm]
            matched.append((old_title, current_title, sceneweb_id, sceneweb_url))
            continue

        # No match found
        unmatched_old.append((old_title, sceneweb_id, sceneweb_url))

    print(f"\nMatched: {len(matched)}")
    print(f"Unmatched: {len(unmatched_old)}")

    # Verify matches by fetching sceneweb and update YAML files
    print("\nVerifying matches and updating YAML files...")
    updated = 0
    skipped_already_has = 0

    for i, (old_title, current_title, sceneweb_id, sceneweb_url) in enumerate(matched):
        yaml_file, data = current_plays[current_title]

        # Skip if already has sceneweb data
        if data.get('sceneweb_id') or data.get('sceneweb_url'):
            skipped_already_has += 1
            continue

        # Verify by fetching sceneweb page
        print(f"[{i+1}/{len(matched)}] Verifying: {current_title}")
        time.sleep(REQUEST_DELAY)

        fetched_title = fetch_sceneweb_title(sceneweb_url)
        if fetched_title and titles_match(current_title, fetched_title):
            # Match verified - update YAML
            data['sceneweb_id'] = sceneweb_id
            data['sceneweb_url'] = sceneweb_url
            save_yaml(yaml_file, data)
            updated += 1
            print(f"  OK: Added sceneweb_id={sceneweb_id}")
        else:
            verification_failed.append((old_title, current_title, sceneweb_url, fetched_title))
            print(f"  FAILED: sceneweb title='{fetched_title}' doesn't match '{current_title}'")

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total old sceneweb entries: {len(old_sceneweb)}")
    print(f"Matched by title: {len(matched)}")
    print(f"Successfully updated: {updated}")
    print(f"Skipped (already has sceneweb): {skipped_already_has}")
    print(f"Verification failed: {len(verification_failed)}")
    print(f"Unmatched (no current play found): {len(unmatched_old)}")

    if verification_failed:
        print("\n--- VERIFICATION FAILURES ---")
        for old_title, current_title, url, fetched in verification_failed:
            print(f"  '{current_title}' vs sceneweb '{fetched}' ({url})")

    if unmatched_old:
        print("\n--- UNMATCHED OLD PLAYS (first 20) ---")
        for old_title, sceneweb_id, sceneweb_url in unmatched_old[:20]:
            print(f"  {old_title} -> {sceneweb_url}")
        if len(unmatched_old) > 20:
            print(f"  ... and {len(unmatched_old) - 20} more")


if __name__ == '__main__':
    main()
