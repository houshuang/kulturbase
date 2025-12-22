#!/usr/bin/env python3
"""
Test Gemini search for a single concert.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('GEMINI_KEY')

# Test with a specific concert
concert_url = "https://bergenphilive.no/alle-konsertopptak/2025/9/dvorak-fiolinkonsert/"
title = "Dvořák: Fiolinkonsert"
year = 2025

print(f"Testing conductor search for:")
print(f"  Title: {title}")
print(f"  Year: {year}")
print(f"  URL: {concert_url}")
print()

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={API_KEY}"

query = f"""Find the conductor (dirigent) for this Bergen Philharmonic concert:
URL: {concert_url}
Title: {title}
Year: {year}

Search the URL or search for "Bergen Filharmoniske {title} {year} dirigent".
Provide ONLY the conductor's full name, or "NOT_FOUND" if you cannot find it.
Format: Just the name like "Edward Gardner" or "NOT_FOUND"
"""

payload = {
    "contents": [{"parts": [{"text": query}]}],
    "tools": [{"google_search": {}}],
    "generationConfig": {"temperature": 0.1}
}

print("Calling Gemini API...")
r = requests.post(url, json=payload, timeout=30)

if r.ok:
    result = r.json()
    print("\nFull API response:")
    print(result)
    print()

    if 'candidates' in result and len(result['candidates']) > 0:
        candidate = result['candidates'][0]
        if 'content' in candidate and 'parts' in candidate['content']:
            parts = candidate['content']['parts']
            for part in parts:
                if 'text' in part:
                    print("Extracted text:")
                    print(part['text'])
                    print()
else:
    print(f"Error: {r.status_code}")
    print(r.text)
