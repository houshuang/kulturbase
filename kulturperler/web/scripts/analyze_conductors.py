#!/usr/bin/env python3
"""Quick script to analyze conductor names that will be added."""

import sqlite3
import yaml
import re
import requests
from pathlib import Path
from collections import Counter

DB_PATH = Path('static/kulturperler.db')

def get_person_by_name(conn, name):
    normalized = name.lower().strip()
    cursor = conn.execute(
        "SELECT id, name FROM persons WHERE LOWER(name) = ? OR LOWER(normalized_name) = ?",
        (normalized, normalized)
    )
    return cursor.fetchone()

def extract_conductor_from_nrk_api(nrk_data):
    if not nrk_data:
        return None

    contributors = nrk_data.get('contributors', [])
    for contrib in contributors:
        role = contrib.get('role', '').lower()
        if 'dirigent' in role:
            name = contrib.get('name', '').strip()
            if name and name != 'Arkivpublisering':
                return name

    long_desc = nrk_data.get('longDescription', '')
    match = re.search(r'Dirigent:\s*([^.\n]+)', long_desc, re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        name = re.sub(r'\s*\(.*?\)\s*$', '', name)
        name = re.sub(r'\.$', '', name)
        return name

    return None

def extract_conductor_from_description(description):
    if not description:
        return None

    patterns = [
        r'Dirigent:\s*([^.\n]+)',
        r'dirigent\s+([A-ZÆØÅ][a-zæøå]+(?:\s+[A-ZÆØÅ][a-zæøå]+)*)',
        r'dirigeres av\s+([^.\n]+)',
        r'med dirigent\s+([^.\n]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            name = re.sub(r'\s*\(.*?\)\s*$', '', name)
            name = re.sub(r'\.$', '', name)
            name = re.sub(r'\s+(og|med|i|fra).*$', '', name, flags=re.IGNORECASE)
            return name

    return None

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

query = """
    SELECT p.id, p.title, p.description, e.prf_id
    FROM performances p
    JOIN works w ON p.work_id = w.id
    LEFT JOIN episodes e ON p.id = e.performance_id
    LEFT JOIN performance_persons pp ON p.id = pp.performance_id AND pp.role = 'conductor'
    WHERE w.category = 'konsert' AND p.source = 'nrk'
    GROUP BY p.id
    HAVING COUNT(pp.person_id) = 0
"""

cursor = conn.execute(query)
performances = [dict(row) for row in cursor.fetchall()]

new_conductors = []
existing_conductors = []

for perf in performances:
    conductor_name = None

    if perf['prf_id']:
        try:
            response = requests.get(f"https://psapi.nrk.no/programs/{perf['prf_id']}", timeout=10)
            response.raise_for_status()
            conductor_name = extract_conductor_from_nrk_api(response.json())
        except:
            pass

    if not conductor_name and perf['description']:
        conductor_name = extract_conductor_from_description(perf['description'])

    if conductor_name:
        existing = get_person_by_name(conn, conductor_name)
        if existing:
            existing_conductors.append(conductor_name)
        else:
            new_conductors.append(conductor_name)

conn.close()

print("NEW CONDUCTORS TO BE CREATED:")
print("=" * 80)
conductor_counts = Counter(new_conductors)
for conductor, count in conductor_counts.most_common():
    print(f"{conductor:40} ({count} performances)")

print(f"\nTotal new conductors: {len(conductor_counts)}")
print(f"Total existing conductors to link: {len(existing_conductors)}")
print(f"\nEXISTING CONDUCTORS:")
for conductor in sorted(set(existing_conductors)):
    print(f"  - {conductor}")
