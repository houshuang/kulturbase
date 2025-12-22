#!/usr/bin/env python3
"""
Comprehensive processing of ALL external platform finds.

Processes:
- ALL 38 complete performances from Archive.org
- ALL valid YouTube videos (11-char video IDs)
- Links to specific works where possible
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
    if url == 'https://www.youtube.com/watch?v=...':
        return False
    # Valid YouTube video IDs are 11 characters
    match = re.search(r'youtube\.com/watch\?v=([\w-]{11})$', url)
    return match is not None

def process_archive_finds():
    """Process ALL complete Archive.org performances."""
    archive_file = OUTPUT_DIR / 'external_archive_finds.json'
    if not archive_file.exists():
        print("No Archive.org data file found")
        return []

    with open(archive_file) as f:
        data = json.load(f)

    complete_performances = []
    for item in data.get('all_results', []):
        classification = item.get('classification', {})

        # Include ALL complete performances
        if not classification.get('is_complete_performance'):
            continue

        # Skip if classification error
        if classification.get('error'):
            continue

        content_type = classification.get('content_type', '')

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
            'is_norwegian': classification.get('is_norwegian', False),
            'source': 'archive.org'
        })

    return complete_performances

def process_youtube_videos():
    """Process ALL valid YouTube videos."""
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

        valid_videos.append({
            'title': video.get('title', ''),
            'url': url,
            'channel': video.get('channel', ''),
            'duration': video.get('duration'),
            'views': video.get('views', ''),
            'source': 'youtube'
        })

    return valid_videos

def load_existing_resources():
    """Load existing external resources."""
    resources_file = DATA_DIR / 'external_resources.yaml'
    if resources_file.exists():
        return load_yaml(resources_file)
    return []

def find_work_by_title_pattern(works_dir, patterns):
    """Find work files matching title patterns."""
    matches = []
    for f in works_dir.glob('*.yaml'):
        w = load_yaml(f)
        title_lower = w.get('title', '').lower()
        for pattern in patterns:
            if pattern.lower() in title_lower:
                matches.append((f, w))
                break
    return matches

def main():
    print("=" * 60)
    print("Comprehensive External Platform Processing")
    print("=" * 60)

    # Load existing resources
    existing_resources = load_existing_resources()
    existing_urls = {r['url'] for r in existing_resources}
    max_id = max([r['id'] for r in existing_resources], default=0)
    next_id = max_id + 1

    new_resources = []

    # Process Archive.org
    print("\n--- Processing ALL Archive.org Complete Performances ---")
    archive_finds = process_archive_finds()
    print(f"Found {len(archive_finds)} complete performances")

    for item in archive_finds:
        if item['url'] in existing_urls:
            print(f"  [SKIP] Already exists: {item['title'][:50]}...")
            continue

        desc_parts = []
        if item['content_type']:
            desc_parts.append(f"Type: {item['content_type']}")
        if item['work_title']:
            desc_parts.append(f"Work: {item['work_title']}")
        if item['composer_playwright']:
            desc_parts.append(f"By: {item['composer_playwright']}")
        if item['performing_company']:
            desc_parts.append(f"Performer: {item['performing_company']}")

        resource = {
            'id': next_id,
            'url': item['url'],
            'title': item['title'],
            'type': f"archive_{item['content_type']}" if item['content_type'] else 'archive_external',
            'description': '. '.join(desc_parts) if desc_parts else item['description'][:200],
            'added_date': datetime.now().isoformat(),
            'is_working': 1
        }
        new_resources.append(resource)
        print(f"  [ADD] {item['title'][:60]}...")
        next_id += 1

    # Process YouTube
    print("\n--- Processing ALL Valid YouTube Videos ---")
    youtube_videos = process_youtube_videos()
    print(f"Found {len(youtube_videos)} valid YouTube videos")

    for video in youtube_videos:
        if video['url'] in existing_urls:
            print(f"  [SKIP] Already exists: {video['title'][:50]}...")
            continue

        desc = f"Channel: {video['channel']}"
        if video['duration']:
            desc += f". Duration: {video['duration']}"

        resource = {
            'id': next_id,
            'url': video['url'],
            'title': video['title'],
            'type': 'youtube',
            'description': desc,
            'added_date': datetime.now().isoformat(),
            'is_working': 1
        }
        new_resources.append(resource)
        print(f"  [ADD] {video['title'][:60]}...")
        next_id += 1

    # Save to external_resources.yaml
    resources_file = DATA_DIR / 'external_resources.yaml'
    if new_resources:
        updated_resources = existing_resources + new_resources
        save_yaml(resources_file, updated_resources)
        print(f"\n✓ Added {len(new_resources)} new external resources")
        print(f"  Total resources: {len(updated_resources)}")
    else:
        print("\nNo new resources to add (all already exist)")

    # Now link specific items to works
    print("\n--- Linking to Specific Works ---")
    works_dir = DATA_DIR / 'plays'

    # Work links to add
    work_links = {
        # Ibsen plays
        'en folkefiende': [
            ('https://archive.org/details/antetvca-An_Enemy_of_the_People_UCI_Arts',
             'An Enemy of the People - UCI Arts', 'archive.org', 'Engelsk oppsetning')
        ],
        'kjære løgnhals': [
            ('https://archive.org/details/NRKTV-FTEA64002564-AR-199412732',
             'Kjære løgnhals (1964) - Archive.org', 'archive.org', 'Ikke tilgjengelig på NRK.no')
        ],
        # Grieg works (for Peer Gynt)
        'peer gynt': [
            ('https://archive.org/details/grieg-symphony-in-c-minor',
             'Grieg: Symphony in C Minor', 'archive.org', None),
            ('https://archive.org/details/edward-grieg-holberg-suite-gerhard-oppitz-herbert-von-karajan',
             'Grieg: Holberg Suite - Karajan', 'archive.org', None),
            ('https://archive.org/details/edvard-hagerup-grieg',
             'Full Length Grieg Concert', 'archive.org', None),
        ],
    }

    for title_pattern, links in work_links.items():
        matches = find_work_by_title_pattern(works_dir, [title_pattern])
        if matches:
            for filepath, work in matches:
                existing_links = work.get('external_links', [])
                existing_link_urls = {l['url'] for l in existing_links}

                new_links = []
                for url, title, link_type, note in links:
                    if url not in existing_link_urls:
                        link = {'url': url, 'title': title, 'type': link_type}
                        if note:
                            link['access_note'] = note
                        new_links.append(link)

                if new_links:
                    work['external_links'] = existing_links + new_links
                    save_yaml(filepath, work)
                    print(f"  Added {len(new_links)} links to '{work['title']}'")

    # Add bergenphilive.no as a streaming platform reference
    print("\n--- Adding Streaming Platform References ---")

    # Check if bergenphilive reference exists
    bergenphilive_url = 'https://bergenphilive.no/alle-konsertopptak/'
    if bergenphilive_url not in existing_urls:
        streaming_resource = {
            'id': next_id,
            'url': bergenphilive_url,
            'title': 'Bergen Filharmoniske Orkester - Alle konsertopptak',
            'type': 'streaming_platform',
            'description': 'Gratis strømmetjeneste med 200+ konserter fra Bergen Filharmoniske Orkester. Inkluderer Grieg, Sæverud, Svendsen og mer.',
            'added_date': datetime.now().isoformat(),
            'is_working': 1
        }
        # Add to resources file
        resources = load_yaml(resources_file)
        resources.append(streaming_resource)
        save_yaml(resources_file, resources)
        print(f"  Added bergenphilive.no streaming platform")
        next_id += 1

    print("\n" + "=" * 60)
    print("PROCESSING COMPLETE")
    print("=" * 60)

if __name__ == '__main__':
    main()
