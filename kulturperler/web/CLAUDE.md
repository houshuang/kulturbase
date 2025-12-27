# Kulturperler - Project Guide

> **⚠️ STOP: YAML is the source of truth. NEVER modify SQLite directly.**
>
> Edit files in `data/*.yaml` → run `python3 scripts/build_database.py`
>
> The SQLite database is a compiled artifact that gets rebuilt from YAML.

A browsable archive of Nordic performing arts recordings, including NRK Fjernsynsteatret, Sveriges Radio Drama, and other Nordic sources.

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
language: "no"                    # Optional, defaults to "no" (see Language Codes below)
playwright_id: 879                # Optional, references persons (for drama)
librettist_id: 123                # Optional, references persons (for opera)
year_written: 1867                # Optional
work_type: "teaterstykke"         # Optional (see work_type values below)
category: "teater"                # Optional (teater/opera/konsert/dramaserie/film/kulturprogram)
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

**Category values:**
- `teater` - Theatre/drama (plays, TV theatre)
- `opera` - Opera and operetta
- `konsert` - Classical concerts
- `dramaserie` - Drama series (multiple episodes)
- `film` - Standalone films (not theatre adaptations)
- `kulturprogram` - Cultural/literature programs

**Work type values:**
- `teaterstykke` - Theatre play
- `radioteater` - Radio theatre/hörspel
- `barneteater` - Children's theatre
- `film` - Feature film
- `kortfilm` - Short film
- `dokumentär` - Documentary
- `opera` - Opera
- `operetta` - Operetta
- `symphony` - Symphony
- `concerto` - Concerto
- `horespill` - Radio play (Norwegian)
- `dramaserie` - Drama series

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
prf_id: "PRHO04000315"            # Required, unique (NRK ID or SR_12345 for Sveriges Radio)
title: "Episode Title"            # Required
description: |                    # Optional
  Description text...
year: 1975                        # Optional
duration_seconds: 3600            # Optional
image_url: "https://..."          # Optional
nrk_url: "https://tv.nrk.no/..."  # Optional
sr_url: "https://sverigesradio.se/..." # Optional, for Sveriges Radio
play_id: 264                      # Optional, references plays
performance_id: 100               # Optional, references performances
source: "nrk"                     # Optional (nrk/sr/archive/yle/dr_bonanza)
language: "no"                    # Optional, defaults to "no" (see Language Codes below)
medium: "tv"                      # Optional (tv/radio/stream)
series_id: "MSPO..."              # Optional
about_person_id: 879              # Optional, for kulturprogram episodes about an author
episode_number: 5                 # Optional, for sorting within a performance

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
source: "nrk"                     # Optional (nrk/sr/youtube/archive/yle/dr_bonanza)
language: "no"                    # Optional, defaults to "no" (see Language Codes below)
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

## Language Codes

The database supports content in multiple Nordic languages using ISO 639-1 codes:

| Code | Language | Primary Source |
|------|----------|----------------|
| `no` | Norwegian | NRK (default) |
| `sv` | Swedish | Sveriges Radio |
| `da` | Danish | DR Bonanza (Archive.org) |
| `fi` | Finnish | Yle Arenan (Swedish content only) |

**Important:**
- Norwegian content (`no`) is the default - don't need to specify explicitly
- Only set `language` field when importing non-Norwegian content
- Works in different languages can link to the same playwright (e.g., Ibsen's "Et dukkehjem" in Norwegian and Swedish performances both link to the same work and playwright)
- The frontend has language filters on browse pages when multiple languages exist

**Cross-language work linking:**
When the same play exists in multiple languages (e.g., Strindberg in Swedish and Norwegian), they should share the same work entry. The `language` field on the **performance** indicates which language that specific production is in.

## Importing from External Sources

### Source Codes
| Source | Code | ID Format | URL Field | Example |
|--------|------|-----------|-----------|---------|
| NRK | `nrk` | NRK program ID | `nrk_url` | `PRHO04000315` |
| Sveriges Radio | `sr` | `SR_{episode_id}` | `sr_url` | `SR_2501552` |
| Archive.org | `archive` | Item identifier | `archive_url` | `archive_item_id` |
| YouTube | `youtube` | `YT_{video_id}` | `youtube_url` | `YT_dQw4w9WgXcQ` |
| DR Bonanza | `dr_bonanza` | `DR_{identifier}` | `dr_url` | `DR_12345` |
| Yle | `yle` | `YLE_{program_id}` | `yle_url` | `YLE_12345` |

**URL Field Mapping:** The database stores all source URLs in the `nrk_url` column. When adding a new source:
1. Add the source-specific URL field to YAML files (e.g., `yle_url` for Yle content)
2. Update `scripts/build_database.py` to include the new field in the URL fallback chain:
   ```python
   source_url = e.get('nrk_url') or e.get('sr_url') or e.get('new_source_url')
   ```
3. Update `src/routes/opptak/[id]/+page.svelte` to show correct button text for the new source

### Sveriges Radio Import

Sveriges Radio has a public API with Nordic radio theatre. Use `scripts/import_sr_drama.py`.

**Available programs:**
| Program ID | Name | Content |
|------------|------|---------|
| 4453 | Dramaklassiker | Classic radio theatre (Strindberg, Ibsen, etc.) |
| 3171 | Drama för unga | Children's drama |
| 4976 | Sveriges Radio Drama | Contemporary drama |
| 6605 | Scenen | Shakespeare adaptations |
| 4947 | P3 Serie | Crime/thriller series |

**API example:**
```python
import requests

# Fetch all episodes for a program
url = 'https://api.sr.se/api/v2/episodes/index'
params = {'programid': 4453, 'format': 'json', 'pagination': 'false'}
r = requests.get(url, params=params)
episodes = r.json().get('episodes', [])
```

**Import workflow:**
```bash
# Import all SR drama programs
python3 scripts/import_sr_drama.py

# Import specific program only
python3 scripts/import_sr_drama.py --program 4453

# Dry run (see what would be imported)
python3 scripts/import_sr_drama.py --dry-run
```

**After import, enrich with playwright info:**
```bash
python3 scripts/enrich_swedish_works.py --known-only
```

### Yle (Finnish-Swedish) Import

Yle (Finnish Broadcasting Company) produces Swedish-language radio theatre at Svenska Yle. Use `scripts/import_yle_radioteater.py`.

**Note:** Yle's API was disabled in May 2021. Content must be discovered via web search and pages scraped individually.

**Notable content:**
| Title | Year | Author | Notes |
|-------|------|--------|-------|
| Medeas dotter | 2023 | Are Nikkinen | Prix Italia 2024 finalist |
| Lyssnar på killar | 2019 | Ida Kronholm | 105 min audio drama |
| Nils Holgerssons underbara resa | 2020 | Selma Lagerlöf | 17-episode series by Teater Fabel |
| Fjädern | 1990 | Erik Ohls | Prix Italia winner |
| När göken gol vid Seine | 1993 | Janina Jansson | Prix Futura winner |
| Inbjudan till resa | 1998 | Petri Salin | Nordic Radio Play Prize 2000 |
| Tre vita skjortor | 1960 | Walentin Chorell | Classic Finnish-Swedish drama |

**Episode ID format:** `YLE_{program_name}_{number}` (e.g., `YLE_MEDEAS_1`, `YLE_NILS_03`)

**Availability:** Most older content is geo-restricted to Finland or has expired. Check `arenan.yle.fi` for current availability.

**Manual discovery workflow:**
```bash
# Search for content
# Use web search: site:arenan.yle.fi "Radioteatern" OR "hörspel"

# Fetch page details with WebFetch
# Extract: title, author, director, cast, year, duration

# Add to import script and run
python3 scripts/import_yle_radioteater.py
```

### Filtering Meta-Content

When importing, **exclude meta-content** that isn't actual performances:
- Trailers (typically < 2 minutes)
- Interviews about productions
- Behind-the-scenes content
- "Eftersnack" (aftershow discussions)
- Memorial/tribute programs

**Patterns to filter out:**
```python
SKIP_PATTERNS = [
    'trailer',
    'berättar om',      # "tells about" (interviews)
    'minns',            # "remembers" (memorials)
    'eftersnack',       # aftershow
    'intervju',         # interview
]

def is_meta_content(title):
    lower = title.lower()
    return any(p in lower for p in SKIP_PATTERNS)
```

**If meta-content gets imported by mistake**, remove the work, performance, and episode YAML files.

### Work Linking Strategy

When importing, try to link to existing works rather than creating duplicates:

1. **Exact title match** - Same title, same playwright
2. **Author match** - Parse "Title av Author" pattern from episode titles
3. **Known works mapping** - Maintain a dict of title → author for classics
4. **Create new** - Only if no match found

**Example title parsing (Swedish):**
```python
import re

def parse_title_and_author(title):
    """Parse 'Kronbruden av August Strindberg' -> ('Kronbruden', 'August Strindberg')"""
    match = re.match(r'^(.+?)\s+av\s+(.+?)$', title, re.IGNORECASE)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return title, None
```

## Data Statistics

Current counts (December 2024):
- 2,500+ works with ~1,000 composer links
- 4,600+ persons
- 5,300+ episodes:
  - ~4,000 Norwegian (NRK)
  - ~650 YouTube/external
  - ~340 Swedish (Sveriges Radio)
  - ~30 Finnish-Swedish (Yle)
- 2,500+ performances
- 530 NRK about programs
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

- **NRK TV API** - Norwegian episode metadata, images
- **Sveriges Radio API** - Swedish radio theatre (Dramaklassiker, Drama för unga, etc.)
- **Yle Arenan** - Finnish-Swedish radio theatre (Svenska Yle)
- **Sceneweb** - Play/playwright metadata
- **Norwegian Wikipedia** - Author bios, images
- **Swedish Wikipedia** - Swedish/Finnish-Swedish author/work info
- **Wikidata** - Structured data (birth/death years)
- **Bokselskap** - Full text links for public domain works
- **Archive.org** - DR Bonanza Danish content (torrent-only)

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

### Sveriges Radio API (api.sr.se)
No authentication required. Base URL: `https://api.sr.se/api/v2`
Documentation: https://api.sr.se/api/documentation/v2/

```python
import requests

# List all episodes for a program
r = requests.get('https://api.sr.se/api/v2/episodes/index', params={
    'programid': 4453,  # Dramaklassiker
    'format': 'json',
    'pagination': 'false'
})
episodes = r.json().get('episodes', [])

# Get single episode
r = requests.get('https://api.sr.se/api/v2/episodes/2501552', params={'format': 'json'})
episode = r.json().get('episode', {})
```

**Key fields:**
- `id` - Episode ID (use as `SR_{id}` for prf_id)
- `title` - Episode title
- `description` - Description
- `publishdateutc` - Publish date in `/Date(timestamp)/` format
- `imageurl` - Thumbnail URL
- `listenpodfile.duration` - Duration in seconds
- `listenpodfile.url` - Direct audio URL
- `url` - Web page URL

**Parsing SR date format:**
```python
import re
from datetime import datetime

def parse_sr_date(date_str):
    """Parse '/Date(1234567890000)/' to datetime."""
    match = re.search(r'/Date\((\d+)\)/', date_str or '')
    if match:
        return datetime.fromtimestamp(int(match.group(1)) / 1000)
    return None
```

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

## Kulturprogrammer (Cultural Programs)

The `kulturprogram` category contains literature/book programs like Bokprogrammet, Salongen, Leseforeningen, etc. These are handled differently from theater/opera content.

### Kulturprogrammer Page Requirements
The `/kulturprogrammer` page displays programs from the `performances` table where the associated `work` has `category = 'kulturprogram'`. To add a new series to this page:

1. **Create a work** in `data/plays/{id}.yaml`:
   ```yaml
   id: 2712
   title: Ukens lyriker
   category: kulturprogram
   work_type: lyrikk  # bokprogram/lyrikk/kulturmagasin/dokumentar
   synopsis: Fra NRKs arkiv henter vi opptak av kjente lyrikere.
   ```

2. **Create a performance** in `data/performances/{id}.yaml`:
   ```yaml
   id: 2950
   work_id: 2712
   title: Ukens lyriker
   source: nrk
   medium: tv
   year: 1995
   series_id: ukens-lyriker
   image_url: https://gfx.nrk.no/...
   ```

3. **Link episodes** to the performance by adding `performance_id: 2950` to each episode YAML file.

**Work types for kulturprogram:**
- `bokprogram` - Book/literature discussion programs
- `lyrikk` - Poetry programs
- `kulturmagasin` - Cultural magazine shows
- `dokumentar` - Documentary programs about culture/authors

### Structure
- **Works** with `category: kulturprogram` and `work_type: bokprogram` (or similar)
- **Performances** group episodes by program/series
- **Episodes** link to performances and optionally to authors via `about_person_id`

### Linking Episodes to Authors
Episodes discussing specific authors can be linked using `about_person_id`:
```yaml
# data/episodes/MKTF01002312.yaml
prf_id: MKTF01002312
title: møter Jan Roar Leikvoll
about_person_id: 1234  # Links to the author being discussed
performance_id: 2934
```

This enables "Programmer om [person]" sections on person pages showing all episodes about that author.

### Episode Numbering for Sorting
Episodes have an optional `episode_number` field for proper sorting within a performance:
```yaml
episode_number: 105  # Season 1, Episode 5
```

**Numbering conventions:**
- Simple series: Use 1, 2, 3, etc.
- Multi-season series: Use season*100 + episode (s01e05 → 105, s02e05 → 205)
- Bonus episodes: Use 999 or 9999

The frontend sorts by `episode_number ASC NULLS LAST, prf_id ASC`.

### Fetching NRK TV Series with Multiple Seasons
NRK TV series often have multiple seasons. To fetch all episodes:

```python
import requests

series_id = 'bokprogrammet'
base_url = 'https://psapi.nrk.no/tv/catalog/series'

# 1. Get series info to find available seasons
r = requests.get(f'{base_url}/{series_id}')
series = r.json()
seasons = series.get('_links', {}).get('seasons', [])

# 2. Fetch each season - episodes are embedded in the response
all_episodes = []
for season in seasons:
    season_name = season['name']  # e.g., "2010", "2011"
    r = requests.get(f'{base_url}/{series_id}/seasons/{season_name}')
    season_data = r.json()

    # Episodes are in _embedded.instalments (NOT a separate /episodes endpoint)
    episodes = season_data.get('_embedded', {}).get('instalments', [])
    all_episodes.extend(episodes)
    print(f"Season {season_name}: {len(episodes)} episodes")
```

**Important:** Episodes are embedded in the season response under `_embedded.instalments`, not at a separate `/episodes` endpoint.

### Generating Better Titles from Descriptions
Many older episodes have only date-based titles like "15. mars 2011". To generate better titles:

```python
from openai import OpenAI
import json

client = OpenAI()

# Batch episodes for efficiency (10-12 per request)
prompt = """For each episode below, generate a short Norwegian title (3-6 words) based on the description.
The title should capture the main topic or guest. Don't include dates.

1. [MKTF01001512] Description: Hovedgjest i kveldens program er krimforfatter Jørn Lier Horst...

Return JSON array: [{"prf_id": "...", "new_title": "..."}]
"""

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.3
)
```

**Tips:**
- Check if episodes have descriptions before processing (older programs often don't)
- NRK API `titles.subtitle` field sometimes has useful info, but often empty
- Process in batches of 10-12 for efficiency
- Use temperature 0.3 for consistent results

### Classifying Episodes by Author (for about_person_id)
Use OpenAI to identify which author an episode discusses:

```python
prompt = """For each episode, identify the PRIMARY author/person being discussed.
Match against this list of known persons:
- Henrik Ibsen (id: 879)
- Knut Hamsun (id: 1234)
...

Episode: "Bokprogrammet møter Jo Nesbø om hans nye krimroman"

Return: {"prf_id": "...", "person_id": 879, "person_name": "Jo Nesbø"}
Return null for person_id if no clear match or multiple authors discussed equally.
"""
```

**Important:** Use strict full-name matching only. Fuzzy matching causes errors (e.g., "Nils Collett Vogt" matching "Nils Vogt" who is a different person).

## Importing Programs from NRK Screenshots

When given screenshots of NRK TV program listings, follow this workflow:

### 1. Identify programs from screenshots
Programs typically fall into categories:
- **Theatre productions** - standalone plays (Lang dags ferd mot natt, Hypokonderen)
- **Kulturprogrammer series** - literature/culture shows (Lesekunst, Filmredaksjonen)
- **Portrait/documentary** - about authors/artists (Møte med Tarjei Vesaas)
- **About programs** - for author pages (Henrik Ibsen portrett)

### 2. Check what already exists
```bash
# Check for existing episodes
sqlite3 static/kulturperler.db "SELECT prf_id, title FROM episodes WHERE title LIKE '%search%';"

# Check for existing series
sqlite3 static/kulturperler.db "SELECT DISTINCT series_id FROM episodes WHERE series_id IS NOT NULL;" | grep "search"

# Check about programs
sqlite3 static/kulturperler.db "SELECT id, title FROM nrk_about_programs WHERE title LIKE '%search%';"
```

### 3. Search NRK API for programs
```python
import requests

# Search for programs
r = requests.get('https://psapi.nrk.no/search', params={'q': 'program name', 'pageSize': 10})
hits = r.json().get('hits', [])
for h in hits:
    hit = h.get('hit', {})
    print(f"{hit.get('id')} | {hit.get('title')} | {h.get('type')}")

# Get standalone program details
r = requests.get('https://psapi.nrk.no/programs/PRFID')
data = r.json()
# Fields: title, shortDescription, productionYear, duration, image.webImages

# Check if series exists
r = requests.get('https://psapi.nrk.no/tv/catalog/series/series-id')
```

### 4. Fetch series episodes
**Important:** Episodes are in `_embedded.instalments` (not a separate endpoint):
```python
# Get series with seasons
r = requests.get('https://psapi.nrk.no/tv/catalog/series/series-id')
seasons = r.json().get('_embedded', {}).get('seasons', [])

# Get episodes from each season
for season in seasons:
    season_name = season.get('_links', {}).get('self', {}).get('name')
    r2 = requests.get(f'https://psapi.nrk.no/tv/catalog/series/series-id/seasons/{season_name}')
    episodes = r2.json().get('_embedded', {}).get('instalments', [])
    # Note: some series use 'episodes' instead of 'instalments'
```

### 5. Import workflow
For **standalone programs**:
1. Create episode YAML in `data/episodes/{prf_id}.yaml`
2. Include: prf_id, title, description, year, duration_seconds, image_url, nrk_url

For **series** to show on kulturprogrammer page:
1. Create episode YAMLs with `series_id`
2. Create work YAML with `category: kulturprogram`
3. Create performance YAML linking to work with `series_id` and `image_url`
4. Update episodes with `performance_id`

For **about programs** (author portraits):
1. Create YAML in `data/nrk_about_programs/{series-id}.yaml`
2. Include `person_id` to link to author

### 6. Always fetch images
```python
def get_image_url(data):
    """Extract 960px image from NRK API response."""
    web_images = data.get('image', {}).get('webImages', [])
    for img in web_images:
        if img.get('pixelWidth') == 960:
            return img.get('imageUrl')
    return web_images[-1].get('imageUrl') if web_images else None
```

### 7. Parse duration
```python
import re
def parse_duration(duration_str):
    """Parse ISO8601 duration (PT1H30M45S) to seconds."""
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?', duration_str or '')
    if not match: return None
    h, m, s = int(match.group(1) or 0), int(match.group(2) or 0), float(match.group(3) or 0)
    return int(h * 3600 + m * 60 + s)
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
