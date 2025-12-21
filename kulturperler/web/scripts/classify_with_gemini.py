#!/usr/bin/env python3
"""
Phase 3: Classify episodes using Gemini Flash.

Uses Gemini to classify each episode as ballet/opera/symphony/etc and extract metadata.
Outputs: output/classical_classified.json
"""

import json
import time
import os
import re
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

import google.generativeai as genai

# Load environment
load_dotenv()

OUTPUT_DIR = Path(__file__).parent.parent / "output"
INPUT_FILE = OUTPUT_DIR / "classical_episodes_raw.json"
OUTPUT_FILE = OUTPUT_DIR / "classical_classified.json"
CACHE_FILE = OUTPUT_DIR / "gemini_cache.json"

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')

# Rate limiting
MAX_REQUESTS_PER_MINUTE = 30
REQUEST_INTERVAL = 60 / MAX_REQUESTS_PER_MINUTE


def load_cache():
    """Load cached Gemini responses."""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE) as f:
                return json.load(f)
        except:
            pass
    return {}


def save_cache(cache):
    """Save Gemini responses to cache."""
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def create_classification_prompt(episode):
    """Create the prompt for Gemini classification."""
    title = episode.get('title', '')
    subtitle = episode.get('subtitle', '')
    description = episode.get('description', '') or subtitle
    series_title = episode.get('series_title', '')
    contributors = episode.get('contributors', [])

    # Format contributors
    contrib_str = ""
    if contributors:
        contrib_str = "\n".join([f"  - {c.get('name', '?')}: {c.get('role', '?')}" for c in contributors[:15]])

    prompt = f"""Analyze this NRK program metadata and classify it as classical music content.

SERIES: {series_title}
TITLE: {title}
SUBTITLE: {subtitle}
DESCRIPTION: {description}
CONTRIBUTORS:
{contrib_str if contrib_str else "  (none listed)"}

Answer these questions about the program:

1. Is this an actual performance of classical music (ballet/opera/symphony/orchestral concert), or is it:
   - A documentary/discussion ABOUT classical music
   - An introduction to a performance
   - Not classical music at all (sports, news, pop/rock, children's show, etc.)

2. If it IS classical music content:
   a) What is the specific work being performed? (e.g., "Swan Lake", "Carmen", "Symphony No. 5")
   b) Who is the composer? (e.g., Tchaikovsky, Verdi, Beethoven)
   c) What genre? (ballet, opera, operetta, symphony, concerto, orchestral, chamber, choral, other_classical)

3. For operas/operettas:
   a) What language is it sung in? (Norwegian, Italian, German, French, Russian, English, other)
   b) Is this a Norwegian translation of a foreign opera? (historically significant if yes)

4. Is this a complete performance, or part of a multi-part broadcast?
   Look for indicators like "1:2", "del 1 av 2", "(1/2)", "del 1", etc.

5. If based on a literary work (play, novel), what is it? (e.g., "Based on Ibsen's Peer Gynt")

Return ONLY valid JSON (no markdown code blocks, just raw JSON):
{{
  "is_classical": true/false,
  "content_type": "performance|documentary|introduction|discussion|not_classical",
  "genre": "ballet|opera|operetta|symphony|concerto|orchestral|chamber|choral|other_classical|not_classical",
  "work_title": "string or null",
  "work_title_original": "original language title or null",
  "composer": "string or null",
  "performance_language": "norwegian|italian|german|french|russian|english|instrumental|mixed|unknown",
  "is_norwegian_translation": true/false,
  "is_multipart": true/false,
  "part_indicator": "string like '1/2' or 'del 1' or null",
  "based_on_literary_work": "string or null",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation of classification"
}}"""

    return prompt


def classify_episode(episode, cache):
    """Classify a single episode using Gemini."""
    prf_id = episode.get('prf_id', '')

    # Check cache
    if prf_id in cache:
        return cache[prf_id]

    prompt = create_classification_prompt(episode)

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Try to parse JSON (handle potential markdown wrapping)
        if text.startswith('```'):
            # Remove markdown code blocks
            text = re.sub(r'^```json?\s*', '', text)
            text = re.sub(r'\s*```$', '', text)

        result = json.loads(text)
        result['prf_id'] = prf_id
        result['classification_timestamp'] = datetime.now().isoformat()

        return result

    except json.JSONDecodeError as e:
        print(f"    JSON parse error for {prf_id}: {e}")
        return {
            'prf_id': prf_id,
            'is_classical': None,
            'error': f'JSON parse error: {str(e)}',
            'raw_response': text[:500] if 'text' in dir() else None,
        }
    except Exception as e:
        print(f"    Error classifying {prf_id}: {e}")
        return {
            'prf_id': prf_id,
            'is_classical': None,
            'error': str(e),
        }


def main():
    print("=" * 60)
    print("Phase 3: Classifying Episodes with Gemini")
    print("=" * 60)

    # Load episodes
    if not INPUT_FILE.exists():
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        print("Please run extract_classical_episodes.py first.")
        return

    with open(INPUT_FILE) as f:
        data = json.load(f)

    episodes = data.get('episodes', [])
    print(f"Found {len(episodes)} episodes to classify")

    # Load cache
    cache = load_cache()
    cached_count = sum(1 for ep in episodes if ep.get('prf_id') in cache)
    print(f"Already cached: {cached_count}")

    # Classify episodes
    results = []
    classified_count = 0
    error_count = 0

    print("\nClassifying episodes...")
    for i, episode in enumerate(episodes):
        prf_id = episode.get('prf_id', '')

        if i % 25 == 0:
            print(f"  Progress: {i}/{len(episodes)} ({len(results)} classified, {error_count} errors)")

        # Use cache if available
        if prf_id in cache:
            results.append({**episode, 'classification': cache[prf_id]})
            classified_count += 1
            continue

        # Rate limiting
        time.sleep(REQUEST_INTERVAL)

        # Classify
        classification = classify_episode(episode, cache)

        if classification.get('error'):
            error_count += 1
        else:
            # Cache successful result
            cache[prf_id] = classification
            if i % 50 == 0:
                save_cache(cache)

        classified_count += 1
        results.append({**episode, 'classification': classification})

    # Final cache save
    save_cache(cache)

    # Separate by classification
    classical_performances = []
    documentaries = []
    introductions = []
    not_classical = []
    errors = []

    for item in results:
        cls = item.get('classification', {})

        if cls.get('error'):
            errors.append(item)
        elif not cls.get('is_classical'):
            not_classical.append(item)
        elif cls.get('content_type') == 'performance':
            classical_performances.append(item)
        elif cls.get('content_type') == 'documentary':
            documentaries.append(item)
        elif cls.get('content_type') == 'introduction':
            introductions.append(item)
        else:
            # Default to not classical if uncertain
            not_classical.append(item)

    # Count by genre
    genre_counts = {}
    for item in classical_performances:
        genre = item.get('classification', {}).get('genre', 'unknown')
        genre_counts[genre] = genre_counts.get(genre, 0) + 1

    # Count Norwegian translations
    norwegian_translations = [
        item for item in classical_performances
        if item.get('classification', {}).get('is_norwegian_translation')
    ]

    # Output
    output_data = {
        'classified_at': datetime.now().isoformat(),
        'statistics': {
            'total_input': len(episodes),
            'total_classified': classified_count,
            'classical_performances': len(classical_performances),
            'documentaries': len(documentaries),
            'introductions': len(introductions),
            'not_classical': len(not_classical),
            'errors': len(errors),
            'norwegian_translations': len(norwegian_translations),
            'by_genre': genre_counts,
        },
        'classical_performances': classical_performances,
        'documentaries': documentaries,
        'introductions': introductions,
        'not_classical': not_classical,
        'errors': errors,
    }

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("CLASSIFICATION COMPLETE")
    print("=" * 60)
    print(f"Total classified: {classified_count}")
    print(f"Classical performances: {len(classical_performances)}")
    print(f"Documentaries/discussions: {len(documentaries)}")
    print(f"Introductions: {len(introductions)}")
    print(f"Not classical music: {len(not_classical)}")
    print(f"Errors: {len(errors)}")
    print(f"\nNorwegian translations of foreign works: {len(norwegian_translations)}")
    print(f"\nBy genre:")
    for genre, count in sorted(genre_counts.items(), key=lambda x: -x[1]):
        print(f"  {genre}: {count}")
    print(f"\nOutput written to: {OUTPUT_FILE}")
    print(f"Cache saved to: {CACHE_FILE}")

    # Show some Norwegian translations
    if norwegian_translations:
        print("\n--- Sample Norwegian Translations ---")
        for item in norwegian_translations[:5]:
            cls = item.get('classification', {})
            print(f"  {item.get('title')}")
            print(f"    Work: {cls.get('work_title')} by {cls.get('composer')}")
            print(f"    Language: {cls.get('performance_language')}")


if __name__ == "__main__":
    main()
