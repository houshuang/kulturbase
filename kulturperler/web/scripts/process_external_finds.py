#!/usr/bin/env python3
"""
Process external platform finds and add to database.

Reads output/youtube_gemini_search.json and output/external_archive_finds.json
and adds relevant content to data/external_resources.yaml.
"""

import json
import re
import yaml
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / 'data'
OUTPUT_DIR = Path(__file__).parent.parent / 'output'

def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def save_yaml(path, data):
    def str_representer(dumper, data):
        if '\n' in data:
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
        return dumper.represent_scalar('tag:yaml.org,2002:str', data)
    yaml.add_representer(str, str_representer)

    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

def is_valid_youtube_url(url):
    """Check if YouTube URL has a valid 11-character video ID."""
    if not url or url == 'https://www.youtube.com/watch?v=null':
        return False
    match = re.search(r'youtube\.com/watch\?v=([\w-]{11})$', url)
    return match is not None

def parse_duration(duration_str):
    """Parse duration string like '1:39:57' or '31:26' to minutes."""
    if not duration_str:
        return None
    parts = duration_str.split(':')
    try:
        if len(parts) == 3:
            return int(parts[0]) * 60 + int(parts[1]) + int(parts[2]) / 60
        elif len(parts) == 2:
            return int(parts[0]) + int(parts[1]) / 60
        return None
    except ValueError:
        return None

def load_works():
    """Load all works from YAML files for matching."""
    works = {}
    works_dir = DATA_DIR / 'plays'  # Still using plays directory
    for f in works_dir.glob('*.yaml'):
        w = load_yaml(f)
        works[w['id']] = w
        # Index by normalized title for matching
        title_lower = w['title'].lower()
        works[title_lower] = w
    return works

def find_work_by_title(works, title):
    """Try to find a work by title."""
    title_lower = title.lower()

    # Direct match
    if title_lower in works:
        return works[title_lower]

    # Partial match
    for key, work in works.items():
        if isinstance(key, str) and key in title_lower:
            return work
        if isinstance(work, dict) and work.get('title', '').lower() in title_lower:
            return work

    return None

def process_youtube_videos():
    """Process YouTube videos and return valid entries."""
    youtube_file = OUTPUT_DIR / 'youtube_gemini_search.json'
    if not youtube_file.exists():
        print("No YouTube data file found")
        return []

    with open(youtube_file) as f:
        data = json.load(f)

    valid_videos = []
    for video in data.get('videos', []):
        url = video.get('url', '')
        if not is_valid_youtube_url(url):
            continue

        duration = parse_duration(video.get('duration'))

        # Filter for substantial content (>15 minutes for music, >30 for performances)
        if duration and duration < 15:
            continue

        valid_videos.append({
            'title': video.get('title', ''),
            'url': url,
            'channel': video.get('channel', ''),
            'duration_minutes': int(duration) if duration else None,
            'views': video.get('views', ''),
            'source': 'youtube'
        })

    return valid_videos

def process_archive_finds():
    """Process Archive.org finds and return complete performances."""
    archive_file = OUTPUT_DIR / 'external_archive_finds.json'
    if not archive_file.exists():
        print("No Archive.org data file found")
        return []

    with open(archive_file) as f:
        data = json.load(f)

    complete_performances = []
    for item in data.get('all_results', []):
        classification = item.get('classification', {})

        # Skip if not a complete performance
        if not classification.get('is_complete_performance'):
            continue

        # Skip if classification error
        if classification.get('error'):
            continue

        # Skip non-Norwegian content (unless it's opera/ballet)
        content_type = classification.get('content_type', '')
        is_norwegian = classification.get('is_norwegian', False)

        # Include Norwegian content and complete operas/ballets regardless
        if not is_norwegian and content_type not in ['opera', 'ballet', 'symphony', 'theatre']:
            continue

        complete_performances.append({
            'identifier': item.get('identifier', ''),
            'title': item.get('title', ''),
            'url': item.get('url', ''),
            'description': item.get('description', '')[:500] if item.get('description') else '',
            'creator': item.get('creator', ''),
            'content_type': content_type,
            'work_title': classification.get('work_title'),
            'composer_playwright': classification.get('composer_playwright'),
            'performing_company': classification.get('performing_company'),
            'is_norwegian': is_norwegian,
            'source': 'archive.org'
        })

    return complete_performances

def main():
    print("=" * 60)
    print("Processing External Platform Finds")
    print("=" * 60)

    # Load existing external resources
    resources_file = DATA_DIR / 'external_resources.yaml'
    existing_resources = load_yaml(resources_file) if resources_file.exists() else []
    existing_urls = {r['url'] for r in existing_resources}

    # Find max ID
    max_id = max([r['id'] for r in existing_resources], default=0)
    next_id = max_id + 1

    # Load works for linking
    works = load_works()

    # Process YouTube
    print("\n--- Processing YouTube Videos ---")
    youtube_videos = process_youtube_videos()
    print(f"Found {len(youtube_videos)} valid YouTube videos")

    new_youtube = []
    for video in youtube_videos:
        if video['url'] in existing_urls:
            continue

        resource = {
            'id': next_id,
            'url': video['url'],
            'title': video['title'],
            'type': 'youtube',
            'description': f"Channel: {video['channel']}. Duration: {video['duration_minutes']} min" if video['duration_minutes'] else f"Channel: {video['channel']}",
            'added_date': datetime.now().isoformat(),
            'is_working': 1
        }
        new_youtube.append(resource)
        next_id += 1

    print(f"New YouTube resources to add: {len(new_youtube)}")

    # Process Archive.org
    print("\n--- Processing Archive.org Finds ---")
    archive_finds = process_archive_finds()
    print(f"Found {len(archive_finds)} complete performances")

    new_archive = []
    for item in archive_finds:
        if item['url'] in existing_urls:
            continue

        desc_parts = []
        if item['work_title']:
            desc_parts.append(f"Work: {item['work_title']}")
        if item['composer_playwright']:
            desc_parts.append(f"By: {item['composer_playwright']}")
        if item['performing_company']:
            desc_parts.append(f"Performed by: {item['performing_company']}")
        if item['content_type']:
            desc_parts.append(f"Type: {item['content_type']}")

        resource = {
            'id': next_id,
            'url': item['url'],
            'title': item['title'],
            'type': 'archive_external',
            'description': '. '.join(desc_parts) if desc_parts else item['description'][:200],
            'added_date': datetime.now().isoformat(),
            'is_working': 1
        }
        new_archive.append(resource)
        next_id += 1

    print(f"New Archive.org resources to add: {len(new_archive)}")

    # Combine and save
    all_new = new_youtube + new_archive
    if all_new:
        updated_resources = existing_resources + all_new
        save_yaml(resources_file, updated_resources)
        print(f"\n✓ Added {len(all_new)} new external resources")
        print(f"  Total resources: {len(updated_resources)}")
    else:
        print("\nNo new resources to add (all already exist)")

    # Print summary of notable additions
    print("\n--- Notable New Additions ---")
    for r in all_new[:20]:
        print(f"  [{r['type']}] {r['title'][:60]}...")

    return all_new

if __name__ == '__main__':
    main()
