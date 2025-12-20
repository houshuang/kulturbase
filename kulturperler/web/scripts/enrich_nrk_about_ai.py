#!/usr/bin/env python3
"""
Fetch NRK programs ABOUT playwrights with AI-powered relevance filtering.
Uses Claude to assess whether each program is actually about the playwright.

Usage:
  # Dry run - show candidates without AI filtering or database changes
  python3 enrich_nrk_about_ai.py --dry-run

  # Full run with AI filtering (requires API key)
  export ANTHROPIC_API_KEY=sk-ant-...
  python3 enrich_nrk_about_ai.py

  # Process specific playwright only
  python3 enrich_nrk_about_ai.py --playwright "Henrik Ibsen"
"""

import sqlite3
import requests
import time
import re
import json
import os
import argparse
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "static" / "kulturperler.db"
CACHE_PATH = Path(__file__).parent.parent / "static" / "nrk_about_cache.json"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

def load_cache():
    if CACHE_PATH.exists():
        with open(CACHE_PATH) as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_PATH, 'w') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

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

def search_nrk(query):
    """Search NRK for programs matching query."""
    params = {'q': query, 'page': 1, 'pageSize': 30}
    try:
        response = requests.get('https://psapi.nrk.no/search', params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"  Search error: {e}")
        return None

def get_program_details(program_id):
    """Get detailed program info."""
    try:
        response = requests.get(f"https://psapi.nrk.no/programs/{program_id}", timeout=10)
        response.raise_for_status()
        return response.json()
    except:
        return None

def get_series_details(series_id):
    """Get series info."""
    try:
        url = f"https://psapi.nrk.no/tv/catalog/series/{series_id}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except:
        return None

def ai_assess_relevance(playwright_name, playwright_years, program_title, program_description, cache):
    """Use Claude to assess if program is actually about the playwright."""

    cache_key = f"ai:{playwright_name}:{program_title}"
    if cache_key in cache:
        return cache[cache_key]

    if not ANTHROPIC_API_KEY:
        print("  WARNING: No ANTHROPIC_API_KEY set, skipping AI review")
        return {"dominated": False, "dominated": None, "dominated": 0}

    prompt = f"""You are assessing whether an NRK TV program is specifically ABOUT a playwright/author.

Playwright: {playwright_name}
{f"Years: {playwright_years}" if playwright_years else ""}

Program title: {program_title}
Program description: {program_description or "(no description)"}

Assess whether this program is:
1. A documentary, portrait, interview, or discussion specifically ABOUT this playwright
2. A program discussing their life, work, or legacy
3. An adaptation or reading of their work (NOT a stage performance - those are tracked separately)

The program should be ABOUT the person, not just mentioning them or having a similar name.

Respond with JSON only:
{{"is_about_playwright": true/false, "confidence": 0.0-1.0, "reason": "brief explanation"}}"""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 200,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        text = result["content"][0]["text"]

        # Parse JSON from response
        json_match = re.search(r'\{[^}]+\}', text)
        if json_match:
            assessment = json.loads(json_match.group())
            cache[cache_key] = assessment
            return assessment
    except Exception as e:
        print(f"  AI assessment error: {e}")

    return {"is_about_playwright": False, "confidence": 0, "reason": "AI assessment failed"}

def main():
    parser = argparse.ArgumentParser(description='Enrich NRK about programs with AI filtering')
    parser.add_argument('--dry-run', action='store_true', help='Show candidates without AI filtering or DB changes')
    parser.add_argument('--playwright', type=str, help='Process only this playwright (by name)')
    parser.add_argument('--limit', type=int, default=0, help='Limit number of playwrights to process')
    args = parser.parse_args()

    dry_run = args.dry_run

    if not dry_run and not ANTHROPIC_API_KEY:
        print("ERROR: Set ANTHROPIC_API_KEY environment variable")
        print("Example: export ANTHROPIC_API_KEY=sk-ant-...")
        print("\nOr use --dry-run to see candidates without AI filtering")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get playwrights with plays in DB
    if args.playwright:
        cursor.execute("""
            SELECT DISTINCT p.id, p.name, p.birth_year, p.death_year
            FROM persons p
            JOIN plays pl ON p.id = pl.playwright_id
            WHERE p.name LIKE ?
            ORDER BY p.name
        """, (f"%{args.playwright}%",))
    else:
        cursor.execute("""
            SELECT DISTINCT p.id, p.name, p.birth_year, p.death_year
            FROM persons p
            JOIN plays pl ON p.id = pl.playwright_id
            ORDER BY p.name
        """)
    playwrights = cursor.fetchall()

    if args.limit > 0:
        playwrights = playwrights[:args.limit]

    print(f"Processing {len(playwrights)} playwrights...")
    if dry_run:
        print("DRY RUN MODE - no AI filtering, no database changes\n")

    # Get existing episodes to exclude
    cursor.execute("SELECT prf_id FROM episodes")
    existing_episodes = {row['prf_id'] for row in cursor.fetchall()}

    # Get already processed programs
    cursor.execute("SELECT id FROM nrk_about_programs")
    existing_about = {row['id'] for row in cursor.fetchall()}

    cache = load_cache()
    total_added = 0
    total_rejected = 0

    for playwright in playwrights:
        person_id = playwright['id']
        name = playwright['name']
        years = ""
        if playwright['birth_year']:
            years = f"{playwright['birth_year']}-{playwright['death_year'] or ''}"

        print(f"\n{'='*50}")
        print(f"{name} {f'({years})' if years else ''}")
        print('='*50)

        # Search NRK
        search_result = search_nrk(name)
        if not search_result:
            continue

        hits = search_result.get('hits', [])
        print(f"Found {len(hits)} search results")

        candidates = []

        for hit_wrapper in hits:
            hit = hit_wrapper.get('hit', {})
            hit_type = hit_wrapper.get('type', '')
            program_id = hit.get('id')

            if not program_id:
                continue
            if program_id in existing_episodes or program_id in existing_about:
                continue

            title = hit.get('title', '')
            description = hit.get('description', '')

            # Get more details
            if hit_type == 'serie':
                details = get_series_details(program_id)
                if details:
                    standard = details.get('standard', {})
                    titles = standard.get('titles', {})
                    title = titles.get('title', title)
                    description = titles.get('subtitle', description)

                    # Get episode info
                    embedded = details.get('_embedded', {})
                    seasons = embedded.get('seasons', [])
                    episode_count = 0
                    total_duration = 0
                    for season in seasons:
                        eps = season.get('_embedded', {}).get('episodes', [])
                        episode_count += len(eps)
                        for ep in eps:
                            total_duration += parse_duration(ep.get('duration')) or 0

                    # Also check instalments
                    instalments = embedded.get('instalments', {}).get('_embedded', {}).get('instalments', [])
                    if instalments and episode_count == 0:
                        episode_count = len(instalments)
                        for ep in instalments:
                            total_duration += parse_duration(ep.get('duration')) or 0

                    if total_duration < 600:  # < 10 min total
                        continue

                    nrk_url = f"https://tv.nrk.no/serie/{program_id}"
                    image_url = None
                    images = standard.get('image', [])
                    if images:
                        image_url = images[1].get('url') if len(images) > 1 else images[0].get('url')

                    candidates.append({
                        'id': program_id,
                        'title': title,
                        'description': description,
                        'duration': total_duration,
                        'episode_count': episode_count,
                        'nrk_url': nrk_url,
                        'image_url': image_url,
                        'program_type': 'serie'
                    })
            else:
                details = get_program_details(program_id)
                if details:
                    title = details.get('title', title)
                    description = details.get('shortDescription', '') or details.get('longDescription', '')
                    duration = parse_duration(details.get('duration'))

                    if not duration or duration < 600:  # < 10 min
                        continue

                    # Check availability
                    availability = details.get('availability', {})
                    if availability.get('status') not in ['available', 'onDemand', None, '']:
                        continue

                    nrk_url = f"https://tv.nrk.no/program/{program_id}"
                    image_url = None
                    images = details.get('image', {}).get('webImages', [])
                    if images:
                        image_url = images[0].get('uri', images[0].get('url'))

                    candidates.append({
                        'id': program_id,
                        'title': title,
                        'description': description,
                        'duration': duration,
                        'episode_count': None,
                        'nrk_url': nrk_url,
                        'image_url': image_url,
                        'program_type': hit_type or 'program'
                    })

            time.sleep(0.2)

        # AI review each candidate
        for candidate in candidates:
            dur_min = candidate['duration'] // 60 if candidate['duration'] else 0
            ep_info = f", {candidate['episode_count']} ep" if candidate['episode_count'] else ""

            if dry_run:
                # Dry run - just show candidate info
                print(f"\n  CANDIDATE: {candidate['title']} ({dur_min} min{ep_info})")
                if candidate['description']:
                    print(f"    Desc: {candidate['description'][:100]}...")
                print(f"    URL: {candidate['nrk_url']}")
                continue

            print(f"\n  Checking: {candidate['title']} ({dur_min} min{ep_info})")

            assessment = ai_assess_relevance(
                name, years,
                candidate['title'],
                candidate['description'],
                cache
            )

            is_relevant = assessment.get('is_about_playwright', False)
            confidence = assessment.get('confidence', 0)
            reason = assessment.get('reason', '')

            if is_relevant and confidence >= 0.7:
                print(f"    ✓ ACCEPTED (confidence: {confidence:.0%}): {reason}")

                # Insert into database
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO nrk_about_programs
                        (id, person_id, title, description, duration_seconds, nrk_url,
                         interest_score, image_url, program_type, episode_count)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        candidate['id'], person_id, candidate['title'],
                        candidate['description'], candidate['duration'],
                        candidate['nrk_url'], int(confidence * 100),
                        candidate['image_url'], candidate['program_type'],
                        candidate['episode_count']
                    ))
                    conn.commit()
                    existing_about.add(candidate['id'])
                    total_added += 1
                except Exception as e:
                    print(f"    DB error: {e}")
            else:
                print(f"    ✗ REJECTED (confidence: {confidence:.0%}): {reason}")
                total_rejected += 1

            time.sleep(0.3)  # Rate limit AI calls

        # Save cache periodically
        save_cache(cache)
        time.sleep(0.5)

    # Summary
    cursor.execute("SELECT COUNT(*) FROM nrk_about_programs")
    total = cursor.fetchone()[0]

    print(f"\n{'='*50}")
    print("SUMMARY")
    print('='*50)
    print(f"Added: {total_added}")
    print(f"Rejected: {total_rejected}")
    print(f"Total in database: {total}")

    # Show recent additions
    cursor.execute("""
        SELECT n.title, p.name, n.duration_seconds/60 as mins
        FROM nrk_about_programs n
        JOIN persons p ON n.person_id = p.id
        ORDER BY n.id DESC
        LIMIT 10
    """)
    print("\nRecent additions:")
    for row in cursor.fetchall():
        print(f"  {row[1]}: {row[0]} ({row[2]} min)")

    save_cache(cache)
    conn.close()

if __name__ == '__main__':
    main()
