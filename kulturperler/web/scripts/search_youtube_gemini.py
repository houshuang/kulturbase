#!/usr/bin/env python3
"""
Search YouTube for Norwegian classical content using Gemini with Google Search grounding.
"""

import os
import json
import time
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = Path('output')
OUTPUT_DIR.mkdir(exist_ok=True)

GEMINI_API_KEY = os.getenv('GEMINI_KEY')

# Search queries for Norwegian classical content
SEARCH_QUERIES = [
    # Opera - Den Norske Opera
    "site:youtube.com Den Norske Opera full opera complete",
    "site:youtube.com Norwegian National Opera full performance",
    "site:youtube.com Oslo Opera House full opera",

    # Ballet - Nasjonalballetten
    "site:youtube.com Nasjonalballetten full ballet complete",
    "site:youtube.com Norwegian National Ballet full performance",
    "site:youtube.com Den Norske Ballett Svanesjøen",

    # Orchestras
    "site:youtube.com Oslo Filharmonien full concert complete",
    "site:youtube.com Oslo Philharmonic Orchestra full symphony",
    "site:youtube.com Bergen Filharmoniske Orkester full concert",
    "site:youtube.com Bergen Philharmonic full symphony Grieg",
    "site:youtube.com KORK Norwegian Radio Orchestra full concert",
    "site:youtube.com Trondheim Symfoniorkester full",

    # Norwegian composers
    "site:youtube.com Edvard Grieg Piano Concerto full orchestra",
    "site:youtube.com Grieg Peer Gynt suite full orchestra complete",
    "site:youtube.com Johan Svendsen symphony full",
    "site:youtube.com Harald Sæverud symphony full",
    "site:youtube.com Arne Nordheim full performance",

    # Theatre
    "site:youtube.com Nationaltheatret full play complete",
    "site:youtube.com Det Norske Teatret full forestilling",
    "site:youtube.com Henrik Ibsen full play Norwegian theatre",
    "site:youtube.com Peer Gynt full theatre performance",
    "site:youtube.com Ibsen Et dukkehjem full play",

    # Specific works
    "site:youtube.com Norwegian opera Carmen full",
    "site:youtube.com Norwegian ballet Swan Lake full Svanesjøen",
    "site:youtube.com Norwegian Nutcracker ballet full Nøtteknekkeren",
]


def search_with_gemini(query: str) -> dict:
    """Use Gemini 2.0 Flash with Google Search grounding via REST API."""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

    prompt = f"""Search YouTube for: {query}

Find YouTube videos matching this search. For each video found, extract:
1. Video title
2. YouTube URL (must be youtube.com/watch?v= format)
3. Channel name
4. Duration if visible
5. View count if visible

Return results as JSON array:
[
  {{"title": "...", "url": "https://www.youtube.com/watch?v=...", "channel": "...", "duration": "...", "views": "..."}}
]

Only include actual YouTube video results with valid URLs. If no results found, return [].
Return ONLY the JSON array, no other text."""

    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "tools": [{
            "google_search": {}
        }],
        "generationConfig": {
            "temperature": 0.1
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        # Extract text from response
        text = ""
        if 'candidates' in data and data['candidates']:
            parts = data['candidates'][0].get('content', {}).get('parts', [])
            for part in parts:
                if 'text' in part:
                    text += part['text']

        text = text.strip()

        # Try to extract JSON from response
        if text.startswith('['):
            bracket_count = 0
            end_idx = 0
            for i, c in enumerate(text):
                if c == '[':
                    bracket_count += 1
                elif c == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        end_idx = i + 1
                        break
            json_text = text[:end_idx]
            return json.loads(json_text)
        elif '```json' in text:
            json_text = text.split('```json')[1].split('```')[0].strip()
            return json.loads(json_text)
        elif '```' in text:
            json_text = text.split('```')[1].split('```')[0].strip()
            return json.loads(json_text)
        else:
            # Try to find JSON array anywhere in text
            import re
            match = re.search(r'\[.*?\]', text, re.DOTALL)
            if match:
                return json.loads(match.group())
            return []
    except Exception as e:
        print(f"    Error: {e}")
        return []


def main():
    print("=" * 60)
    print("YouTube Search via Gemini with Google Search Grounding")
    print("=" * 60)

    all_results = []
    seen_urls = set()

    for i, query in enumerate(SEARCH_QUERIES):
        print(f"\n[{i+1}/{len(SEARCH_QUERIES)}] {query}")

        results = search_with_gemini(query)

        for r in results:
            url = r.get('url', '')
            if url and url not in seen_urls and 'youtube.com' in url:
                seen_urls.add(url)
                r['search_query'] = query
                all_results.append(r)
                print(f"  + {r.get('title', 'Unknown')[:60]}")

        # Rate limiting
        time.sleep(2)

    print(f"\n\nTotal unique videos found: {len(all_results)}")

    # Save results
    output_file = OUTPUT_DIR / 'youtube_gemini_search.json'
    with open(output_file, 'w') as f:
        json.dump({
            'generated': datetime.now().isoformat(),
            'total_videos': len(all_results),
            'videos': all_results
        }, f, indent=2, ensure_ascii=False)

    print(f"Results saved to: {output_file}")

    # Generate text report
    report_file = OUTPUT_DIR / 'report_youtube_finds.txt'
    with open(report_file, 'w') as f:
        f.write("# YOUTUBE SEARCH RESULTS (via Gemini)\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Total videos found: {len(all_results)}\n")
        f.write("=" * 60 + "\n\n")

        # Group by category
        categories = {
            'opera': [],
            'ballet': [],
            'orchestra': [],
            'theatre': [],
            'composer': []
        }

        for v in all_results:
            query = v.get('search_query', '').lower()
            if 'opera' in query:
                categories['opera'].append(v)
            elif 'ballet' in query or 'ballett' in query:
                categories['ballet'].append(v)
            elif 'filharmon' in query or 'symphony' in query or 'orkester' in query or 'kork' in query:
                categories['orchestra'].append(v)
            elif 'theatre' in query or 'teater' in query or 'teatret' in query:
                categories['theatre'].append(v)
            else:
                categories['composer'].append(v)

        for cat, videos in categories.items():
            if videos:
                f.write(f"\n## {cat.upper()} ({len(videos)} videos)\n")
                f.write("-" * 40 + "\n")
                for v in videos:
                    f.write(f"\n{v.get('title', 'Unknown')}\n")
                    f.write(f"  URL: {v.get('url', 'N/A')}\n")
                    f.write(f"  Channel: {v.get('channel', 'N/A')}\n")
                    if v.get('duration'):
                        f.write(f"  Duration: {v.get('duration')}\n")
                    if v.get('views'):
                        f.write(f"  Views: {v.get('views')}\n")

    print(f"Report saved to: {report_file}")


if __name__ == '__main__':
    main()
