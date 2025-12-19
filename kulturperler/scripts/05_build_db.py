#!/usr/bin/env python3
"""
Build SQLite database from harvested and enriched data.

This script creates the full database schema and populates it with data.

Usage:
    python 05_build_db.py [--input DATA_DIR] [--output DB_PATH]
"""

import argparse
import json
import sqlite3
from pathlib import Path
from datetime import datetime


SCHEMA = """
-- Teaterstykker (originalverk)
CREATE TABLE IF NOT EXISTS plays (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    original_title TEXT,
    playwright_id INTEGER,
    year_written INTEGER,
    wikidata_id TEXT,
    sceneweb_id INTEGER,
    sceneweb_url TEXT,
    wikipedia_url TEXT,
    FOREIGN KEY (playwright_id) REFERENCES persons(id)
);

-- Personer (dramatikere, regissører, skuespillere)
CREATE TABLE IF NOT EXISTS persons (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    normalized_name TEXT,
    birth_year INTEGER,
    death_year INTEGER,
    nationality TEXT,
    wikidata_id TEXT,
    sceneweb_id INTEGER,
    sceneweb_url TEXT,
    wikipedia_url TEXT
);

-- Episoder fra NRK
CREATE TABLE IF NOT EXISTS episodes (
    prf_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    year INTEGER,
    duration_seconds INTEGER,
    image_url TEXT,
    nrk_url TEXT,
    play_id INTEGER,
    source TEXT DEFAULT 'nrk',
    medium TEXT DEFAULT 'tv',  -- 'tv' or 'radio'
    FOREIGN KEY (play_id) REFERENCES plays(id)
);

-- Episode-person relasjoner
CREATE TABLE IF NOT EXISTS episode_persons (
    id INTEGER PRIMARY KEY,
    episode_id TEXT NOT NULL,
    person_id INTEGER NOT NULL,
    role TEXT,
    character_name TEXT,
    FOREIGN KEY (episode_id) REFERENCES episodes(prf_id),
    FOREIGN KEY (person_id) REFERENCES persons(id)
);

-- Tags for kategorisering
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    color TEXT
);

-- Episode tags
CREATE TABLE IF NOT EXISTS episode_tags (
    episode_id TEXT NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (episode_id, tag_id),
    FOREIGN KEY (episode_id) REFERENCES episodes(prf_id),
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);

-- Play tags
CREATE TABLE IF NOT EXISTS play_tags (
    play_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (play_id, tag_id),
    FOREIGN KEY (play_id) REFERENCES plays(id),
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);

-- Eksterne ressurser
CREATE TABLE IF NOT EXISTS external_resources (
    id INTEGER PRIMARY KEY,
    url TEXT NOT NULL,
    title TEXT,
    type TEXT,
    description TEXT,
    added_date TEXT,
    verified_date TEXT,
    is_working INTEGER DEFAULT 1
);

-- Episode resources
CREATE TABLE IF NOT EXISTS episode_resources (
    episode_id TEXT NOT NULL,
    resource_id INTEGER NOT NULL,
    PRIMARY KEY (episode_id, resource_id),
    FOREIGN KEY (episode_id) REFERENCES episodes(prf_id),
    FOREIGN KEY (resource_id) REFERENCES external_resources(id)
);

-- Play resources
CREATE TABLE IF NOT EXISTS play_resources (
    play_id INTEGER NOT NULL,
    resource_id INTEGER NOT NULL,
    PRIMARY KEY (play_id, resource_id),
    FOREIGN KEY (play_id) REFERENCES plays(id),
    FOREIGN KEY (resource_id) REFERENCES external_resources(id)
);

-- Person resources
CREATE TABLE IF NOT EXISTS person_resources (
    person_id INTEGER NOT NULL,
    resource_id INTEGER NOT NULL,
    PRIMARY KEY (person_id, resource_id),
    FOREIGN KEY (person_id) REFERENCES persons(id),
    FOREIGN KEY (resource_id) REFERENCES external_resources(id)
);

-- Eksterne opptak (Youtube, etc.)
CREATE TABLE IF NOT EXISTS external_performances (
    id INTEGER PRIMARY KEY,
    play_id INTEGER,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    platform TEXT,
    year INTEGER,
    language TEXT,
    description TEXT,
    duration_seconds INTEGER,
    venue TEXT,
    content_type TEXT,  -- full_performance, reading, documentary, discussion
    source_id TEXT,     -- original ID from source (e.g., archive.org identifier)
    thumbnail_url TEXT,
    added_date TEXT,
    verified_date TEXT,
    is_working INTEGER DEFAULT 1,
    FOREIGN KEY (play_id) REFERENCES plays(id)
);

-- External performance persons
CREATE TABLE IF NOT EXISTS external_performance_persons (
    performance_id INTEGER NOT NULL,
    person_id INTEGER NOT NULL,
    role TEXT,
    PRIMARY KEY (performance_id, person_id, role),
    FOREIGN KEY (performance_id) REFERENCES external_performances(id),
    FOREIGN KEY (person_id) REFERENCES persons(id)
);

-- Link health tracking
CREATE TABLE IF NOT EXISTS link_checks (
    id INTEGER PRIMARY KEY,
    url TEXT NOT NULL,
    entity_type TEXT,
    entity_id TEXT,
    last_check TEXT,
    status_code INTEGER,
    is_available INTEGER
);

-- Metadata
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Indekser
CREATE INDEX IF NOT EXISTS idx_plays_playwright ON plays(playwright_id);
CREATE INDEX IF NOT EXISTS idx_episodes_year ON episodes(year);
CREATE INDEX IF NOT EXISTS idx_episodes_play ON episodes(play_id);
CREATE INDEX IF NOT EXISTS idx_episodes_medium ON episodes(medium);
CREATE INDEX IF NOT EXISTS idx_episode_persons_role ON episode_persons(role);
CREATE INDEX IF NOT EXISTS idx_episode_persons_episode ON episode_persons(episode_id);
CREATE INDEX IF NOT EXISTS idx_episode_persons_person ON episode_persons(person_id);
CREATE INDEX IF NOT EXISTS idx_persons_name ON persons(normalized_name);

-- Full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS episodes_fts USING fts5(
    prf_id,
    title,
    description,
    content='episodes',
    content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS episodes_ai AFTER INSERT ON episodes BEGIN
    INSERT INTO episodes_fts(rowid, prf_id, title, description)
    VALUES (NEW.rowid, NEW.prf_id, NEW.title, NEW.description);
END;
"""


def normalize_name(name: str) -> str:
    """Normalize a name for searching."""
    if not name:
        return ""
    # Remove extra whitespace, lowercase
    normalized = " ".join(name.lower().split())
    return normalized


def get_or_create_person(conn: sqlite3.Connection, name: str) -> int:
    """Get or create a person by name, return their ID."""
    cursor = conn.cursor()
    normalized = normalize_name(name)

    # Check if exists
    cursor.execute(
        "SELECT id FROM persons WHERE normalized_name = ?",
        (normalized,)
    )
    row = cursor.fetchone()
    if row:
        return row[0]

    # Create new
    cursor.execute(
        "INSERT INTO persons (name, normalized_name) VALUES (?, ?)",
        (name, normalized)
    )
    conn.commit()
    return cursor.lastrowid


def map_role(api_role: str) -> str:
    """Map NRK API role to our simplified role."""
    role_lower = api_role.lower()

    if any(word in role_lower for word in ["regissør", "regi"]):
        return "director"
    if any(word in role_lower for word in ["skuespiller", "medvirkende", "artist"]):
        return "actor"
    if any(word in role_lower for word in ["manusforfatter", "forfatter"]):
        return "playwright"
    if any(word in role_lower for word in ["komponist", "musikk"]):
        return "composer"
    if any(word in role_lower for word in ["scenograf"]):
        return "set_designer"
    if any(word in role_lower for word in ["kostyme"]):
        return "costume_designer"
    if any(word in role_lower for word in ["produsent", "produksjon"]):
        return "producer"

    return "other"


def detect_medium(series_name: str, episode_data: dict) -> str:
    """Detect medium (tv/radio) from series name or episode data."""
    # Check if explicitly set in episode data
    if episode_data.get("medium"):
        return episode_data.get("medium")

    # Check series name for radio indicators
    radio_series = ["radioteatret", "radioteater"]
    if series_name.lower() in radio_series:
        return "radio"

    # Check NRK URL pattern
    nrk_url = episode_data.get("nrk_url", "")
    if "radio.nrk.no" in nrk_url:
        return "radio"

    return "tv"


def import_episode(cursor, conn, ep: dict, default_medium: str = "tv"):
    """Import a single episode."""
    prf_id = ep.get("prf_id")
    if not prf_id:
        return False

    # Get medium from episode data or use default
    medium = ep.get("medium", default_medium)

    # Insert episode
    cursor.execute("""
        INSERT OR REPLACE INTO episodes
        (prf_id, title, description, year, duration_seconds, image_url, nrk_url, source, medium)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        prf_id,
        ep.get("title", ""),
        ep.get("description", ""),
        ep.get("year"),
        ep.get("duration_seconds"),
        ep.get("image_url", ""),
        ep.get("nrk_url", ""),
        "nrk",
        medium,
    ))

    # Import contributors
    for contrib in ep.get("contributors", []):
        name = contrib.get("name")
        role = contrib.get("role", "")
        if not name:
            continue

        person_id = get_or_create_person(conn, name)
        mapped_role = map_role(role)

        cursor.execute("""
            INSERT OR IGNORE INTO episode_persons
            (episode_id, person_id, role)
            VALUES (?, ?, ?)
        """, (prf_id, person_id, mapped_role))

    return True


def import_episodes(conn: sqlite3.Connection, data_dir: Path):
    """Import episodes from harvested data."""
    cursor = conn.cursor()
    total_imported = 0

    raw_dir = data_dir / "raw"
    if not raw_dir.exists():
        print(f"Warning: {raw_dir} does not exist")
        return

    # Import TV episodes from series directories (fjernsynsteatret, etc.)
    for series_dir in raw_dir.iterdir():
        if not series_dir.is_dir():
            continue

        # Skip the hoerespill directory - we handle it separately
        if series_dir.name == "hoerespill":
            continue

        episodes_file = series_dir / "episodes.json"
        if not episodes_file.exists():
            continue

        series_name = series_dir.name
        print(f"Importing TV episodes from {series_name}...")

        with open(episodes_file, "r", encoding="utf-8") as f:
            episodes = json.load(f)

        count = 0
        for ep in episodes:
            # Detect medium from series name or episode data
            medium = detect_medium(series_name, ep)
            if import_episode(cursor, conn, ep, medium):
                count += 1

        print(f"  -> {count} episodes")
        total_imported += count

    # Import radio episodes from hoerespill directory
    hoerespill_file = raw_dir / "hoerespill" / "all_episodes.json"
    if hoerespill_file.exists():
        print(f"Importing radio episodes from hoerespill...")

        with open(hoerespill_file, "r", encoding="utf-8") as f:
            episodes = json.load(f)

        count = 0
        for ep in episodes:
            if import_episode(cursor, conn, ep, "radio"):
                count += 1

        print(f"  -> {count} radio episodes")
        total_imported += count

    conn.commit()
    print(f"Total imported: {total_imported} episodes")


def add_default_tags(conn: sqlite3.Connection):
    """Add some default tags."""
    cursor = conn.cursor()

    default_tags = [
        ("child_friendly", "Barnevennlig", "#4CAF50"),
        ("classic", "Klassiker", "#9C27B0"),
        ("comedy", "Komedie", "#FF9800"),
        ("drama", "Drama", "#2196F3"),
        ("ibsen", "Ibsen", "#607D8B"),
        ("holberg", "Holberg", "#795548"),
        ("norwegian", "Norsk", "#F44336"),
        ("international", "Internasjonal", "#3F51B5"),
    ]

    for name, display, color in default_tags:
        cursor.execute("""
            INSERT OR IGNORE INTO tags (name, display_name, color)
            VALUES (?, ?, ?)
        """, (name, display, color))

    conn.commit()


def build_database(data_dir: Path, db_path: Path):
    """Build the complete database."""
    print(f"\n{'='*60}")
    print(f"Building database: {db_path}")
    print(f"Data directory: {data_dir}")
    print(f"{'='*60}\n")

    # Remove existing database
    if db_path.exists():
        db_path.unlink()
        print(f"Removed existing database")

    # Create new database
    conn = sqlite3.connect(db_path)

    print("Creating schema...")
    conn.executescript(SCHEMA)

    print("Importing episodes...")
    import_episodes(conn, data_dir)

    print("Adding default tags...")
    add_default_tags(conn)

    # Add metadata
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO metadata (key, value) VALUES (?, ?)",
        ("built_at", datetime.now().isoformat())
    )
    cursor.execute(
        "INSERT INTO metadata (key, value) VALUES (?, ?)",
        ("version", "1.0.0")
    )
    conn.commit()

    # Get stats
    cursor.execute("SELECT COUNT(*) FROM episodes")
    ep_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM persons")
    person_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM episode_persons")
    ep_person_count = cursor.fetchone()[0]

    print(f"\n{'='*60}")
    print(f"Database built successfully!")
    print(f"  Episodes: {ep_count}")
    print(f"  Persons: {person_count}")
    print(f"  Episode-Person relations: {ep_person_count}")
    print(f"  Output: {db_path}")
    print(f"{'='*60}\n")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Build SQLite database")
    parser.add_argument(
        "--input",
        default="data",
        help="Data directory (default: data)",
    )
    parser.add_argument(
        "--output",
        default="data/kulturperler.db",
        help="Output database path (default: data/kulturperler.db)",
    )

    args = parser.parse_args()

    script_dir = Path(__file__).parent.parent
    data_dir = script_dir / args.input
    db_path = script_dir / args.output

    build_database(data_dir, db_path)


if __name__ == "__main__":
    main()
