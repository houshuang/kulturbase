#!/usr/bin/env python3
"""
Build SQLite database from YAML files.

This reads all data from data/ and compiles it into static/kulturperler.db.
The database is now a build artifact, not the source of truth.
"""

import sqlite3
import os
import yaml
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).parent.parent / 'data'
OUTPUT_PATH = Path(__file__).parent.parent / 'static' / 'kulturperler.db'

SCHEMA = """
-- Works table (formerly plays - now supports plays, opera, concerts, drama series)
CREATE TABLE works (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    original_title TEXT,
    work_type TEXT,           -- teaterstykke, nrk_teaterstykke, dramaserie, opera, konsert
    category TEXT,            -- teater, opera, konsert, dramaserie (for UI grouping)
    playwright_id INTEGER,    -- for plays
    composer_id INTEGER,      -- for opera/concerts
    librettist_id INTEGER,    -- for opera (text author)
    creator_id INTEGER,       -- generic creator fallback
    year_written INTEGER,
    synopsis TEXT,
    based_on_work_id INTEGER, -- if this work is based on another work
    wikidata_id TEXT,
    sceneweb_id INTEGER,
    sceneweb_url TEXT,
    wikipedia_url TEXT,
    FOREIGN KEY (playwright_id) REFERENCES persons(id),
    FOREIGN KEY (composer_id) REFERENCES persons(id),
    FOREIGN KEY (librettist_id) REFERENCES persons(id),
    FOREIGN KEY (creator_id) REFERENCES persons(id),
    FOREIGN KEY (based_on_work_id) REFERENCES works(id)
);

-- Keep plays as a view for backwards compatibility
CREATE VIEW plays AS SELECT * FROM works WHERE category = 'teater' OR category IS NULL;

-- Persons table
CREATE TABLE persons (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    normalized_name TEXT,
    birth_year INTEGER,
    death_year INTEGER,
    nationality TEXT,
    bio TEXT,
    wikidata_id TEXT,
    sceneweb_id INTEGER,
    sceneweb_url TEXT,
    wikipedia_url TEXT
);

-- Institutions table (orchestras, theaters, opera houses, etc.)
CREATE TABLE institutions (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    short_name TEXT,
    type TEXT,              -- orchestra, theater, opera_house, ensemble
    location TEXT,
    founded_year INTEGER,
    bio TEXT,
    wikipedia_url TEXT,
    image_url TEXT
);

-- Episodes table
CREATE TABLE episodes (
    prf_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    year INTEGER,
    duration_seconds INTEGER,
    image_url TEXT,
    nrk_url TEXT,
    youtube_url TEXT,
    work_id INTEGER,        -- renamed from play_id
    performance_id INTEGER,
    source TEXT DEFAULT 'nrk',
    medium TEXT DEFAULT 'tv',
    series_id TEXT,
    FOREIGN KEY (work_id) REFERENCES works(id),
    FOREIGN KEY (performance_id) REFERENCES performances(id)
);

-- Episode persons (junction table)
CREATE TABLE episode_persons (
    id INTEGER PRIMARY KEY,
    episode_id TEXT NOT NULL,
    person_id INTEGER NOT NULL,
    role TEXT,
    character_name TEXT,
    FOREIGN KEY (episode_id) REFERENCES episodes(prf_id),
    FOREIGN KEY (person_id) REFERENCES persons(id)
);

-- Performances table
CREATE TABLE performances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER,
    source TEXT DEFAULT 'nrk',
    year INTEGER,
    title TEXT,
    description TEXT,
    venue TEXT,
    total_duration INTEGER,
    image_url TEXT,
    medium TEXT DEFAULT 'tv',
    series_id TEXT,
    FOREIGN KEY (work_id) REFERENCES works(id)
);

-- Performance institutions (junction table for orchestras, ensembles, etc.)
CREATE TABLE performance_institutions (
    performance_id INTEGER NOT NULL,
    institution_id INTEGER NOT NULL,
    role TEXT,              -- orchestra, ensemble, co_producer, etc.
    PRIMARY KEY (performance_id, institution_id, role),
    FOREIGN KEY (performance_id) REFERENCES performances(id),
    FOREIGN KEY (institution_id) REFERENCES institutions(id)
);

-- Performance persons (junction table)
CREATE TABLE performance_persons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    performance_id INTEGER NOT NULL,
    person_id INTEGER NOT NULL,
    role TEXT,
    character_name TEXT,
    UNIQUE(performance_id, person_id, role, character_name),
    FOREIGN KEY (performance_id) REFERENCES performances(id),
    FOREIGN KEY (person_id) REFERENCES persons(id)
);

-- NRK about programs
CREATE TABLE nrk_about_programs (
    id TEXT PRIMARY KEY,
    person_id INTEGER,
    title TEXT,
    description TEXT,
    duration_seconds INTEGER,
    nrk_url TEXT,
    image_url TEXT,
    program_type TEXT,
    year INTEGER,
    episode_count INTEGER,
    interest_score INTEGER DEFAULT 0,
    FOREIGN KEY (person_id) REFERENCES persons(id)
);

-- Tags table
CREATE TABLE tags (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    color TEXT
);

-- Episode tags (junction table)
CREATE TABLE episode_tags (
    episode_id TEXT NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (episode_id, tag_id),
    FOREIGN KEY (episode_id) REFERENCES episodes(prf_id),
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);

-- Work tags (junction table)
CREATE TABLE work_tags (
    work_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (work_id, tag_id),
    FOREIGN KEY (work_id) REFERENCES works(id),
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);

-- External resources table
CREATE TABLE external_resources (
    id INTEGER PRIMARY KEY,
    url TEXT NOT NULL,
    title TEXT,
    type TEXT,
    description TEXT,
    added_date TEXT,
    verified_date TEXT,
    is_working INTEGER DEFAULT 1
);

-- Episode resources (junction table)
CREATE TABLE episode_resources (
    episode_id TEXT NOT NULL,
    resource_id INTEGER NOT NULL,
    PRIMARY KEY (episode_id, resource_id),
    FOREIGN KEY (episode_id) REFERENCES episodes(prf_id),
    FOREIGN KEY (resource_id) REFERENCES external_resources(id)
);

-- Work resources (junction table)
CREATE TABLE work_resources (
    work_id INTEGER NOT NULL,
    resource_id INTEGER NOT NULL,
    PRIMARY KEY (work_id, resource_id),
    FOREIGN KEY (work_id) REFERENCES works(id),
    FOREIGN KEY (resource_id) REFERENCES external_resources(id)
);

-- Person resources (junction table)
CREATE TABLE person_resources (
    person_id INTEGER NOT NULL,
    resource_id INTEGER NOT NULL,
    PRIMARY KEY (person_id, resource_id),
    FOREIGN KEY (person_id) REFERENCES persons(id),
    FOREIGN KEY (resource_id) REFERENCES external_resources(id)
);

-- Work external links
CREATE TABLE work_external_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    title TEXT,
    type TEXT,
    access_note TEXT,
    FOREIGN KEY (work_id) REFERENCES works(id)
);

-- Metadata table
CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Indices
CREATE INDEX idx_works_playwright ON works(playwright_id);
CREATE INDEX idx_works_composer ON works(composer_id);
CREATE INDEX idx_works_type ON works(work_type);
CREATE INDEX idx_works_category ON works(category);
CREATE INDEX idx_episodes_year ON episodes(year);
CREATE INDEX idx_episodes_work ON episodes(work_id);
CREATE INDEX idx_episodes_medium ON episodes(medium);
CREATE INDEX idx_episode_persons_role ON episode_persons(role);
CREATE INDEX idx_episode_persons_episode ON episode_persons(episode_id);
CREATE INDEX idx_episode_persons_person ON episode_persons(person_id);
CREATE INDEX idx_persons_name ON persons(normalized_name);
CREATE INDEX idx_performances_work ON performances(work_id);
CREATE INDEX idx_performances_year ON performances(year);
CREATE INDEX idx_performances_medium ON performances(medium);
CREATE INDEX idx_performances_series ON performances(series_id);
CREATE INDEX idx_performance_persons_perf ON performance_persons(performance_id);
CREATE INDEX idx_performance_persons_person ON performance_persons(person_id);
CREATE INDEX idx_performance_persons_role ON performance_persons(role);
CREATE INDEX idx_performance_institutions_perf ON performance_institutions(performance_id);
CREATE INDEX idx_performance_institutions_inst ON performance_institutions(institution_id);
CREATE INDEX idx_work_external_links_work_id ON work_external_links(work_id);
CREATE INDEX idx_institutions_type ON institutions(type);

-- Full-text search table
CREATE VIRTUAL TABLE episodes_fts USING fts5(
    prf_id,
    title,
    description,
    content='episodes',
    content_rowid='rowid'
);

-- Trigger to keep FTS in sync
CREATE TRIGGER episodes_ai AFTER INSERT ON episodes BEGIN
    INSERT INTO episodes_fts(rowid, prf_id, title, description)
    VALUES (NEW.rowid, NEW.prf_id, NEW.title, NEW.description);
END;
"""


def load_yaml(path):
    """Load YAML file."""
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_yaml_dir(dir_path):
    """Load all YAML files from a directory."""
    data = []
    for file in sorted(dir_path.glob('*.yaml')):
        data.append(load_yaml(file))
    return data


def build_database():
    print(f"Building database from {DATA_DIR}")
    print(f"Output: {OUTPUT_PATH}")
    print()

    # Remove existing database
    if OUTPUT_PATH.exists():
        OUTPUT_PATH.unlink()

    conn = sqlite3.connect(OUTPUT_PATH)
    conn.executescript(SCHEMA)

    stats = {}

    # Load and insert persons first (needed for foreign keys)
    print("Loading persons...")
    persons = load_yaml_dir(DATA_DIR / 'persons')
    person_resources = []
    for p in persons:
        conn.execute("""
            INSERT INTO persons (id, name, normalized_name, birth_year, death_year,
                                 nationality, bio, wikidata_id, sceneweb_id, sceneweb_url, wikipedia_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (p['id'], p['name'], p.get('normalized_name'), p.get('birth_year'),
              p.get('death_year'), p.get('nationality'), p.get('bio'),
              p.get('wikidata_id'), p.get('sceneweb_id'), p.get('sceneweb_url'), p.get('wikipedia_url')))
        for res in p.get('resources', []):
            person_resources.append((p['id'], res['id']))
    stats['persons'] = len(persons)
    print(f"  Inserted {len(persons)} persons")

    # Load and insert works (supports both old 'plays' dir and new 'works' dir)
    print("Loading works...")
    works_dir = DATA_DIR / 'works'
    if not works_dir.exists():
        works_dir = DATA_DIR / 'plays'  # Fallback to old directory name
    works = load_yaml_dir(works_dir)
    work_external_links = []
    for w in works:
        conn.execute("""
            INSERT INTO works (id, title, original_title, work_type, category,
                              playwright_id, composer_id, librettist_id, creator_id,
                              year_written, synopsis, based_on_work_id,
                              wikidata_id, sceneweb_id, sceneweb_url, wikipedia_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (w['id'], w['title'], w.get('original_title'), w.get('work_type'), w.get('category'),
              w.get('playwright_id'), w.get('composer_id'), w.get('librettist_id'), w.get('creator_id'),
              w.get('year_written'), w.get('synopsis'), w.get('based_on_work_id'),
              w.get('wikidata_id'), w.get('sceneweb_id'), w.get('sceneweb_url'), w.get('wikipedia_url')))
        for link in w.get('external_links', []):
            work_external_links.append((
                w['id'], link['url'], link.get('title'), link.get('type'), link.get('access_note')
            ))
    stats['works'] = len(works)
    print(f"  Inserted {len(works)} works")

    # Insert work external links
    if work_external_links:
        print("  Inserting work external links...")
        for link in work_external_links:
            conn.execute("""
                INSERT INTO work_external_links (work_id, url, title, type, access_note)
                VALUES (?, ?, ?, ?, ?)
            """, link)
        stats['work_external_links'] = len(work_external_links)
        print(f"  Inserted {len(work_external_links)} work external links")

    # Load and insert institutions (if directory exists)
    institutions_dir = DATA_DIR / 'institutions'
    if institutions_dir.exists():
        print("Loading institutions...")
        institutions = load_yaml_dir(institutions_dir)
        for inst in institutions:
            conn.execute("""
                INSERT INTO institutions (id, name, short_name, type, location,
                                         founded_year, bio, wikipedia_url, image_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (inst['id'], inst['name'], inst.get('short_name'), inst.get('type'),
                  inst.get('location'), inst.get('founded_year'), inst.get('bio'),
                  inst.get('wikipedia_url'), inst.get('image_url')))
        stats['institutions'] = len(institutions)
        print(f"  Inserted {len(institutions)} institutions")
    else:
        stats['institutions'] = 0

    # Load and insert performances
    print("Loading performances...")
    performances = load_yaml_dir(DATA_DIR / 'performances')
    performance_credits = []
    performance_institution_links = []
    for p in performances:
        conn.execute("""
            INSERT INTO performances (id, work_id, source, year, title, description,
                                      venue, total_duration, image_url, medium, series_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (p['id'], p.get('work_id'), p.get('source'), p.get('year'), p.get('title'),
              p.get('description'), p.get('venue'), p.get('total_duration'),
              p.get('image_url'), p.get('medium'), p.get('series_id')))
        for credit in p.get('credits', []):
            performance_credits.append((
                p['id'], credit['person_id'], credit.get('role'), credit.get('character_name')
            ))
        # Handle institution links (orchestras, ensembles, etc.)
        for inst_link in p.get('institutions', []):
            performance_institution_links.append((
                p['id'], inst_link['institution_id'], inst_link.get('role', 'orchestra')
            ))
    stats['performances'] = len(performances)
    print(f"  Inserted {len(performances)} performances")

    # Insert performance credits
    print("  Inserting performance credits...")
    for pc in performance_credits:
        conn.execute("""
            INSERT OR IGNORE INTO performance_persons (performance_id, person_id, role, character_name)
            VALUES (?, ?, ?, ?)
        """, pc)
    stats['performance_credits'] = len(performance_credits)
    print(f"  Inserted {len(performance_credits)} performance credits")

    # Insert performance institution links
    if performance_institution_links:
        print("  Inserting performance institution links...")
        for pi in performance_institution_links:
            conn.execute("""
                INSERT OR IGNORE INTO performance_institutions (performance_id, institution_id, role)
                VALUES (?, ?, ?)
            """, pi)
        print(f"  Inserted {len(performance_institution_links)} performance institution links")

    # Load and insert episodes
    print("Loading episodes...")
    episodes = load_yaml_dir(DATA_DIR / 'episodes')
    episode_credits = []
    episode_resources = []
    for e in episodes:
        # Support both old 'play_id' and new 'work_id' field names
        work_id = e.get('work_id') or e.get('play_id')
        conn.execute("""
            INSERT INTO episodes (prf_id, title, description, year, duration_seconds,
                                 image_url, nrk_url, youtube_url, work_id, performance_id, source, medium, series_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (e['prf_id'], e['title'], e.get('description'), e.get('year'),
              e.get('duration_seconds'), e.get('image_url'), e.get('nrk_url'),
              e.get('youtube_url'), work_id, e.get('performance_id'), e.get('source'),
              e.get('medium'), e.get('series_id')))
        for credit in e.get('credits', []):
            episode_credits.append((
                e['prf_id'], credit['person_id'], credit.get('role'), credit.get('character_name')
            ))
        for res in e.get('resources', []):
            episode_resources.append((e['prf_id'], res['id']))
    stats['episodes'] = len(episodes)
    print(f"  Inserted {len(episodes)} episodes")

    # Insert episode credits
    print("  Inserting episode credits...")
    credit_id = 1
    for ec in episode_credits:
        conn.execute("""
            INSERT INTO episode_persons (id, episode_id, person_id, role, character_name)
            VALUES (?, ?, ?, ?, ?)
        """, (credit_id, ec[0], ec[1], ec[2], ec[3]))
        credit_id += 1
    stats['episode_credits'] = len(episode_credits)
    print(f"  Inserted {len(episode_credits)} episode credits")

    # Load and insert NRK about programs
    print("Loading NRK about programs...")
    nrk_programs = load_yaml_dir(DATA_DIR / 'nrk_about_programs')
    for p in nrk_programs:
        conn.execute("""
            INSERT INTO nrk_about_programs (id, person_id, title, description, duration_seconds,
                                           nrk_url, image_url, program_type, year, episode_count, interest_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (p['id'], p.get('person_id'), p.get('title'), p.get('description'),
              p.get('duration_seconds'), p.get('nrk_url'), p.get('image_url'),
              p.get('program_type'), p.get('year'), p.get('episode_count'), p.get('interest_score')))
    stats['nrk_about_programs'] = len(nrk_programs)
    print(f"  Inserted {len(nrk_programs)} NRK about programs")

    # Load and insert tags
    print("Loading tags...")
    tags = load_yaml(DATA_DIR / 'tags.yaml')
    for t in tags:
        conn.execute("""
            INSERT INTO tags (id, name, display_name, color)
            VALUES (?, ?, ?, ?)
        """, (t['id'], t['name'], t['display_name'], t.get('color')))
    stats['tags'] = len(tags)
    print(f"  Inserted {len(tags)} tags")

    # Load and insert external resources
    print("Loading external resources...")
    resources = load_yaml(DATA_DIR / 'external_resources.yaml')
    for r in resources:
        conn.execute("""
            INSERT INTO external_resources (id, url, title, type, description, added_date, verified_date, is_working)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (r['id'], r['url'], r.get('title'), r.get('type'), r.get('description'),
              r.get('added_date'), r.get('verified_date'), r.get('is_working')))
    stats['external_resources'] = len(resources)
    print(f"  Inserted {len(resources)} external resources")

    # Insert resource links
    print("  Inserting resource links...")
    for ep_id, res_id in episode_resources:
        conn.execute("INSERT INTO episode_resources (episode_id, resource_id) VALUES (?, ?)", (ep_id, res_id))
    for p_id, res_id in person_resources:
        conn.execute("INSERT INTO person_resources (person_id, resource_id) VALUES (?, ?)", (p_id, res_id))
    print(f"  Inserted {len(episode_resources)} episode-resource links")
    print(f"  Inserted {len(person_resources)} person-resource links")
    stats['episode_resources'] = len(episode_resources)
    stats['person_resources'] = len(person_resources)

    # Load and insert metadata
    print("Loading metadata...")
    metadata = load_yaml(DATA_DIR / 'metadata.yaml')
    for key, value in metadata.items():
        conn.execute("INSERT INTO metadata (key, value) VALUES (?, ?)", (key, value))
    stats['metadata'] = len(metadata)
    print(f"  Inserted {len(metadata)} metadata entries")

    conn.commit()
    conn.close()

    print()
    print("Build complete!")
    print(f"  Database size: {OUTPUT_PATH.stat().st_size / 1024 / 1024:.2f} MB")
    return stats


def verify_counts():
    """Verify row counts match expected values."""
    print()
    print("Verifying row counts...")
    conn = sqlite3.connect(OUTPUT_PATH)

    counts = {}
    for table in ['works', 'persons', 'institutions', 'episodes', 'performances',
                  'episode_persons', 'performance_persons', 'performance_institutions',
                  'nrk_about_programs', 'tags', 'external_resources', 'work_external_links',
                  'episode_resources', 'person_resources', 'metadata']:
        cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
        counts[table] = cursor.fetchone()[0]

    conn.close()

    print("  Table counts:")
    for table, count in counts.items():
        print(f"    {table}: {count}")

    # Also verify works by category
    conn = sqlite3.connect(OUTPUT_PATH)
    cursor = conn.execute("SELECT category, COUNT(*) FROM works GROUP BY category")
    print("\n  Works by category:")
    for row in cursor.fetchall():
        cat = row[0] or '(none)'
        print(f"    {cat}: {row[1]}")

    cursor = conn.execute("SELECT work_type, COUNT(*) FROM works GROUP BY work_type")
    print("\n  Works by type:")
    for row in cursor.fetchall():
        wtype = row[0] or '(none)'
        print(f"    {wtype}: {row[1]}")

    conn.close()

    return counts


if __name__ == '__main__':
    stats = build_database()
    counts = verify_counts()
