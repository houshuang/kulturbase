#!/usr/bin/env python3
"""
Search YouTube, Vimeo, Archive.org for Norwegian classical performances.

Finds complete operas, ballets, symphonies, and theatre performances.
Outputs: Multiple JSON files in output/
"""

import json
import time
import re
import os
from pathlib import Path
from datetime import datetime
from urllib.parse import quote_plus
from dotenv import load_dotenv

import requests
import google.generativeai as genai

load_dotenv()

OUTPUT_DIR = Path(__file__).parent.parent / "output"
DATA_DIR = Path(__file__).parent.parent / "data"

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')

# Search queries organized by category
SEARCH_QUERIES = {
    'opera': [
        'Den Norske Opera full opera',
        'norsk opera komplett',
        'Norwegian opera full performance',
        'Bergen Nasjonale Opera full',
        'opera norway full HD',
        'Carmen Den Norske Opera',
        'La Traviata Oslo Opera',
        'Tosca Norwegian Opera',
        'Madama Butterfly Norway',
        'Don Giovanni Oslo',
    ],
    'ballet': [
        'Nasjonalballetten full ballet',
        'Norwegian National Ballet full',
        'Den Norske Ballett full',
        'Carte Blanche dance full',
        'Svanesjøen Nasjonalballetten',
        'Swan Lake Norwegian Ballet',
        'Nøtteknekkeren Nasjonalballetten',
        'Nutcracker Norwegian Ballet',
        'Peer Gynt ballet full',
        'Ibsen ballet full',
    ],
    'symphony': [
        'Oslo Filharmonien full concert',
        'Oslo Philharmonic full symphony',
        'Bergen Filharmoniske full',
        'Bergen Philharmonic Orchestra full',
        'Trondheim Symfoniorkester full',
        'KORK full concert',
        'Stavanger Symfoniorkester full',
        'Arctic Philharmonic full',
        'Grieg piano concerto full Norway',
        'Grieg Peer Gynt suite full orchestra',
        'Svendsen symphony full',
        'Nordheim orchestral full',
    ],
    'theatre': [
        'Nationaltheatret full play',
        'Det Norske Teatret full',
        'Den Nationale Scene full',
        'Ibsen full play Norwegian',
        'Peer Gynt theatre full',
        'Et dukkehjem full play',
        'Hedda Gabler full Norwegian',
        'Vildanden full play',
        'Gengangere Ibsen full',
        'Brand Ibsen full',
        'norsk teater full forestilling',
        'Norwegian theatre full performance',
    ],
    'composers': [
        'Edvard Grieg full concert',
        'Johan Svendsen symphony full',
        'Arne Nordheim full',
        'Harald Sæverud full',
        'Geirr Tveitt full',
        'Klaus Egge full',
        'Fartein Valen full',
    ],
}

# Archive.org specific searches
ARCHIVE_SEARCHES = [
    'norwegian opera',
    'norwegian ballet',
    'norwegian theatre',
    'oslo philharmonic',
    'bergen philharmonic',
    'ibsen theatre',
    'grieg concert',
    'nasjonalballetten',
    'nationaltheatret',
]


def search_youtube_via_web(query, max_results=20):
    """Search YouTube via web search and extract video info."""
    results = []

    # Use DuckDuckGo to search YouTube
    search_url = f"https://html.duckduckgo.com/html/?q=site:youtube.com+{quote_plus(query)}"

    try:
        resp = requests.get(search_url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }, timeout=15)

        if resp.ok:
            # Extract YouTube URLs from results
            youtube_urls = re.findall(r'https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})', resp.text)

            for video_id in youtube_urls[:max_results]:
                results.append({
                    'platform': 'youtube',
                    'video_id': video_id,
                    'url': f'https://www.youtube.com/watch?v={video_id}',
                    'query': query,
                })
    except Exception as e:
        print(f"    Error searching YouTube: {e}")

    return results


def search_vimeo_via_web(query, max_results=10):
    """Search Vimeo via web search."""
    results = []

    search_url = f"https://html.duckduckgo.com/html/?q=site:vimeo.com+{quote_plus(query)}"

    try:
        resp = requests.get(search_url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }, timeout=15)

        if resp.ok:
            # Extract Vimeo URLs
            vimeo_urls = re.findall(r'https?://(?:www\.)?vimeo\.com/(\d+)', resp.text)

            for video_id in vimeo_urls[:max_results]:
                results.append({
                    'platform': 'vimeo',
                    'video_id': video_id,
                    'url': f'https://vimeo.com/{video_id}',
                    'query': query,
                })
    except Exception as e:
        print(f"    Error searching Vimeo: {e}")

    return results


def search_archive_org(query, max_results=20):
    """Search Archive.org for video content."""
    results = []

    # Archive.org API
    api_url = f"https://archive.org/advancedsearch.php"
    params = {
        'q': f'{query} AND mediatype:movies',
        'fl[]': ['identifier', 'title', 'description', 'creator', 'date', 'runtime'],
        'rows': max_results,
        'output': 'json',
    }

    try:
        resp = requests.get(api_url, params=params, timeout=15)
        if resp.ok:
            data = resp.json()
            docs = data.get('response', {}).get('docs', [])

            for doc in docs:
                results.append({
                    'platform': 'archive.org',
                    'identifier': doc.get('identifier'),
                    'title': doc.get('title'),
                    'description': doc.get('description', ''),
                    'creator': doc.get('creator'),
                    'date': doc.get('date'),
                    'runtime': doc.get('runtime'),
                    'url': f"https://archive.org/details/{doc.get('identifier')}",
                    'query': query,
                })
    except Exception as e:
        print(f"    Error searching Archive.org: {e}")

    return results


def get_youtube_metadata(video_id):
    """Get metadata for a YouTube video using oembed."""
    try:
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        resp = requests.get(url, timeout=10)
        if resp.ok:
            data = resp.json()
            return {
                'title': data.get('title', ''),
                'author_name': data.get('author_name', ''),
                'author_url': data.get('author_url', ''),
                'thumbnail_url': data.get('thumbnail_url', ''),
            }
    except:
        pass
    return None


def get_vimeo_metadata(video_id):
    """Get metadata for a Vimeo video using oembed."""
    try:
        url = f"https://vimeo.com/api/oembed.json?url=https://vimeo.com/{video_id}"
        resp = requests.get(url, timeout=10)
        if resp.ok:
            data = resp.json()
            return {
                'title': data.get('title', ''),
                'author_name': data.get('author_name', ''),
                'author_url': data.get('author_url', ''),
                'duration': data.get('duration', 0),
                'thumbnail_url': data.get('thumbnail_url', ''),
                'description': data.get('description', ''),
            }
    except:
        pass
    return None


def classify_with_gemini(title, description, platform, query_category):
    """Use Gemini to classify if this is a complete performance."""
    prompt = f"""Analyze this video from {platform} and determine if it's a complete performance.

Title: {title}
Description: {description[:500] if description else 'No description'}
Search category: {query_category}

Questions:
1. Is this likely a COMPLETE performance (full opera, full ballet, full symphony, full play)?
   - Look for indicators like "full", "complete", "komplett", duration mentions
   - Trailers, excerpts, highlights are NOT complete
2. What type of content is it? (opera, ballet, symphony, orchestral concert, theatre, documentary, other)
3. Is it Norwegian or by a Norwegian company?
4. What is the work being performed (if identifiable)?
5. Who is performing (company/orchestra)?

Return ONLY valid JSON:
{{
  "is_complete_performance": true/false,
  "content_type": "opera|ballet|symphony|orchestral|theatre|documentary|other",
  "is_norwegian": true/false,
  "work_title": "string or null",
  "composer_playwright": "string or null",
  "performing_company": "string or null",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation"
}}"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Clean up JSON
        if text.startswith('```'):
            text = re.sub(r'^```json?\s*', '', text)
            text = re.sub(r'\s*```$', '', text)

        return json.loads(text)
    except Exception as e:
        return {'error': str(e), 'is_complete_performance': None}


def load_existing_plays():
    """Load existing play titles from database for matching."""
    plays = set()
    plays_dir = DATA_DIR / "plays"

    if plays_dir.exists():
        for f in plays_dir.glob("*.yaml"):
            try:
                import yaml
                with open(f) as fp:
                    data = yaml.safe_load(fp)
                    if data and data.get('title'):
                        plays.add(data['title'].lower())
            except:
                pass

    return plays


def main():
    print("=" * 60)
    print("External Platform Search for Norwegian Classical Content")
    print("=" * 60)

    OUTPUT_DIR.mkdir(exist_ok=True)

    all_youtube_results = []
    all_vimeo_results = []
    all_archive_results = []

    existing_plays = load_existing_plays()
    print(f"Loaded {len(existing_plays)} existing plays for matching")

    # Search YouTube
    print("\n[1/3] Searching YouTube...")
    youtube_seen = set()
    for category, queries in SEARCH_QUERIES.items():
        print(f"\n  Category: {category}")
        for query in queries:
            print(f"    Searching: {query}")
            results = search_youtube_via_web(query)

            for r in results:
                if r['video_id'] not in youtube_seen:
                    youtube_seen.add(r['video_id'])
                    r['category'] = category
                    all_youtube_results.append(r)

            time.sleep(1)  # Rate limiting

    print(f"\n  Total YouTube videos found: {len(all_youtube_results)}")

    # Search Vimeo
    print("\n[2/3] Searching Vimeo...")
    vimeo_seen = set()
    for category, queries in SEARCH_QUERIES.items():
        print(f"\n  Category: {category}")
        for query in queries[:3]:  # Fewer queries for Vimeo
            print(f"    Searching: {query}")
            results = search_vimeo_via_web(query)

            for r in results:
                if r['video_id'] not in vimeo_seen:
                    vimeo_seen.add(r['video_id'])
                    r['category'] = category
                    all_vimeo_results.append(r)

            time.sleep(1)

    print(f"\n  Total Vimeo videos found: {len(all_vimeo_results)}")

    # Search Archive.org
    print("\n[3/3] Searching Archive.org...")
    archive_seen = set()
    for query in ARCHIVE_SEARCHES:
        print(f"  Searching: {query}")
        results = search_archive_org(query)

        for r in results:
            if r['identifier'] not in archive_seen:
                archive_seen.add(r['identifier'])
                all_archive_results.append(r)

        time.sleep(0.5)

    print(f"\n  Total Archive.org items found: {len(all_archive_results)}")

    # Enrich with metadata and classify
    print("\n[4/5] Enriching YouTube metadata and classifying...")
    enriched_youtube = []
    for i, video in enumerate(all_youtube_results):
        if i % 10 == 0:
            print(f"  Processing {i}/{len(all_youtube_results)}...")

        metadata = get_youtube_metadata(video['video_id'])
        if metadata:
            video.update(metadata)

            # Classify with Gemini
            time.sleep(2)  # Rate limiting for Gemini
            classification = classify_with_gemini(
                video.get('title', ''),
                '',  # YouTube oembed doesn't give description
                'YouTube',
                video.get('category', '')
            )
            video['classification'] = classification

            enriched_youtube.append(video)

    print("\n[5/5] Enriching Vimeo metadata and classifying...")
    enriched_vimeo = []
    for i, video in enumerate(all_vimeo_results):
        if i % 10 == 0:
            print(f"  Processing {i}/{len(all_vimeo_results)}...")

        metadata = get_vimeo_metadata(video['video_id'])
        if metadata:
            video.update(metadata)

            # Classify with Gemini
            time.sleep(2)
            classification = classify_with_gemini(
                video.get('title', ''),
                video.get('description', ''),
                'Vimeo',
                video.get('category', '')
            )
            video['classification'] = classification

            enriched_vimeo.append(video)

    # Classify Archive.org results
    print("\n  Classifying Archive.org results...")
    for i, item in enumerate(all_archive_results):
        if i % 10 == 0:
            print(f"  Processing {i}/{len(all_archive_results)}...")

        time.sleep(2)
        classification = classify_with_gemini(
            item.get('title', ''),
            item.get('description', ''),
            'Archive.org',
            'archive'
        )
        item['classification'] = classification

    # Filter for complete performances
    complete_youtube = [v for v in enriched_youtube
                        if v.get('classification', {}).get('is_complete_performance')]
    complete_vimeo = [v for v in enriched_vimeo
                      if v.get('classification', {}).get('is_complete_performance')]
    complete_archive = [a for a in all_archive_results
                        if a.get('classification', {}).get('is_complete_performance')]

    # Find theatre performances not in database
    theatre_candidates = []
    for platform_results in [enriched_youtube, enriched_vimeo]:
        for v in platform_results:
            cls = v.get('classification', {})
            if cls.get('content_type') == 'theatre' and cls.get('is_complete_performance'):
                work_title = cls.get('work_title', '').lower()
                if work_title and work_title not in existing_plays:
                    theatre_candidates.append(v)

    # Save results
    with open(OUTPUT_DIR / 'external_youtube_finds.json', 'w', encoding='utf-8') as f:
        json.dump({
            'searched_at': datetime.now().isoformat(),
            'total_found': len(enriched_youtube),
            'complete_performances': len(complete_youtube),
            'all_results': enriched_youtube,
            'complete_only': complete_youtube,
        }, f, indent=2, ensure_ascii=False)

    with open(OUTPUT_DIR / 'external_vimeo_finds.json', 'w', encoding='utf-8') as f:
        json.dump({
            'searched_at': datetime.now().isoformat(),
            'total_found': len(enriched_vimeo),
            'complete_performances': len(complete_vimeo),
            'all_results': enriched_vimeo,
            'complete_only': complete_vimeo,
        }, f, indent=2, ensure_ascii=False)

    with open(OUTPUT_DIR / 'external_archive_finds.json', 'w', encoding='utf-8') as f:
        json.dump({
            'searched_at': datetime.now().isoformat(),
            'total_found': len(all_archive_results),
            'complete_performances': len(complete_archive),
            'all_results': all_archive_results,
            'complete_only': complete_archive,
        }, f, indent=2, ensure_ascii=False)

    with open(OUTPUT_DIR / 'external_theatre_candidates.json', 'w', encoding='utf-8') as f:
        json.dump({
            'searched_at': datetime.now().isoformat(),
            'note': 'Theatre performances NOT in existing database',
            'candidates': theatre_candidates,
        }, f, indent=2, ensure_ascii=False)

    # Generate text report
    with open(OUTPUT_DIR / 'report_external_sources.txt', 'w', encoding='utf-8') as f:
        f.write("# EXTERNAL PLATFORM SEARCH RESULTS\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("=" * 60 + "\n\n")

        f.write("## SUMMARY\n")
        f.write(f"YouTube: {len(enriched_youtube)} found, {len(complete_youtube)} complete performances\n")
        f.write(f"Vimeo: {len(enriched_vimeo)} found, {len(complete_vimeo)} complete performances\n")
        f.write(f"Archive.org: {len(all_archive_results)} found, {len(complete_archive)} complete performances\n")
        f.write(f"New theatre candidates: {len(theatre_candidates)}\n\n")

        f.write("## YOUTUBE - COMPLETE PERFORMANCES\n")
        f.write("-" * 40 + "\n")
        for v in complete_youtube:
            cls = v.get('classification', {})
            f.write(f"\n{v.get('title', 'Unknown')}\n")
            f.write(f"  URL: {v.get('url')}\n")
            f.write(f"  Channel: {v.get('author_name', '?')}\n")
            f.write(f"  Type: {cls.get('content_type', '?')}\n")
            f.write(f"  Work: {cls.get('work_title', '?')}\n")
            f.write(f"  Company: {cls.get('performing_company', '?')}\n")
            f.write(f"  Norwegian: {cls.get('is_norwegian', '?')}\n")

        f.write("\n\n## VIMEO - COMPLETE PERFORMANCES\n")
        f.write("-" * 40 + "\n")
        for v in complete_vimeo:
            cls = v.get('classification', {})
            f.write(f"\n{v.get('title', 'Unknown')}\n")
            f.write(f"  URL: {v.get('url')}\n")
            f.write(f"  Duration: {v.get('duration', 0) // 60} minutes\n")
            f.write(f"  Channel: {v.get('author_name', '?')}\n")
            f.write(f"  Type: {cls.get('content_type', '?')}\n")
            f.write(f"  Work: {cls.get('work_title', '?')}\n")

        f.write("\n\n## ARCHIVE.ORG - COMPLETE PERFORMANCES\n")
        f.write("-" * 40 + "\n")
        for item in complete_archive:
            cls = item.get('classification', {})
            f.write(f"\n{item.get('title', 'Unknown')}\n")
            f.write(f"  URL: {item.get('url')}\n")
            f.write(f"  Creator: {item.get('creator', '?')}\n")
            f.write(f"  Date: {item.get('date', '?')}\n")
            f.write(f"  Type: {cls.get('content_type', '?')}\n")

        if theatre_candidates:
            f.write("\n\n## NEW THEATRE CANDIDATES\n")
            f.write("(Not in existing database)\n")
            f.write("-" * 40 + "\n")
            for v in theatre_candidates:
                cls = v.get('classification', {})
                f.write(f"\n{v.get('title', 'Unknown')}\n")
                f.write(f"  URL: {v.get('url')}\n")
                f.write(f"  Work: {cls.get('work_title', '?')}\n")
                f.write(f"  Playwright: {cls.get('composer_playwright', '?')}\n")

    print("\n" + "=" * 60)
    print("SEARCH COMPLETE")
    print("=" * 60)
    print(f"\nYouTube: {len(enriched_youtube)} found, {len(complete_youtube)} complete")
    print(f"Vimeo: {len(enriched_vimeo)} found, {len(complete_vimeo)} complete")
    print(f"Archive.org: {len(all_archive_results)} found, {len(complete_archive)} complete")
    print(f"New theatre candidates: {len(theatre_candidates)}")
    print(f"\nResults written to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
