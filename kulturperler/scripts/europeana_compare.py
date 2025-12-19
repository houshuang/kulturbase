#!/usr/bin/env python3
"""
Compare Europeana NRK video content against kulturperler database.
Identifies:
1. Content in both (could be fallback URLs)
2. Content only in Europeana (potentially new content to add)
"""
import json
import requests
import sqlite3
import re
from collections import defaultdict

API_KEY = "api2demo"
BASE_URL = "https://api.europeana.eu/record/v2/search.json"

def extract_prf_id_from_url(url):
    """Extract program ID from various NRK URL formats"""
    if not url:
        return None
    # Format: https://tv.nrk.no/serie/fjernsynsteatret/FTEA00005387
    match = re.search(r'/([A-Z]{4}\d{8})', url)
    if match:
        return match.group(1)
    # Format: https://tv.nrk.no/se?v=FDRP17010099
    match = re.search(r'v=([A-Z]{4}\d{8})', url)
    if match:
        return match.group(1)
    # Timestamped format: /FMAA50000450/26-01-1950#t=4m5s
    match = re.search(r'/([A-Z]{4}\d{8})/', url)
    if match:
        return match.group(1)
    return None

def fetch_all_europeana_nrk_videos():
    """Fetch all NRK video content from Europeana using cursor pagination"""
    all_items = []
    cursor = "*"
    batch = 0

    while cursor:
        batch += 1
        params = {
            "wskey": API_KEY,
            "query": "*",
            "qf": ["DATA_PROVIDER:NRK", "TYPE:VIDEO"],
            "rows": 100,
            "cursor": cursor
        }

        try:
            response = requests.get(BASE_URL, params=params, timeout=30)
            data = response.json()
        except Exception as e:
            print(f"Error fetching batch {batch}: {e}")
            break

        items = data.get("items", [])
        all_items.extend(items)

        # Get next cursor
        cursor = data.get("nextCursor")

        print(f"Batch {batch}: fetched {len(items)} items (total: {len(all_items)})")

        if not cursor:
            break

    return all_items

def main():
    print("=" * 60)
    print("EUROPEANA NRK CONTENT vs KULTURPERLER DATABASE")
    print("=" * 60)

    print("\n1. Fetching all Europeana NRK video content...")
    europeana_items = fetch_all_europeana_nrk_videos()
    print(f"\nTotal Europeana NRK items fetched: {len(europeana_items)}")

    # Extract program IDs and organize by series
    europeana_by_prf = {}
    europeana_by_series = defaultdict(list)
    no_prf_id = []

    for item in europeana_items:
        url = item.get("edmIsShownAt", [None])[0] if item.get("edmIsShownAt") else None
        prf_id = extract_prf_id_from_url(url)

        title_dict = item.get("dcTitleLangAware", {})
        title = title_dict.get("no", title_dict.get("def", ["Unknown"]))[0]

        desc_dict = item.get("dcDescriptionLangAware", {})
        desc = desc_dict.get("no", desc_dict.get("def", [""]))[0] if desc_dict else ""

        # Detect series from URL
        series = None
        if url:
            if "fjernsynsteatret" in url:
                series = "fjernsynsteatret"
            elif "filmavisen" in url:
                series = "filmavisen"
            elif "radioteatret" in url or "horespill" in url:
                series = "radioteatret"
            else:
                # Extract series from URL pattern /serie/XXX/
                match = re.search(r'/serie/([^/]+)/', url)
                if match:
                    series = match.group(1)

        item_data = {
            "title": title,
            "url": url,
            "europeana_id": item.get("id"),
            "description": desc[:500] if desc else "",
            "series": series
        }

        if prf_id:
            europeana_by_prf[prf_id] = item_data
            if series:
                europeana_by_series[series].append((prf_id, item_data))
        else:
            no_prf_id.append(item_data)

    print(f"Items with extractable prf_id: {len(europeana_by_prf)}")
    print(f"Items without extractable prf_id: {len(no_prf_id)}")

    print("\n2. Series breakdown in Europeana:")
    for series, items in sorted(europeana_by_series.items(), key=lambda x: -len(x[1])):
        print(f"   {series}: {len(items)}")

    # Connect to database
    print("\n3. Loading kulturperler database...")
    conn = sqlite3.connect("/Users/stian/src/nrk/kulturperler/web/static/kulturperler.db")
    cursor = conn.cursor()

    # Get all episodes from database with their NRK URLs
    cursor.execute("""
        SELECT e.prf_id, e.title, e.nrk_url, e.description, p.title as play_title
        FROM episodes e
        LEFT JOIN plays p ON e.play_id = p.id
    """)
    db_episodes = {}
    for row in cursor.fetchall():
        prf_id, title, nrk_url, desc, play_title = row
        db_episodes[prf_id] = {
            "title": title,
            "nrk_url": nrk_url,
            "description": desc,
            "play_title": play_title
        }
        # Also try to extract prf_id from the nrk_url if different format
        if nrk_url:
            url_prf = extract_prf_id_from_url(nrk_url)
            if url_prf and url_prf != prf_id:
                db_episodes[url_prf] = db_episodes[prf_id]

    print(f"Database episodes: {len(db_episodes)}")

    # Compare
    in_both = []
    europeana_only = []

    for prf_id, eu_data in europeana_by_prf.items():
        if prf_id in db_episodes:
            in_both.append({
                "prf_id": prf_id,
                "europeana_title": eu_data["title"],
                "db_title": db_episodes[prf_id]["title"],
                "europeana_url": eu_data["url"],
                "db_url": db_episodes[prf_id]["nrk_url"],
                "series": eu_data["series"],
                "play_title": db_episodes[prf_id]["play_title"]
            })
        else:
            europeana_only.append({
                "prf_id": prf_id,
                "title": eu_data["title"],
                "url": eu_data["url"],
                "europeana_id": eu_data["europeana_id"],
                "series": eu_data["series"],
                "description": eu_data["description"]
            })

    print("\n" + "=" * 60)
    print("COMPARISON RESULTS")
    print("=" * 60)
    print(f"\nIn BOTH Europeana and database: {len(in_both)}")
    print(f"In Europeana ONLY (not in database): {len(europeana_only)}")

    # Series breakdown for europeana-only items
    europeana_only_by_series = defaultdict(list)
    for item in europeana_only:
        series = item.get("series") or "unknown"
        europeana_only_by_series[series].append(item)

    print("\n4. EUROPEANA-ONLY items by series:")
    for series, items in sorted(europeana_only_by_series.items(), key=lambda x: -len(x[1])):
        print(f"   {series}: {len(items)}")

    # Show fjernsynsteatret content not in database
    fjernsynsteatret_only = europeana_only_by_series.get("fjernsynsteatret", [])
    if fjernsynsteatret_only:
        print(f"\n5. FJERNSYNSTEATRET items NOT in database ({len(fjernsynsteatret_only)}):")
        for item in sorted(fjernsynsteatret_only, key=lambda x: x["title"])[:50]:
            print(f"\n   {item['prf_id']}: {item['title']}")
            print(f"   URL: {item['url']}")
            if item['description']:
                print(f"   Desc: {item['description'][:200]}...")

    # Check for matching content that could use fallback URLs
    print(f"\n6. Items in BOTH (could add Europeana as reference):")
    fjernsynsteatret_both = [i for i in in_both if i.get("series") == "fjernsynsteatret"]
    print(f"   Fjernsynsteatret items in both: {len(fjernsynsteatret_both)}")

    conn.close()

    # Save detailed results
    results = {
        "summary": {
            "total_europeana": len(europeana_items),
            "with_prf_id": len(europeana_by_prf),
            "in_both": len(in_both),
            "europeana_only": len(europeana_only),
            "database_episodes": len(db_episodes)
        },
        "in_both": in_both,
        "europeana_only": europeana_only,
        "europeana_only_by_series": {k: v for k, v in europeana_only_by_series.items()}
    }

    with open("europeana_comparison.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nDetailed results saved to europeana_comparison.json")

if __name__ == "__main__":
    main()
