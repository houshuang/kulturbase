#!/usr/bin/env python3
"""
Export SQLite database to YAML files.

This creates the data/ directory structure with all data as YAML files,
which then becomes the source of truth for the database.
"""

import sqlite3
import os
import yaml
from pathlib import Path
from collections import defaultdict

# Configure YAML to use block style for multiline strings
def str_representer(dumper, data):
    if '\n' in data:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

yaml.add_representer(str, str_representer)

DB_PATH = Path(__file__).parent.parent / 'static' / 'kulturperler.db'
DATA_DIR = Path(__file__).parent.parent / 'data'


def dict_factory(cursor, row):
    """Convert sqlite row to dict."""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def clean_dict(d):
    """Remove None values and empty strings from dict for cleaner YAML."""
    return {k: v for k, v in d.items() if v is not None and v != ''}


def write_yaml(path, data):
    """Write data to YAML file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def export_plays(conn):
    """Export plays table."""
    print("Exporting plays...")
    cursor = conn.execute("SELECT * FROM plays ORDER BY id")
    plays = cursor.fetchall()

    for play in plays:
        data = clean_dict({
            'id': play['id'],
            'title': play['title'],
            'original_title': play['original_title'],
            'playwright_id': play['playwright_id'],
            'year_written': play['year_written'],
            'synopsis': play['synopsis'],
            'wikidata_id': play['wikidata_id'],
            'sceneweb_id': play['sceneweb_id'],
            'sceneweb_url': play['sceneweb_url'],
            'wikipedia_url': play['wikipedia_url'],
        })
        write_yaml(DATA_DIR / 'plays' / f"{play['id']}.yaml", data)

    print(f"  Exported {len(plays)} plays")
    return len(plays)


def export_persons(conn):
    """Export persons table."""
    print("Exporting persons...")
    cursor = conn.execute("SELECT * FROM persons ORDER BY id")
    persons = cursor.fetchall()

    # Get person resources
    person_resources = defaultdict(list)
    cursor = conn.execute("""
        SELECT pr.person_id, er.*
        FROM person_resources pr
        JOIN external_resources er ON pr.resource_id = er.id
    """)
    for row in cursor.fetchall():
        person_resources[row['person_id']].append(clean_dict({
            'id': row['id'],
            'url': row['url'],
            'title': row['title'],
            'type': row['type'],
            'description': row['description'],
        }))

    for person in persons:
        data = clean_dict({
            'id': person['id'],
            'name': person['name'],
            'normalized_name': person['normalized_name'],
            'birth_year': person['birth_year'],
            'death_year': person['death_year'],
            'nationality': person['nationality'],
            'bio': person['bio'],
            'wikidata_id': person['wikidata_id'],
            'sceneweb_id': person['sceneweb_id'],
            'sceneweb_url': person['sceneweb_url'],
            'wikipedia_url': person['wikipedia_url'],
        })
        if person['id'] in person_resources:
            data['resources'] = person_resources[person['id']]
        write_yaml(DATA_DIR / 'persons' / f"{person['id']}.yaml", data)

    print(f"  Exported {len(persons)} persons")
    return len(persons)


def export_episodes(conn):
    """Export episodes table with embedded credits."""
    print("Exporting episodes...")
    cursor = conn.execute("SELECT * FROM episodes ORDER BY prf_id")
    episodes = cursor.fetchall()

    # Get all episode_persons
    print("  Loading episode credits...")
    episode_credits = defaultdict(list)
    cursor = conn.execute("""
        SELECT episode_id, person_id, role, character_name
        FROM episode_persons
        ORDER BY episode_id, id
    """)
    for row in cursor.fetchall():
        episode_credits[row['episode_id']].append(clean_dict({
            'person_id': row['person_id'],
            'role': row['role'],
            'character_name': row['character_name'],
        }))

    # Get episode resources
    episode_resources = defaultdict(list)
    cursor = conn.execute("""
        SELECT er_link.episode_id, er.*
        FROM episode_resources er_link
        JOIN external_resources er ON er_link.resource_id = er.id
    """)
    for row in cursor.fetchall():
        episode_resources[row['episode_id']].append(clean_dict({
            'id': row['id'],
            'url': row['url'],
            'title': row['title'],
            'type': row['type'],
            'description': row['description'],
        }))

    total_credits = 0
    for episode in episodes:
        prf_id = episode['prf_id']
        data = clean_dict({
            'prf_id': prf_id,
            'title': episode['title'],
            'description': episode['description'],
            'year': episode['year'],
            'duration_seconds': episode['duration_seconds'],
            'image_url': episode['image_url'],
            'nrk_url': episode['nrk_url'],
            'play_id': episode['play_id'],
            'performance_id': episode['performance_id'],
            'source': episode['source'],
            'medium': episode['medium'],
            'series_id': episode['series_id'],
        })
        if prf_id in episode_credits:
            data['credits'] = episode_credits[prf_id]
            total_credits += len(episode_credits[prf_id])
        if prf_id in episode_resources:
            data['resources'] = episode_resources[prf_id]
        write_yaml(DATA_DIR / 'episodes' / f"{prf_id}.yaml", data)

    print(f"  Exported {len(episodes)} episodes with {total_credits} credits")
    return len(episodes), total_credits


def export_performances(conn):
    """Export performances table with embedded credits."""
    print("Exporting performances...")
    cursor = conn.execute("SELECT * FROM performances ORDER BY id")
    performances = cursor.fetchall()

    # Get all performance_persons
    print("  Loading performance credits...")
    performance_credits = defaultdict(list)
    cursor = conn.execute("""
        SELECT performance_id, person_id, role, character_name
        FROM performance_persons
        ORDER BY performance_id, id
    """)
    for row in cursor.fetchall():
        performance_credits[row['performance_id']].append(clean_dict({
            'person_id': row['person_id'],
            'role': row['role'],
            'character_name': row['character_name'],
        }))

    total_credits = 0
    for perf in performances:
        perf_id = perf['id']
        data = clean_dict({
            'id': perf_id,
            'work_id': perf['work_id'],
            'source': perf['source'],
            'year': perf['year'],
            'title': perf['title'],
            'description': perf['description'],
            'venue': perf['venue'],
            'total_duration': perf['total_duration'],
            'image_url': perf['image_url'],
            'medium': perf['medium'],
            'series_id': perf['series_id'],
        })
        if perf_id in performance_credits:
            data['credits'] = performance_credits[perf_id]
            total_credits += len(performance_credits[perf_id])
        write_yaml(DATA_DIR / 'performances' / f"{perf_id}.yaml", data)

    print(f"  Exported {len(performances)} performances with {total_credits} credits")
    return len(performances), total_credits


def export_nrk_about_programs(conn):
    """Export nrk_about_programs table."""
    print("Exporting NRK about programs...")
    cursor = conn.execute("SELECT * FROM nrk_about_programs ORDER BY id")
    programs = cursor.fetchall()

    for prog in programs:
        data = clean_dict({
            'id': prog['id'],
            'person_id': prog['person_id'],
            'title': prog['title'],
            'description': prog['description'],
            'duration_seconds': prog['duration_seconds'],
            'nrk_url': prog['nrk_url'],
            'image_url': prog['image_url'],
            'program_type': prog['program_type'],
            'year': prog['year'],
            'episode_count': prog['episode_count'],
            'interest_score': prog['interest_score'],
        })
        write_yaml(DATA_DIR / 'nrk_about_programs' / f"{prog['id']}.yaml", data)

    print(f"  Exported {len(programs)} NRK about programs")
    return len(programs)


def export_tags(conn):
    """Export tags table to single file."""
    print("Exporting tags...")
    cursor = conn.execute("SELECT * FROM tags ORDER BY id")
    tags = cursor.fetchall()

    data = [clean_dict({
        'id': tag['id'],
        'name': tag['name'],
        'display_name': tag['display_name'],
        'color': tag['color'],
    }) for tag in tags]

    write_yaml(DATA_DIR / 'tags.yaml', data)
    print(f"  Exported {len(tags)} tags")
    return len(tags)


def export_external_resources(conn):
    """Export external_resources that aren't linked to specific entities."""
    print("Exporting external resources...")
    cursor = conn.execute("SELECT * FROM external_resources ORDER BY id")
    resources = cursor.fetchall()

    data = [clean_dict({
        'id': res['id'],
        'url': res['url'],
        'title': res['title'],
        'type': res['type'],
        'description': res['description'],
        'added_date': res['added_date'],
        'verified_date': res['verified_date'],
        'is_working': res['is_working'],
    }) for res in resources]

    write_yaml(DATA_DIR / 'external_resources.yaml', data)
    print(f"  Exported {len(resources)} external resources")
    return len(resources)


def export_metadata(conn):
    """Export metadata table."""
    print("Exporting metadata...")
    cursor = conn.execute("SELECT * FROM metadata")
    rows = cursor.fetchall()

    data = {row['key']: row['value'] for row in rows}
    write_yaml(DATA_DIR / 'metadata.yaml', data)
    print(f"  Exported {len(rows)} metadata entries")
    return len(rows)


def main():
    print(f"Exporting database from {DB_PATH}")
    print(f"Output directory: {DATA_DIR}")
    print()

    # Clean existing data directory
    if DATA_DIR.exists():
        import shutil
        shutil.rmtree(DATA_DIR)
    DATA_DIR.mkdir(parents=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory

    stats = {}
    stats['plays'] = export_plays(conn)
    stats['persons'] = export_persons(conn)
    stats['episodes'], stats['episode_credits'] = export_episodes(conn)
    stats['performances'], stats['performance_credits'] = export_performances(conn)
    stats['nrk_about_programs'] = export_nrk_about_programs(conn)
    stats['tags'] = export_tags(conn)
    stats['external_resources'] = export_external_resources(conn)
    stats['metadata'] = export_metadata(conn)

    conn.close()

    print()
    print("Export complete!")
    print(f"  Plays: {stats['plays']}")
    print(f"  Persons: {stats['persons']}")
    print(f"  Episodes: {stats['episodes']} (with {stats['episode_credits']} credits)")
    print(f"  Performances: {stats['performances']} (with {stats['performance_credits']} credits)")
    print(f"  NRK About Programs: {stats['nrk_about_programs']}")
    print(f"  Tags: {stats['tags']}")
    print(f"  External Resources: {stats['external_resources']}")
    print(f"  Metadata: {stats['metadata']}")


if __name__ == '__main__':
    main()
