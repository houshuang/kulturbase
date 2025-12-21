#!/usr/bin/env python3
"""
Classify plays into work types using Gemini Flash.

Categories:
- teaterstykke: Traditional play, performed elsewhere (theater history exists)
- nrk_teaterstykke: Written specifically for NRK TV/radio, never staged elsewhere
- dramaserie: Multi-episode narrative series, not a theatrical play

Signals for classification:
- Episode count (dramaserie typically 10+ episodes)
- Playwright is known theater playwright = likely teaterstykke
- Sceneweb URL present = definitely teaterstykke
- Title patterns (series names = dramaserie)
- Synopsis content
"""

import json
import time
import os
import re
import yaml
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

import google.generativeai as genai

# Load environment
load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "output"
CACHE_FILE = OUTPUT_DIR / "play_classification_cache.json"

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')

# Rate limiting
MAX_REQUESTS_PER_MINUTE = 30
REQUEST_INTERVAL = 60 / MAX_REQUESTS_PER_MINUTE


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
    OUTPUT_DIR.mkdir(exist_ok=True)
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def load_all_plays():
    """Load all plays with related data."""
    plays = []
    plays_dir = DATA_DIR / "plays"

    # Load persons for playwright lookup
    persons = {}
    for f in (DATA_DIR / "persons").glob("*.yaml"):
        p = load_yaml(f)
        persons[p['id']] = p

    # Load episodes to count per play
    episode_counts = {}
    for f in (DATA_DIR / "episodes").glob("*.yaml"):
        ep = load_yaml(f)
        play_id = ep.get('play_id')
        if play_id:
            episode_counts[play_id] = episode_counts.get(play_id, 0) + 1

    # Load plays
    for f in sorted(plays_dir.glob("*.yaml")):
        play = load_yaml(f)
        play['_file_path'] = str(f)
        play['_episode_count'] = episode_counts.get(play['id'], 0)

        # Get playwright name
        playwright_id = play.get('playwright_id')
        if playwright_id and playwright_id in persons:
            play['_playwright_name'] = persons[playwright_id].get('name', '')
        else:
            play['_playwright_name'] = ''

        plays.append(play)

    return plays


def create_classification_prompt(play):
    """Create the prompt for Gemini classification."""
    title = play.get('title', '')
    original_title = play.get('original_title', '')
    synopsis = play.get('synopsis', '')
    playwright = play.get('_playwright_name', '')
    episode_count = play.get('_episode_count', 0)
    has_sceneweb = bool(play.get('sceneweb_url'))
    year_written = play.get('year_written', '')

    prompt = f"""Classify this Norwegian TV/radio production into one of three categories.

TITLE: {title}
ORIGINAL TITLE: {original_title if original_title and original_title != title else '(same)'}
PLAYWRIGHT/AUTHOR: {playwright if playwright else '(unknown)'}
YEAR WRITTEN: {year_written if year_written else '(unknown)'}
SYNOPSIS: {synopsis if synopsis else '(none available)'}
EPISODE COUNT: {episode_count}
HAS SCENEWEB URL: {has_sceneweb} (Sceneweb = Norwegian theater database)

CLASSIFICATION OPTIONS:
1. **teaterstykke** - A real theatrical play that has been performed on stage elsewhere.
   Indicators: Known playwright (Ibsen, Shakespeare, Holberg, Chekhov, etc.),
   has Sceneweb URL, classic or contemporary theater work, typically 1-3 episodes.

2. **nrk_teaterstykke** - A dramatic work written SPECIFICALLY for NRK TV/radio.
   Never performed on stage, but still has theatrical quality. Written by TV/radio writers.
   Typically 1-5 episodes, may have unknown or Norwegian TV writers as authors.

3. **dramaserie** - A TV/radio drama SERIES, not a play.
   Indicators: High episode count (10+), episodic structure, ongoing storylines,
   names like "adventures of...", detective series, soap opera style, etc.

IMPORTANT: If it has a Sceneweb URL, it's almost certainly "teaterstykke".
If playwright is Ibsen, Shakespeare, Holberg, Strindberg, Chekhov, Molière, Bjørnson,
Brecht, Beckett, or other famous playwright - it's "teaterstykke".

Return ONLY valid JSON (no markdown):
{{
  "work_type": "teaterstykke|nrk_teaterstykke|dramaserie",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation"
}}"""

    return prompt


FAMOUS_PLAYWRIGHTS = {
    'Henrik Ibsen', 'William Shakespeare', 'Ludvig Holberg', 'August Strindberg',
    'Anton Tsjekhov', 'Anton Chekhov', 'Molière', 'Bjørnstjerne Bjørnson',
    'Bertolt Brecht', 'Samuel Beckett', 'Eugene O\'Neill', 'Tennessee Williams',
    'Arthur Miller', 'Oscar Wilde', 'George Bernard Shaw', 'Federico García Lorca',
    'Jean Anouilh', 'Jean-Paul Sartre', 'Albert Camus', 'Eugène Ionesco',
    'Harold Pinter', 'Tom Stoppard', 'Edward Albee', 'David Mamet',
    'Nordahl Grieg', 'Gunnar Heiberg', 'Hans E. Kinck', 'Helge Krog',
    'Oskar Braaten', 'Nils Kjær', 'Johan Borgen', 'Tarjei Vesaas',
    'Jens Bjørneboe', 'Georg Brandes', 'Carlo Goldoni', 'Pierre de Marivaux',
    'Jean Racine', 'Pierre Corneille', 'Sophokles', 'Euripides', 'Aristofanes',
    'Friedrich Schiller', 'Johann Wolfgang von Goethe', 'Heinrich von Kleist',
    'Hugo von Hofmannsthal', 'Frank Wedekind', 'Gerhart Hauptmann',
    'Maxim Gorkij', 'Nikolai Gogol', 'Alexander Ostrovsky', 'Ivan Turgenjev',
    'Agatha Christie', 'Arne Garborg', 'Alexander Kielland', 'Jonas Lie',
    'Amalie Skram', 'Knut Hamsun', 'Sigurd Hoel', 'Aksel Sandemose',
}


def classify_play(play, cache):
    """Classify a single play using Gemini."""
    play_id = str(play['id'])

    # Check cache
    if play_id in cache:
        return cache[play_id]

    # Auto-classify if has Sceneweb URL (definitely a theater play)
    if play.get('sceneweb_url'):
        return {
            'work_type': 'teaterstykke',
            'confidence': 1.0,
            'reasoning': 'Has Sceneweb URL (Norwegian theater database)',
            'auto_classified': True
        }

    # Auto-classify high episode counts as dramaserie
    if play.get('_episode_count', 0) >= 15:
        return {
            'work_type': 'dramaserie',
            'confidence': 0.9,
            'reasoning': f"High episode count ({play.get('_episode_count')} episodes)",
            'auto_classified': True
        }

    # Auto-classify plays by famous playwrights
    playwright = play.get('_playwright_name', '')
    if playwright in FAMOUS_PLAYWRIGHTS:
        return {
            'work_type': 'teaterstykke',
            'confidence': 0.95,
            'reasoning': f'Famous playwright: {playwright}',
            'auto_classified': True
        }

    prompt = create_classification_prompt(play)

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Remove markdown code blocks if present
        if text.startswith('```'):
            text = re.sub(r'^```json?\s*', '', text)
            text = re.sub(r'\s*```$', '', text)

        result = json.loads(text)
        result['auto_classified'] = False
        return result

    except json.JSONDecodeError as e:
        print(f"    JSON parse error for {play_id}: {e}")
        return {
            'work_type': 'nrk_teaterstykke',  # Default
            'confidence': 0.0,
            'error': f'JSON parse error: {str(e)}',
            'raw_response': text[:500] if 'text' in dir() else None,
        }
    except Exception as e:
        print(f"    Error classifying {play_id}: {e}")
        return {
            'work_type': 'nrk_teaterstykke',  # Default
            'confidence': 0.0,
            'error': str(e),
        }


def main():
    print("=" * 60)
    print("Classifying Plays with Gemini Flash")
    print("=" * 60)

    # Load plays
    plays = load_all_plays()
    print(f"Found {len(plays)} plays to classify")

    # Load cache
    cache = load_cache()
    cached_count = sum(1 for p in plays if str(p['id']) in cache)
    print(f"Already cached: {cached_count}")

    # Count auto-classifiable
    with_sceneweb = sum(1 for p in plays if p.get('sceneweb_url'))
    high_episode = sum(1 for p in plays if p.get('_episode_count', 0) >= 15)
    print(f"Auto-classifiable: {with_sceneweb} with Sceneweb, {high_episode} high-episode series")

    # Classify plays
    results = {
        'teaterstykke': [],
        'nrk_teaterstykke': [],
        'dramaserie': [],
        'errors': []
    }

    print("\nClassifying plays...")
    for i, play in enumerate(plays):
        play_id = str(play['id'])

        if i % 50 == 0:
            print(f"  Progress: {i}/{len(plays)}")
            save_cache(cache)

        # Classify (uses cache, auto-classify, or Gemini)
        if play_id not in cache:
            # Rate limit only for Gemini calls
            if not play.get('sceneweb_url') and play.get('_episode_count', 0) < 15:
                time.sleep(REQUEST_INTERVAL)

            classification = classify_play(play, cache)
            cache[play_id] = classification
        else:
            classification = cache[play_id]

        # Record result
        work_type = classification.get('work_type', 'nrk_teaterstykke')
        if classification.get('error'):
            results['errors'].append({
                'id': play['id'],
                'title': play['title'],
                'classification': classification
            })
        else:
            results[work_type].append({
                'id': play['id'],
                'title': play['title'],
                'playwright': play.get('_playwright_name', ''),
                'episode_count': play.get('_episode_count', 0),
                'classification': classification
            })

    # Final cache save
    save_cache(cache)

    # Summary
    print("\n" + "=" * 60)
    print("CLASSIFICATION COMPLETE")
    print("=" * 60)
    print(f"Teaterstykke (real plays): {len(results['teaterstykke'])}")
    print(f"NRK Teaterstykke (written for NRK): {len(results['nrk_teaterstykke'])}")
    print(f"Dramaserie (series): {len(results['dramaserie'])}")
    print(f"Errors: {len(results['errors'])}")

    # Save full results
    OUTPUT_DIR.mkdir(exist_ok=True)
    output_file = OUTPUT_DIR / "play_classifications.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'classified_at': datetime.now().isoformat(),
            'statistics': {
                'teaterstykke': len(results['teaterstykke']),
                'nrk_teaterstykke': len(results['nrk_teaterstykke']),
                'dramaserie': len(results['dramaserie']),
                'errors': len(results['errors']),
            },
            **results
        }, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to: {output_file}")

    # Show samples
    print("\n--- Sample Dramaserier (high episode count) ---")
    for item in sorted(results['dramaserie'], key=lambda x: -x['episode_count'])[:10]:
        print(f"  {item['title']} ({item['episode_count']} episodes)")

    print("\n--- Sample NRK Teaterstykke ---")
    for item in results['nrk_teaterstykke'][:10]:
        print(f"  {item['title']} by {item['playwright'] or '(unknown)'}")

    return results


def apply_classifications():
    """Apply classifications to YAML files."""
    print("\n" + "=" * 60)
    print("Applying classifications to YAML files")
    print("=" * 60)

    cache = load_cache()
    if not cache:
        print("ERROR: No classifications found. Run classification first.")
        return

    plays_dir = DATA_DIR / "plays"
    updated = 0

    for f in sorted(plays_dir.glob("*.yaml")):
        play = load_yaml(f)
        play_id = str(play['id'])

        if play_id in cache:
            classification = cache[play_id]
            work_type = classification.get('work_type', 'nrk_teaterstykke')

            # Determine category based on work_type
            if work_type == 'dramaserie':
                category = 'dramaserie'
            else:
                category = 'teater'

            # Update play data
            play['work_type'] = work_type
            play['category'] = category

            save_yaml(f, play)
            updated += 1

    print(f"Updated {updated} play files with work_type and category")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--apply':
        apply_classifications()
    else:
        main()
        print("\nTo apply classifications to YAML files, run:")
        print("  python3 scripts/classify_plays.py --apply")
