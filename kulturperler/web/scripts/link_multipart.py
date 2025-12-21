#!/usr/bin/env python3
"""
Phase 4: Link multi-part performances.

Groups episodes into performances, identifying multi-part broadcasts and introductions.
Outputs: output/classical_performances.json
"""

import json
import re
import uuid
from pathlib import Path
from datetime import datetime
from collections import defaultdict

OUTPUT_DIR = Path(__file__).parent.parent / "output"
INPUT_FILE = OUTPUT_DIR / "classical_classified.json"
OUTPUT_FILE = OUTPUT_DIR / "classical_performances.json"


def extract_part_info(title, classification):
    """Extract part number from title or classification."""
    # Check classification first
    part_indicator = classification.get('part_indicator')
    if part_indicator:
        # Parse indicators like "1/2", "del 1", "1:2"
        match = re.search(r'(\d+)\s*[/:av]\s*(\d+)', str(part_indicator))
        if match:
            return int(match.group(1)), int(match.group(2))
        match = re.search(r'del\s*(\d+)', str(part_indicator).lower())
        if match:
            return int(match.group(1)), None

    # Check title
    patterns = [
        r'[\(\[]?\s*(\d+)\s*[/:]\s*(\d+)\s*[\)\]]?',  # (1/2), 1:2
        r'del\s+(\d+)\s+av\s+(\d+)',  # del 1 av 2
        r'del\s+(\d+)',  # del 1
        r'part\s+(\d+)',  # part 1
        r'episode\s+(\d+)',  # episode 1
    ]

    for pattern in patterns:
        match = re.search(pattern, title.lower())
        if match:
            part = int(match.group(1))
            total = int(match.group(2)) if len(match.groups()) > 1 else None
            return part, total

    return None, None


def normalize_work_title(title):
    """Normalize work title for matching."""
    if not title:
        return None

    # Lowercase and remove special characters
    normalized = title.lower()
    normalized = re.sub(r'[^\w\s]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized).strip()

    return normalized


def group_performances(episodes):
    """Group episodes into performances."""
    # Group by series_id + work_title + composer
    groups = defaultdict(list)

    for ep in episodes:
        cls = ep.get('classification', {})

        series_id = ep.get('series_id', '')
        work_title = cls.get('work_title', '')
        composer = cls.get('composer', '')

        # Create grouping key
        normalized_title = normalize_work_title(work_title) or ''
        normalized_composer = (composer or '').lower().strip()

        # Group by series + work + composer
        key = f"{series_id}|{normalized_title}|{normalized_composer}"
        groups[key].append(ep)

    return groups


def create_performance(episodes, performance_id):
    """Create a performance object from grouped episodes."""
    if not episodes:
        return None

    # Get common info from first episode's classification
    first_cls = episodes[0].get('classification', {})

    # Sort episodes by part number or episode number
    sorted_episodes = []
    for ep in episodes:
        cls = ep.get('classification', {})
        part_num, total_parts = extract_part_info(ep.get('title', ''), cls)
        ep_num = ep.get('episode_number')

        sorted_episodes.append({
            **ep,
            '_part_num': part_num or ep_num or 0,
            '_total_parts': total_parts,
        })

    sorted_episodes.sort(key=lambda x: x.get('_part_num', 0))

    # Separate introductions from main parts
    main_parts = []
    introductions = []

    for ep in sorted_episodes:
        cls = ep.get('classification', {})
        if cls.get('content_type') == 'introduction':
            introductions.append(ep)
        else:
            main_parts.append(ep)

    # Calculate total duration
    total_duration = sum(ep.get('duration_seconds', 0) for ep in sorted_episodes)

    # Get year (earliest)
    years = [ep.get('year') for ep in sorted_episodes if ep.get('year')]
    year = min(years) if years else None

    # Build episode list
    episode_list = []
    for ep in sorted_episodes:
        part_num, total = extract_part_info(ep.get('title', ''), ep.get('classification', {}))
        episode_list.append({
            'prf_id': ep.get('prf_id'),
            'title': ep.get('title'),
            'part_number': part_num,
            'duration_seconds': ep.get('duration_seconds'),
            'is_introduction': ep.get('classification', {}).get('content_type') == 'introduction',
            'nrk_url': ep.get('nrk_url'),
        })

    return {
        'performance_id': performance_id,
        'work_title': first_cls.get('work_title'),
        'work_title_original': first_cls.get('work_title_original'),
        'composer': first_cls.get('composer'),
        'genre': first_cls.get('genre'),
        'performance_language': first_cls.get('performance_language'),
        'is_norwegian_translation': first_cls.get('is_norwegian_translation', False),
        'based_on_literary_work': first_cls.get('based_on_literary_work'),
        'series_id': sorted_episodes[0].get('series_id') if sorted_episodes else None,
        'series_title': sorted_episodes[0].get('series_title') if sorted_episodes else None,
        'year': year,
        'medium': sorted_episodes[0].get('medium') if sorted_episodes else None,
        'total_duration_seconds': total_duration,
        'part_count': len(main_parts),
        'has_introduction': len(introductions) > 0,
        'episodes': episode_list,
        'image_url': sorted_episodes[0].get('image_url') if sorted_episodes else None,
    }


def main():
    print("=" * 60)
    print("Phase 4: Linking Multi-Part Performances")
    print("=" * 60)

    # Load classified episodes
    if not INPUT_FILE.exists():
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        print("Please run classify_with_gemini.py first.")
        return

    with open(INPUT_FILE) as f:
        data = json.load(f)

    # Get classical performances and introductions
    performances = data.get('classical_performances', [])
    introductions = data.get('introductions', [])

    print(f"Found {len(performances)} classical performances")
    print(f"Found {len(introductions)} introductions")

    # Combine for grouping
    all_episodes = performances + introductions

    # Group into performances
    groups = group_performances(all_episodes)
    print(f"Created {len(groups)} episode groups")

    # Create performance objects
    performance_list = []
    multipart_count = 0
    with_intro_count = 0

    for group_key, episodes in groups.items():
        perf_id = str(uuid.uuid4())[:8]
        performance = create_performance(episodes, perf_id)

        if performance:
            performance_list.append(performance)

            if performance['part_count'] > 1:
                multipart_count += 1
            if performance['has_introduction']:
                with_intro_count += 1

    # Sort by work title
    performance_list.sort(key=lambda x: (x.get('work_title') or '', x.get('year') or 0))

    # Count by genre
    genre_counts = defaultdict(int)
    for perf in performance_list:
        genre_counts[perf.get('genre', 'unknown')] += 1

    # Count Norwegian translations
    norwegian_translations = [p for p in performance_list if p.get('is_norwegian_translation')]

    # Output
    output_data = {
        'linked_at': datetime.now().isoformat(),
        'statistics': {
            'total_performances': len(performance_list),
            'multipart_performances': multipart_count,
            'with_introduction': with_intro_count,
            'norwegian_translations': len(norwegian_translations),
            'by_genre': dict(genre_counts),
        },
        'performances': performance_list,
    }

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("LINKING COMPLETE")
    print("=" * 60)
    print(f"Total performances: {len(performance_list)}")
    print(f"Multi-part broadcasts: {multipart_count}")
    print(f"With introduction: {with_intro_count}")
    print(f"Norwegian translations: {len(norwegian_translations)}")
    print(f"\nBy genre:")
    for genre, count in sorted(genre_counts.items(), key=lambda x: -x[1]):
        print(f"  {genre}: {count}")
    print(f"\nOutput written to: {OUTPUT_FILE}")

    # Show some multi-part examples
    multipart = [p for p in performance_list if p['part_count'] > 1]
    if multipart:
        print("\n--- Sample Multi-Part Performances ---")
        for perf in multipart[:5]:
            print(f"  {perf.get('work_title')} ({perf.get('year')})")
            print(f"    Composer: {perf.get('composer')}")
            print(f"    Parts: {perf.get('part_count')}")
            print(f"    Episodes: {[e['prf_id'] for e in perf['episodes']]}")


if __name__ == "__main__":
    main()
