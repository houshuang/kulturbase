#!/usr/bin/env python3
"""
Fetch NRK programs ABOUT playwrights (documentaries, discussions, etc.)
and store them for display on author detail pages.
"""

import sqlite3
import requests
import time
import re
from datetime import datetime

DB_PATH = 'static/kulturperler.db'
NRK_SEARCH_API = 'https://psapi.nrk.no/search'
NRK_PROGRAM_API = 'https://psapi.nrk.no/programs'

# Keywords for scoring
HIGH_SCORE_KEYWORDS = ['dokumentar', 'portrett', 'samtale', 'debatt', 'lesning',
                       'opplesning', 'dramatisering', 'jubileum', 'minne',
                       'forfatter', 'dramatiker', 'dikter', 'nobel']
EXCLUDE_KEYWORDS = ['dagsrevyen', 'aktuelt', 'nyhetsmorgen', 'nyhetene']

def parse_duration(iso_duration):
    """Parse ISO 8601 duration (e.g., PT1H17M7.56S) to seconds."""
    if not iso_duration:
        return None
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?', iso_duration)
    if match:
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = float(match.group(3) or 0)
        return int(hours * 3600 + minutes * 60 + seconds)
    return None

def compute_interest_score(title, description, duration, author_name):
    """Compute relevance score for a program."""
    score = 0
    text = f"{title} {description or ''}".lower()

    # Author name in title is highly relevant
    if author_name.lower() in title.lower():
        score += 50

    # Duration bonus (longer = more substantial)
    if duration:
        if duration > 3600:  # > 1 hour
            score += 30
        elif duration > 1800:  # > 30 min
            score += 20
        elif duration > 900:  # > 15 min
            score += 10

    # Keyword bonuses
    for keyword in HIGH_SCORE_KEYWORDS:
        if keyword in text:
            score += 15

    # Exclude penalty
    for keyword in EXCLUDE_KEYWORDS:
        if keyword in text:
            score -= 100

    return score

def search_nrk(query):
    """Search NRK for programs matching query."""
    headers = {'User-Agent': 'Kulturperler/1.0 (educational project)'}
    params = {'q': query, 'page': 1, 'pageSize': 30}

    try:
        response = requests.get(NRK_SEARCH_API, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"  Search error: {e}")
        return None

def get_program_details(program_id):
    """Get detailed program info including duration."""
    headers = {'User-Agent': 'Kulturperler/1.0 (educational project)'}

    try:
        response = requests.get(f"{NRK_PROGRAM_API}/{program_id}", headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"    Details error for {program_id}: {e}")
        return None

def get_series_details(series_id):
    """Get series info including episodes."""
    headers = {'User-Agent': 'Kulturperler/1.0 (educational project)'}

    try:
        # Get series with embedded episodes
        url = f"https://psapi.nrk.no/tv/catalog/series/{series_id}"
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"    Series error for {series_id}: {e}")
        return None

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get playwrights (persons with plays in DB)
    cursor.execute("""
        SELECT DISTINCT p.id, p.name
        FROM persons p
        JOIN plays pl ON p.id = pl.playwright_id
        ORDER BY p.name
    """)
    playwrights = cursor.fetchall()

    print(f"Searching NRK for programs about {len(playwrights)} playwrights...")

    # Get existing episodes to exclude
    cursor.execute("SELECT prf_id FROM episodes")
    existing_episodes = {row['prf_id'] for row in cursor.fetchall()}

    # Get already processed programs
    cursor.execute("SELECT id FROM nrk_about_programs")
    existing_about = {row['id'] for row in cursor.fetchall()}

    total_added = 0

    for playwright in playwrights:
        person_id = playwright['id']
        name = playwright['name']
        print(f"\n{name}...")

        # Search NRK
        search_result = search_nrk(name)
        if not search_result:
            continue

        hits = search_result.get('hits', [])
        print(f"  Found {len(hits)} search results")

        for hit_wrapper in hits:
            # API returns nested structure: {type, hit, highlights}
            hit = hit_wrapper.get('hit', {})
            hit_type = hit_wrapper.get('type', '')

            program_id = hit.get('id')
            if not program_id:
                continue

            # Skip if already in episodes or already processed
            if program_id in existing_episodes:
                continue
            if program_id in existing_about:
                continue

            title = hit.get('title', '')
            description = hit.get('description', '')

            # Handle series - get series info and first episode
            if hit_type == 'serie':
                time.sleep(0.3)
                series_details = get_series_details(program_id)
                if not series_details:
                    continue

                # Get total duration and episode count
                episodes_list = series_details.get('_embedded', {}).get('episodes', [])
                if not episodes_list:
                    continue

                total_duration = sum(parse_duration(ep.get('duration')) or 0 for ep in episodes_list)
                episode_count = len(episodes_list)

                # Filter: minimum 10 minutes total
                if total_duration < 600:
                    continue

                # Use series URL
                nrk_url = f"https://tv.nrk.no/serie/{program_id}"
                program_type = 'serie'
                duration = total_duration
                year = None

                # Get year from first episode
                if episodes_list:
                    first_aired = episodes_list[0].get('firstTransmissionDateDisplayValue', '')
                    if first_aired:
                        year_match = re.search(r'(\d{4})', first_aired)
                        if year_match:
                            year = int(year_match.group(1))

            else:
                # Get program details for duration
                time.sleep(0.3)
                details = get_program_details(program_id)
                if not details:
                    continue

                # Parse duration
                duration_iso = details.get('duration')
                duration = parse_duration(duration_iso)

                # Filter: minimum 10 minutes
                if not duration or duration < 600:
                    print(f"    Skipped {title[:30]}: duration {duration}")
                    continue

                # Check availability - be more lenient
                availability = details.get('availability', {})
                avail_status = availability.get('status', '')
                if avail_status not in ['available', 'onDemand']:
                    print(f"    Skipped {title[:30]}: status {avail_status}")
                    continue

                nrk_url = f"https://tv.nrk.no/program/{program_id}"
                program_type = hit_type

                # Get year from firstAired
                year = None
                first_aired = details.get('firstAired')
                if first_aired:
                    try:
                        year = datetime.fromisoformat(first_aired.replace('Z', '+00:00')).year
                    except:
                        pass

            # Compute interest score
            score = compute_interest_score(title, description, duration, name)

            # Skip low-score items
            if score < 0:
                continue

            # Get image from search hit
            image_data = hit.get('image', {})
            image_url = None
            web_images = image_data.get('webImages', [])
            if web_images:
                image_url = web_images[0].get('imageUrl')

            # Insert into database
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO nrk_about_programs
                    (id, person_id, title, description, duration_seconds, image_url, nrk_url, program_type, year, interest_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (program_id, person_id, title, description, duration, image_url, nrk_url, program_type, year, score))
                conn.commit()
                existing_about.add(program_id)
                total_added += 1
                print(f"    Added: {title} ({duration//60} min, score: {score})")
            except Exception as e:
                print(f"    DB error: {e}")

        time.sleep(0.5)  # Rate limit between authors

    # Summary
    cursor.execute("SELECT COUNT(*) FROM nrk_about_programs")
    total = cursor.fetchone()[0]

    print(f"\n=== Summary ===")
    print(f"Added {total_added} new programs")
    print(f"Total programs in database: {total}")

    # Show top programs by score
    cursor.execute("""
        SELECT n.title, n.interest_score, n.duration_seconds, p.name
        FROM nrk_about_programs n
        JOIN persons p ON n.person_id = p.id
        ORDER BY n.interest_score DESC
        LIMIT 10
    """)
    print("\nTop programs by interest score:")
    for row in cursor.fetchall():
        print(f"  {row[3]}: {row[0]} (score: {row[1]}, {row[2]//60} min)")

    conn.close()

if __name__ == '__main__':
    main()
