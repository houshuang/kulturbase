# Kulturperler - Project Guide

> **⚠️ STOP: YAML is the source of truth. NEVER modify SQLite directly.**
>
> Edit files in `data/*.yaml` → run `python3 scripts/build_database.py`
>
> The SQLite database is a compiled artifact that gets rebuilt from YAML.

A browsable archive of Norwegian performing arts recordings, primarily NRK Fjernsynsteatret.

## Architecture Overview

**YAML files are the source of truth.** The SQLite database is a compiled artifact.

```
data/                          # SOURCE OF TRUTH - tracked in git
├── plays/                     # 863 play files
│   └── {id}.yaml
├── persons/                   # 3,173 person files
│   └── {id}.yaml
├── episodes/                  # 2,360 episode files (credits embedded)
│   └── {prf_id}.yaml
├── performances/              # 880 performance files (credits embedded)
│   └── {id}.yaml
├── nrk_about_programs/        # 403 program files
│   └── {id}.yaml
├── tags.yaml                  # All tags
├── external_resources.yaml    # External links/resources
└── metadata.yaml

static/kulturperler.db         # COMPILED - gitignored, rebuilt from data/
```

## Critical Rules

### DO
- Edit YAML files in `data/` to change data
- Run `python3 scripts/validate_data.py` before committing
- Run `python3 scripts/build_database.py` after changes to rebuild the database
- Use `python3 scripts/query.py` for quick lookups
- Review git diffs to see exactly what changed

### DO NOT
- **NEVER** modify `static/kulturperler.db` directly with SQL
- **NEVER** write enrichment scripts that update SQLite directly
- **NEVER** delete or rename YAML files without checking references first

### Why This Matters
Previous data loss occurred because SQLite was modified directly. With YAML files:
- Every change is visible in git diffs
- Data can be reviewed before committing
- Recovery is trivial (git revert)
- Validation catches broken references

## Data Model - Single Source of Truth

Each piece of information should live in exactly ONE place to prevent drift:

| Data | Source of Truth | NOT here |
|------|-----------------|----------|
| **Composers** | `plays/{id}.yaml` → `composers` array | ~~performance/episode credits~~ |
| **Playwright** | `plays/{id}.yaml` → `playwright_id` | ~~performance/episode credits~~ |
| **Librettist** | `plays/{id}.yaml` → `librettist_id` | ~~performance/episode credits~~ |
| **Director** | `performances/{id}.yaml` → credits | (per-production) |
| **Actors** | `performances/{id}.yaml` → credits | (per-production) |
| **Conductor** | `performances/{id}.yaml` → credits | (per-production) |

### Key Principles

1. **Work-level attributes** (playwright, composer, librettist) belong on the WORK, not on performances
2. **Production-level credits** (director, actors, conductor) belong on the PERFORMANCE
3. **Never duplicate** - if a composer is on the work, don't also add them as a credit on performances
4. **Multiple composers** - use the `composers` array on works, not combined person names like "Mozart, Beethoven"

## Reading Data

### Quick CLI queries
```bash
# Find persons by name
python3 scripts/query.py find-person "Ibsen"

# Find plays by title
python3 scripts/query.py find-play "Peer Gynt"

# Show detailed info
python3 scripts/query.py show-person 879
python3 scripts/query.py show-play 264
python3 scripts/query.py show-episode PRHO04000315

# Statistics
python3 scripts/query.py stats

# List plays needing enrichment
python3 scripts/query.py list-plays --no-playwright
python3 scripts/query.py list-plays --no-synopsis
```

### Complex queries (use SQLite)
```bash
# Rebuild database first if needed
python3 scripts/build_database.py

# Then query
sqlite3 static/kulturperler.db "SELECT id, title FROM plays WHERE playwright_id IS NULL"
```

### Reading YAML files directly
```bash
# View a specific entity
cat data/plays/264.yaml
cat data/persons/879.yaml

# Search across files
grep -r "Henrik Ibsen" data/persons/
grep -l "playwright_id: 879" data/plays/
```

## Modifying Data

### Edit a single field
Edit the YAML file directly:
```yaml
# data/plays/264.yaml
id: 264
title: Peer Gynt
playwright_id: 879        # <- add or change this
year_written: 1867        # <- add or change this
synopsis: |               # <- add multi-line text
  Peer Gynt er et dramatisk dikt...
```

### Add a new person
Create `data/persons/{next_id}.yaml`:
```yaml
id: 3213                  # Use next available ID
name: "New Person Name"
normalized_name: "new person name"
birth_year: 1900
death_year: 1980
bio: |
  Biography text here...
wikipedia_url: https://no.wikipedia.org/wiki/...
```

### Add a new play
Create `data/plays/{next_id}.yaml`:
```yaml
id: 864                   # Use next available ID
title: "Play Title"
original_title: "Original Title"
playwright_id: 879        # Reference to existing person
year_written: 1900
synopsis: |
  Synopsis text...
```

### Link a play to a playwright
Edit `data/plays/{id}.yaml` and add/update the `playwright_id` field:
```yaml
playwright_id: 879        # ID of the person
```

### Add composers to a work
Edit `data/plays/{id}.yaml` and add the `composers` array:
```yaml
composers:
  - person_id: 3252    # Wolfgang Amadeus Mozart
    role: composer
  - person_id: 3456    # If there's an arranger
    role: arranger
```

### Add production credits
Edit `data/performances/{id}.yaml` (NOT episodes) and add to the credits list:
```yaml
credits:
  - person_id: 123
    role: director
  - person_id: 456
    role: actor
    character_name: "Character Name"
  - person_id: 789
    role: conductor
```

**Remember:** Composer/playwright/librettist go on the WORK, not on performance credits.

## Validation

**Always validate before committing:**
```bash
python3 scripts/validate_data.py
```

This checks:
- Required fields (id, title, name, prf_id)
- All cross-references (playwright_id, person_id, play_id, etc.)
- Duplicate IDs

If validation fails, fix the issues before committing.

## Building the Database

After modifying YAML files:
```bash
python3 scripts/build_database.py
```

This:
1. Reads all YAML files
2. Creates fresh SQLite database
3. Inserts all data with proper relationships
4. Creates all indices
5. Sets up FTS5 search

The frontend uses this compiled database.

## Writing Enrichment Scripts

New enrichment scripts should:
1. Read YAML files from `data/`
2. Fetch/compute new data
3. Update YAML files
4. Let the user review changes in git before committing

Example pattern:
```python
import yaml
from pathlib import Path

DATA_DIR = Path('data')

def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)

def save_yaml(path, data):
    with open(path, 'w') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

# Load, modify, save
for play_file in (DATA_DIR / 'plays').glob('*.yaml'):
    play = load_yaml(play_file)

    if not play.get('synopsis'):
        # Fetch synopsis from somewhere
        synopsis = fetch_synopsis(play['title'])
        if synopsis:
            play['synopsis'] = synopsis
            save_yaml(play_file, play)
            print(f"Updated {play_file.name}")
```

## File Format Reference

### plays/{id}.yaml (works)
```yaml
id: 264                           # Required, unique
title: "Peer Gynt"                # Required
original_title: "Peer Gynt"       # Optional
playwright_id: 879                # Optional, references persons (for drama)
librettist_id: 123                # Optional, references persons (for opera)
year_written: 1867                # Optional
work_type: "teaterstykke"         # Optional (teaterstykke/opera/symphony/concerto/etc)
category: "teater"                # Optional (teater/opera/konsert/dramaserie)
synopsis: |                       # Optional, multi-line
  Synopsis text...
wikidata_id: "Q746566"            # Optional
sceneweb_id: 12345                # Optional
sceneweb_url: "https://..."       # Optional
wikipedia_url: "https://..."      # Optional

# For works with composers (music/opera/etc):
composers:                        # Optional, for musical works
  - person_id: 3252               # Required within composer entry
    role: composer                # composer/arranger/orchestrator/lyricist/adapter
  - person_id: 3456
    role: arranger
```

**Composer roles:**
- `composer` - wrote the original music
- `arranger` - arranged existing music
- `orchestrator` - orchestrated the work
- `lyricist` - wrote the lyrics/text
- `adapter` - adapted/revised the work

### persons/{id}.yaml
```yaml
id: 879                           # Required, unique
name: "Henrik Ibsen"              # Required
normalized_name: "henrik ibsen"   # Optional, lowercase for search
birth_year: 1828                  # Optional
death_year: 1906                  # Optional
nationality: "Norwegian"          # Optional
bio: |                            # Optional, multi-line
  Biography text...
wikidata_id: "Q36661"             # Optional
sceneweb_id: 1234                 # Optional
sceneweb_url: "https://..."       # Optional
wikipedia_url: "https://..."      # Optional
```

### episodes/{prf_id}.yaml
```yaml
prf_id: "PRHO04000315"            # Required, unique (NRK ID)
title: "Episode Title"            # Required
description: |                    # Optional
  Description text...
year: 1975                        # Optional
duration_seconds: 3600            # Optional
image_url: "https://..."          # Optional
nrk_url: "https://tv.nrk.no/..."  # Optional
play_id: 264                      # Optional, references plays
performance_id: 100               # Optional, references performances
source: "nrk"                     # Optional (nrk/archive)
medium: "tv"                      # Optional (tv/radio)
series_id: "MSPO..."              # Optional

credits:                          # Optional, production credits only
  - person_id: 123
    role: "director"              # director/actor/producer/other (NOT composer/playwright)
    character_name: "Role Name"   # Optional, for actors
```

**Valid credit roles for episodes/performances:**
- `director` - directed the production
- `actor` - performed in the production
- `producer` - produced the production
- `conductor` - conducted (for music)
- `soloist` - solo performer
- `set_designer`, `costume_designer` - design roles
- `other` - other production roles

**NOT valid** (these belong on the work, not credits):
- ~~composer~~ → use `composers` array on the work
- ~~playwright~~ → use `playwright_id` on the work
- ~~librettist~~ → use `librettist_id` on the work

### performances/{id}.yaml
```yaml
id: 100                           # Required, unique
work_id: 264                      # Required, references plays
source: "nrk"                     # Optional (nrk/youtube/archive/etc)
year: 1975                        # Optional
title: "Performance Title"        # Optional (defaults to work title)
description: |                    # Optional
  Description...
venue: "NRK Studio"               # Optional
total_duration: 7200              # Optional (seconds)
image_url: "https://..."          # Optional
medium: "tv"                      # Optional (tv/radio/stream)
series_id: "MSPO..."              # Optional

credits:                          # Optional, production credits only
  - person_id: 123
    role: "director"              # See valid roles above
  - person_id: 456
    role: "actor"
    character_name: "Hamlet"      # For actors only

institutions:                     # Optional, performing groups
  - institution_id: 7
    role: "orchestra"
```

## Data Statistics

Current counts (December 2024):
- 2,024 works (plays/{id}.yaml) with 1,020 composer links
- 4,371 persons
- 3,666 episodes
- 2,134 performances
- 507 NRK about programs
- 825 external resources

## Frontend

### Tech Stack
- SvelteKit with TypeScript
- sql.js (SQLite in WebAssembly)
- Static site generation

### Development
```bash
npm run dev          # http://localhost:4242
npm run build        # Output: build/
```

### Key Files
- `src/routes/+page.svelte` - Browse page
- `src/routes/play/[id]/+page.svelte` - Play detail
- `src/routes/person/[id]/+page.svelte` - Person detail
- `src/routes/episode/[id]/+page.svelte` - Episode detail
- `src/lib/db.ts` - Database queries
- `src/lib/types.ts` - TypeScript interfaces

## Data Sources

- **NRK TV API** - Episode metadata, images
- **Sceneweb** - Play/playwright metadata
- **Norwegian Wikipedia** - Author bios, images
- **Wikidata** - Structured data (birth/death years)
- **Bokselskap** - Full text links for public domain works

## External APIs

### NRK API (psapi.nrk.no)
No authentication required. Base URL: `https://psapi.nrk.no`

```python
import requests

# Search for content
r = requests.get('https://psapi.nrk.no/search', params={'q': 'opera', 'pageSize': 50})

# Get TV series info
r = requests.get('https://psapi.nrk.no/tv/catalog/series/opera-og-operetter')

# Get season episodes
r = requests.get('https://psapi.nrk.no/tv/catalog/series/opera-og-operetter/seasons/1985')

# Get program details (works for both TV and radio)
r = requests.get('https://psapi.nrk.no/programs/FMUS00000784')

# Radio series
r = requests.get('https://psapi.nrk.no/radio/catalog/series/radioteatret')
r = requests.get('https://psapi.nrk.no/radio/catalog/series/radioteatret/seasons/1/episodes')
```

**Key fields:**
- `usageRights.to.date` - Expiry date (ISO8601) or `usageRights.availableTo` (Unix ms)
- `duration` - ISO8601 format ("PT1H30M45S") or `durationInSeconds`
- `contributors` - Array with `name` and `role`
- `sourceMedium` - 1=TV, 2=Radio

### Gemini 3 Flash API
**Always use Gemini 3 Flash** for external AI tasks. It's the latest model with best performance.

API key in `.env`: `GEMINI_KEY=...`

**Model details:**
- Model ID: `gemini-3-flash-preview`
- Pricing: $0.50/1M input tokens, $3/1M output tokens
- Context window: 1M tokens input, 64k tokens output
- Features: Thinking levels, context caching (90% cost reduction)

```python
import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('GEMINI_KEY')

# Standard generation with Gemini 3 Flash
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={API_KEY}"
payload = {
    "contents": [{"parts": [{"text": "Your prompt here"}]}],
    "generationConfig": {"temperature": 0.1}
}
r = requests.post(url, json=payload)
text = r.json()['candidates'][0]['content']['parts'][0]['text']

# With thinking level (for complex reasoning tasks)
payload = {
    "contents": [{"parts": [{"text": "Complex analysis prompt"}]}],
    "generationConfig": {
        "temperature": 0.1,
        "thinking_level": "medium"  # minimal, low, medium, or high
    }
}

# With Google Search grounding (for web searches)
payload = {
    "contents": [{"parts": [{"text": "Search YouTube for Norwegian opera"}]}],
    "tools": [{"google_search": {}}],
    "generationConfig": {"temperature": 0.1}
}
r = requests.post(url, json=payload)
```

**Note:** The Python SDK (`google.generativeai`) doesn't support `google_search` tool. Use REST API directly for web search grounding.

### Archive.org API
No authentication required.

```python
import requests

# Search
r = requests.get('https://archive.org/advancedsearch.php', params={
    'q': 'norwegian opera',
    'fl[]': ['identifier', 'title', 'description', 'creator', 'date'],
    'output': 'json',
    'rows': 50
})
items = r.json()['response']['docs']

# Get item metadata
r = requests.get('https://archive.org/metadata/ITEM_IDENTIFIER')
```

### YouTube via yt-dlp
Use `yt-dlp` (installed at `/usr/local/bin/yt-dlp`) for fetching YouTube channel videos.
WebFetch cannot access youtube.com, and YouTube RSS feeds are disabled.

```bash
# List all videos from a channel (fast, metadata only)
yt-dlp --flat-playlist --print "%(id)s|%(title)s|%(duration)s" \
  "https://www.youtube.com/channel/CHANNEL_ID/videos"

# Or using handle
yt-dlp --flat-playlist --print "%(id)s|%(title)s|%(duration)s" \
  "https://www.youtube.com/@ChannelHandle/videos"

# Get full metadata as JSON (slower, one request per video)
yt-dlp --no-download -j "https://www.youtube.com/watch?v=VIDEO_ID"

# Batch fetch multiple videos
yt-dlp --no-download -j URL1 URL2 URL3...
```

**Python pattern for fetching channel videos:**
```python
import subprocess
import json

# Fast: Get all video IDs and basic info
result = subprocess.run([
    'yt-dlp', '--flat-playlist', '-j',
    'https://www.youtube.com/@ChannelHandle/videos'
], capture_output=True, text=True, timeout=120)

videos = [json.loads(line) for line in result.stdout.strip().split('\n') if line]

# Slower: Get full metadata for specific videos (in batches)
urls = [f"https://www.youtube.com/watch?v={v['id']}" for v in videos]
result = subprocess.run(
    ['yt-dlp', '--no-download', '-j'] + urls[:10],  # batch of 10
    capture_output=True, text=True, timeout=120
)
detailed = [json.loads(line) for line in result.stdout.strip().split('\n') if line]
```

**Key fields from yt-dlp JSON:**
- `id`: Video ID (11 chars)
- `title`: Full title
- `description`: Full description (not truncated)
- `duration`: Duration in seconds
- `upload_date`: YYYYMMDD format
- `thumbnail`: Thumbnail URL
- `channel`: Channel name

**Classifying videos with Gemini:**
Use Gemini to classify videos as CONCERT vs NOT_CONCERT (interviews, podcasts, etc.):
```python
payload = {
    "contents": [{"parts": [{"text": f"""Classify each video as CONCERT or NOT_CONCERT.
CONCERT = musical performance recording
NOT_CONCERT = interviews, podcasts, behind-the-scenes, announcements

Video list (id|title|duration):
{video_list}

Reply with: video_id|CONCERT or video_id|NOT_CONCERT"""}]}],
    "generationConfig": {"temperature": 0.1}
}
```

## Classical Music Discovery Scripts

Scripts in `scripts/` for discovering classical content:

| Script | Purpose |
|--------|---------|
| `discover_classical_series.py` | Find NRK series with classical content |
| `extract_classical_episodes.py` | Extract episode metadata from series |
| `classify_with_gemini.py` | Classify episodes as opera/ballet/symphony |
| `link_multipart.py` | Group multi-part performances |
| `link_to_plays.py` | Link performances to existing plays |
| `generate_classical_reports.py` | Generate text reports |
| `search_external_platforms.py` | Search Archive.org (YouTube/Vimeo failed) |
| `search_youtube_gemini.py` | Search YouTube via Gemini + Google Search |

Output files go to `output/` (gitignored). See `output/README_external_search.md` for details.

### Running the full pipeline
```bash
# NRK classical content discovery
python3 scripts/discover_classical_series.py
python3 scripts/extract_classical_episodes.py
python3 scripts/classify_with_gemini.py
python3 scripts/link_multipart.py
python3 scripts/link_to_plays.py
python3 scripts/generate_classical_reports.py

# External platform search
python3 scripts/search_external_platforms.py      # Archive.org
python3 scripts/search_youtube_gemini.py          # YouTube via Gemini
```

## Git Conventions

- Branch prefix: `sh/`
- Always run validation before committing data changes
- Review diffs carefully - you can now see exactly what data changed

## Data Enrichment Guidelines

When adding new data, always try to enrich it:

### New Persons (composers, playwrights, etc.)
- **Wikipedia**: Fetch bio (short summary), birth/death years, Wikipedia URL
- **Prefer Norwegian Wikipedia** when available (`no.wikipedia.org`)
- **Images**: Not fetched automatically (copyright concerns)
- Use the Wikipedia REST API with proper User-Agent header:
  ```python
  headers = {'User-Agent': 'Kulturperler/1.0 (https://kulturbase.no)'}
  url = f'https://no.wikipedia.org/api/rest_v1/page/summary/{name}'
  ```

### New Works (plays, operas, symphonies)
- **Synopsis**: Fetch summary from Wikipedia if available
- **Wikipedia URL**: Link to the work's Wikipedia page
- **Wikidata ID**: For structured data linking
- **Year written**: When the work was created

### New NRK Programs (episodes, performances)
- **Images**: Always try to fetch from NRK using their image URL pattern:
  ```
  https://gfx.nrk.no/{image_id}/320
  ```
- **Duration**: Fetch from NRK API
- **Description**: Use NRK's description

### Enrichment Workflow
```bash
# After adding new entries, enrich them:
python3 scripts/enrich_persons.py --new     # Enrich persons without bio
python3 scripts/enrich_works.py --new       # Enrich works without synopsis
```

## Workflow Summary

```bash
# 1. Make changes to YAML files in data/

# 2. Validate
python3 scripts/validate_data.py

# 3. Review changes
git diff data/

# 4. Rebuild database
python3 scripts/build_database.py

# 5. Test frontend
npm run dev

# 6. Commit
git add data/
git commit -m "Add synopsis for Peer Gynt"
```
