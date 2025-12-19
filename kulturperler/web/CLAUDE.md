# Kulturperler - Project Guide

A browsable archive of Norwegian performing arts recordings, primarily NRK Fjernsynsteatret.

## Database

### Location
```
static/kulturperler.db  (SQLite database)
```

### Accessing the Database
```bash
sqlite3 static/kulturperler.db
```

### Core Tables

**plays** - Works/plays
- `id`, `title`, `original_title`, `playwright_id`, `year_written`, `synopsis`
- `sceneweb_url`, `wikipedia_url`, `wikidata_id`

**persons** - Authors, directors, actors
- `id`, `name`, `birth_year`, `death_year`, `bio`, `image_url`
- `sceneweb_url`, `wikipedia_url`, `wikidata_id`

**episodes** - Individual recordings (NRK episodes)
- `prf_id` (NRK ID), `title`, `description`, `year`, `duration_seconds`
- `play_id` (link to plays), `image_url`, `nrk_url`

**episode_persons** - Who worked on which episode
- `episode_id`, `person_id`, `role` (director/actor/playwright/etc.), `character_name`

**performances** - Production instances of plays
- `id`, `work_id`, `year`, `title`, `description`, `venue`

**play_external_links** - External streaming/reading links
- `play_id`, `url`, `title`, `type` (bokselskap/streaming), `access_note`

**nrk_about_programs** - NRK documentaries about playwrights
- `id`, `person_id`, `title`, `description`, `duration_seconds`, `nrk_url`

### Common Queries

```sql
-- Plays without playwright
SELECT id, title FROM plays WHERE playwright_id IS NULL;

-- Plays with Sceneweb URLs but missing data
SELECT id, title, sceneweb_url FROM plays
WHERE sceneweb_url IS NOT NULL AND (playwright_id IS NULL OR synopsis IS NULL);

-- Find a person by name
SELECT * FROM persons WHERE name LIKE '%Ibsen%';

-- Link a play to a playwright
UPDATE plays SET playwright_id = (SELECT id FROM persons WHERE name = 'Henrik Ibsen')
WHERE title LIKE '%Peer Gynt%';

-- Add a synopsis
UPDATE plays SET synopsis = 'Your synopsis here' WHERE id = 123;

-- Check enrichment status
SELECT COUNT(*) as total,
       COUNT(playwright_id) as with_playwright,
       COUNT(synopsis) as with_synopsis,
       COUNT(original_title) as with_original_title
FROM plays;
```

## Enrichment Scripts

Located in `scripts/`:

- **enrich_playwrights.py** - Fetch playwright info, year_written, original_title from Sceneweb
  - Uses cache: `static/sceneweb_cache.json`
  - Run: `python3 scripts/enrich_playwrights.py`

- **enrich_wikipedia_bios.py** - Fetch author bios and images from Norwegian Wikipedia
  - Run: `python3 scripts/enrich_wikipedia_bios.py`

- **enrich_from_wikidata.py** - Add playwright data (birth/death years, Wikidata IDs)
  - Contains manual mappings for well-known plays → playwrights

- **enrich_play_synopsis.py** - Add play synopses (manual data + Wikipedia)
  - Contains KNOWN_SYNOPSES dict for common plays

- **enrich_nrk_about.py** - Fetch NRK programs about playwrights (documentaries, etc.)

## Frontend

### Tech Stack
- SvelteKit with TypeScript
- sql.js (SQLite compiled to WebAssembly for browser)
- Static site generation

### Running Dev Server
```bash
npm run dev
# Runs on http://localhost:4242
```

### Key Files
- `src/routes/+page.svelte` - Browse page (main listing)
- `src/routes/play/[id]/+page.svelte` - Play detail page
- `src/routes/person/[id]/+page.svelte` - Author/person detail page
- `src/routes/episode/[id]/+page.svelte` - Episode detail page
- `src/lib/db.ts` - Database query functions
- `src/lib/types.ts` - TypeScript interfaces

### Building
```bash
npm run build
# Output: build/
```

## Data Sources

- **NRK TV API** - Episode metadata, images
- **Sceneweb** - Play/playwright metadata, original titles
- **Norwegian Wikipedia** - Author bios, images
- **Wikidata** - Structured data (birth/death years, IDs)
- **Bokselskap** - Full text links for public domain works

## Common Tasks

### Add a new playwright
```sql
INSERT INTO persons (name, normalized_name, birth_year, death_year)
VALUES ('Name Here', 'name here', 1900, 1980);
```

### Link plays to playwright
```sql
UPDATE plays SET playwright_id = 123 WHERE title LIKE '%Play Title%';
```

### Add external link (Bokselskap/streaming)
```sql
INSERT INTO play_external_links (play_id, url, title, type, access_note)
VALUES (42, 'https://bokselskap.no/...', 'Bokselskap.no', 'bokselskap', NULL);
```

### Add Applaus Scene link
```sql
INSERT INTO play_external_links (play_id, url, title, type, access_note)
VALUES (42, 'https://applausscene.no/...', 'Applaus Scene', 'streaming', 'Kun for skoler');
```

## Git Branch Naming
Use prefix `sh/` when creating branches.
