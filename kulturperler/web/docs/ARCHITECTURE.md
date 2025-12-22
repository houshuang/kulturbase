# Kulturbase.no - Architecture & Data Structure

## Overview

Kulturbase.no is a browsable archive of Norwegian performing arts recordings, primarily from NRK (Norwegian Broadcasting Corporation) including Fjernsynsteatret (TV theater), Radioteatret (radio theater), and classical music performances from Bergen Filharmoniske Orkester.

**Tech Stack:**
- Frontend: SvelteKit with TypeScript
- Database: SQLite (compiled to WebAssembly via sql.js for browser)
- Data Storage: YAML files (source of truth) → compiled to SQLite
- Hosting: Static site generation

---

## Data Model

### Core Entities

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│   Person    │     │      Work        │     │ Institution │
│             │◄────┤  (composition)   │     │ (orchestra) │
│ playwright  │     │                  │     │             │
│ composer    │     │ playwright_id    │     └─────────────┘
│ director    │     │ composer_id      │            │
│ actor       │     │ librettist_id    │            │
└─────────────┘     │ based_on_work_id │            │
       │            └────────┬─────────┘            │
       │                     │                      │
       │            ┌────────▼─────────┐            │
       │            │   Performance    │◄───────────┘
       └───────────►│  (recording)     │
                    │                  │
                    │ work_id          │
                    │ source           │
                    │ medium           │
                    │ year             │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │     Episode      │
                    │  (media file)    │
                    │                  │
                    │ performance_id   │
                    │ nrk_url          │
                    │ duration         │
                    └──────────────────┘
```

### Entity Descriptions

#### Work (1,482 total)
An abstract creative work - a play, opera, symphony, etc.

| Field | Description |
|-------|-------------|
| `id` | Unique identifier |
| `title` | Norwegian title |
| `original_title` | Original language title (if different) |
| `work_type` | Specific type (see below) |
| `category` | UI grouping category |
| `playwright_id` | Author (for theater) |
| `composer_id` | Composer (for music) |
| `librettist_id` | Librettist (for opera) |
| `based_on_work_id` | Literary source (e.g., Grieg's Peer Gynt → Ibsen's Peer Gynt) |
| `year_written` | Year of composition |
| `synopsis` | Plot summary or opus number |
| `sceneweb_url` | Link to Sceneweb.no |
| `wikipedia_url` | Link to Wikipedia |
| `wikidata_id` | Wikidata identifier |

**Work Types** (granular classification):
| Type | Count | Description |
|------|-------|-------------|
| `nrk_teaterstykke` | 550 | NRK original TV/radio productions |
| `orchestral` | 286 | Orchestral works (suites, tone poems) |
| `teaterstykke` | 276 | Classic theater plays |
| `symphony` | 95 | Symphonies |
| `concerto` | 86 | Concertos |
| `opera` | 50 | Operas |
| `chamber` | 39 | Chamber music |
| `dramaserie` | 37 | Drama series |
| `choral` | 32 | Choral works |
| `ballet` | 23 | Ballets |
| `operetta` | 8 | Operettas |

**Categories** (UI grouping):
| Category | Count | Description |
|----------|-------|-------------|
| `teater` | 826 | Theater works (teaterstykke + nrk_teaterstykke) |
| `konsert` | 548 | Concert works (orchestral, symphony, concerto, chamber, choral) |
| `opera` | 71 | Opera, operetta, ballet |
| `dramaserie` | 37 | Drama series |

#### Performance (1,810 total)
A specific recording or production of a work.

| Field | Description |
|-------|-------------|
| `id` | Unique identifier |
| `work_id` | Link to parent work |
| `source` | Content source (see below) |
| `medium` | tv or radio |
| `year` | Recording year |
| `title` | Performance-specific title |
| `description` | Credits, recording info |
| `venue` | Recording location |
| `total_duration` | Total runtime in seconds |
| `credits` | Array of person_id + role |

**Sources:**
| Source | Count | Description |
|--------|-------|-------------|
| `nrk` | 1,318 | NRK TV/Radio productions |
| `bergenphilive` | 492 | Bergen Phil Live streams |

**Mediums:**
| Medium | Count | Description |
|--------|-------|-------------|
| `tv` | 1,461 | Video recordings |
| `radio` | 349 | Audio recordings |

#### Episode (3,024 total)
An individual media file (video/audio).

| Field | Description |
|-------|-------------|
| `prf_id` | NRK program ID (unique) |
| `performance_id` | Link to parent performance |
| `title` | Episode title |
| `description` | Episode description |
| `year` | Broadcast year |
| `duration_seconds` | Runtime |
| `nrk_url` | Direct link to NRK player |
| `image_url` | Thumbnail URL |
| `source` | nrk, archive, bergenphilive |
| `medium` | tv or radio |
| `part_number` | For multi-part episodes |
| `total_parts` | Total parts in series |
| `is_introduction` | Whether this is an intro segment |
| `resources` | Array of external links (archive.org, etc.) |

#### Person (3,689 total)
A person involved in productions.

| Field | Description |
|-------|-------------|
| `id` | Unique identifier |
| `name` | Full name |
| `normalized_name` | Lowercase, simplified for search |
| `birth_year` | Year of birth |
| `death_year` | Year of death |
| `nationality` | Country |
| `bio` | Biography text |
| `image_url` | Portrait URL |
| `sceneweb_url` | Sceneweb.no link |
| `wikipedia_url` | Wikipedia link |
| `wikidata_id` | Wikidata identifier |

**Roles** (via performance_persons / episode_persons):
- `playwright` - Author/dramatist
- `composer` - Music composer
- `librettist` - Opera librettist
- `director` - Stage/film director
- `actor` - Performer
- `conductor` - Orchestra conductor
- `soloist` - Solo performer
- `set_designer`, `costume_designer`, `producer`, `other`

#### Supporting Entities

**NrkAboutProgram** (403 total)
NRK documentaries and programs about persons (e.g., "Ibsen på TV", "Portrett: Liv Ullmann").

**ExternalResource** (826 total)
External streaming links not yet integrated into Work→Performance model.
- Type: `operavision`, `bergenphilive`, `operaen`, etc.

**WorkExternalLink** (45 total)
Links from works to external reading/viewing sources:
- `bokselskap` - Full text on Bokselskap.no
- `streaming` - External streaming (Applaus Scene, etc.)

---

## File Structure

### Source Data (YAML)
```
data/
├── plays/           # 1,482 work YAML files
│   ├── 1.yaml
│   └── ...
├── performances/    # 1,810 performance YAML files
│   ├── 1.yaml
│   └── ...
├── episodes/        # 3,024 episode YAML files
│   ├── PRHO04000560.yaml
│   └── ...
├── persons/         # 3,689 person YAML files
│   ├── 1.yaml
│   └── ...
├── nrk_about_programs/  # Documentary references
├── institutions/    # Orchestra/theater definitions (unused)
├── external_resources.yaml  # External streaming links
├── tags.yaml        # Content tags
└── metadata.yaml    # Site metadata
```

### Sample YAML Files

**Work (data/plays/1.yaml):**
```yaml
id: 1
title: Miss Marple tar saken i egne hender
original_title: Miss Marple tar saken i egne hender
playwright_id: 1321
synopsis: Miss Marple-mysterier av Agatha Christie...
work_type: teaterstykke
category: teater
```

**Performance (data/performances/1.yaml):**
```yaml
id: 1
work_id: 1
source: nrk
title: Miss Marple tar saken i egne hender
medium: radio
total_duration: 7246
image_url: https://gfx.nrk.no/...
credits:
  - person_id: 1321
    role: playwright
  - person_id: 1276
    role: director
  - person_id: 62
    role: actor
```

**Episode (data/episodes/ARCH_NRK-XXX.yaml):**
```yaml
prf_id: ARCH_NRK-FBUA03015079-AR-
title: Serum Serum 1:6
performance_id: 940
source: archive
medium: tv
year: 1979
resources:
  - url: https://archive.org/details/...
    type: archive_primary
```

### Compiled Database
```
static/kulturperler.db  # SQLite database (built from YAML)
```

Build command: `python3 scripts/build_database.py`

---

## Navigation Structure

### Routes

| URL | Page | Description |
|-----|------|-------------|
| `/` | Home | Landing page with discovery rows |
| `/teater` | Theater | Browse theater works (teaterstykke + nrk_teaterstykke) |
| `/opera` | Opera | Browse opera, ballet, operetta |
| `/dramaserier` | Drama Series | Browse drama series |
| `/konserter` | Concerts | Browse Bergen Phil and classical concerts |
| `/skapere` | Creators | Browse playwrights, composers |
| `/persons` | All Persons | Browse all persons |
| `/work/[id]` | Work Detail | Single work with all performances |
| `/performance/[id]` | Performance Detail | Single performance with episodes |
| `/person/[id]` | Person Detail | Person with works and credits |
| `/episode/[id]` | Episode Detail | Single episode (rarely used directly) |

### Current Navigation Tabs
```
| Hjem | Teater | Opera | Dramaserier | Konserter | Skapere |
```

### Page Relationships
```
Landing Page (/):
  └─► Work cards → /work/[id]
  └─► Performance cards → /performance/[id]
  └─► Concert external links

Work Page (/work/[id]):
  └─► Creator link → /person/[id]
  └─► Performance sections (TV/Radio) → /performance/[id]
  └─► External links (Bokselskap, Applaus Scene)

Performance Page (/performance/[id]):
  └─► Back to work → /work/[id]
  └─► Cast/crew links → /person/[id]
  └─► Episode list → NRK player / archive.org

Person Page (/person/[id]):
  └─► Works written/composed → /work/[id]
  └─► NRK documentaries about them
```

---

## UI Labels & Display Logic

### Medium Labels (Dynamic)
Labels are derived from source + category + medium:

```typescript
function getMediumLabel(source, category, medium) {
  if (source === 'bergenphilive') return 'Bergen Phil Live';
  if (category === 'dramaserie') return 'Dramaserie';
  if (category === 'teater') return medium === 'tv' ? 'Fjernsynsteater' : 'Radioteater';
  return medium === 'tv' ? 'TV-opptak' : 'Lydopptak';
}
```

| Source | Category | Medium | Display Label |
|--------|----------|--------|---------------|
| bergenphilive | * | * | Bergen Phil Live |
| nrk | teater | tv | Fjernsynsteater |
| nrk | teater | radio | Radioteater |
| nrk | dramaserie | * | Dramaserie |
| nrk | konsert | tv | TV-opptak |
| nrk | konsert | radio | Lydopptak |
| nrk | opera | tv | TV-opptak |

### Creator Labels
- Theater works: "av [Playwright]" (skrevet [year])
- Concert works: "[Composer]" (komponert [year])

---

## Data Sources & Enrichment

### Primary Sources
1. **NRK TV/Radio API** - Episode metadata, images, program IDs
2. **Bergen Phil Live** - Concert streams (bergenphilive.no)
3. **Sceneweb.no** - Theater metadata (playwrights, years)
4. **Norwegian Wikipedia** - Biographies, images
5. **Wikidata** - Structured data, identifiers
6. **Bokselskap.no** - Full text links for public domain works
7. **Archive.org** - Alternative video sources

### Enrichment Scripts
```
scripts/
├── build_database.py           # YAML → SQLite
├── enrich_playwrights.py       # Sceneweb data
├── enrich_wikipedia_bios.py    # Wikipedia biographies
├── enrich_from_wikidata.py     # Wikidata integration
├── import_classical_performances.py  # NRK classical import
├── import_bergenphil_concerts.py     # Bergen Phil import (uses Gemini)
├── link_related_works.py       # Connect operas to source plays
├── link_persons.py             # Deduplicate persons
└── validate_data.py            # Data integrity checks
```

---

## Known Limitations & Issues

### Data Model
1. **Institution linking incomplete** - Orchestras/theaters not linked to performances
2. **Conductor/soloist metadata sparse** - Most Bergen Phil concerts lack conductor info
3. **Work relationships limited** - `based_on_work_id` only links to one source
4. **No multi-language support** - All content in Norwegian

### Navigation
1. **No search functionality** - Only browsing by category
2. **Limited filtering** - Year range, playwright only on some pages
3. **No "related works" recommendations**
4. **Episode page rarely accessed** - Most navigation goes Work → Performance

### Content Gaps
1. **826 external resources** not integrated into Work→Performance model
2. **Hørespill (radio drama)** not distinguished from Radioteater
3. **Images missing** for many works and persons
4. **Synopsis missing** for many works

---

## Statistics Summary

| Entity | Count |
|--------|-------|
| Works | 1,482 |
| Performances | 1,810 |
| Episodes | 3,024 |
| Persons | 3,689 |
| External Resources (unintegrated) | 826 |
| NRK About Programs | 403 |
| Work External Links | 45 |

| Category | Works | Performances |
|----------|-------|--------------|
| Teater | 826 | ~880 |
| Konsert | 548 | ~550 |
| Opera | 71 | ~75 |
| Dramaserie | 37 | ~37 |

| Source | Performances |
|--------|--------------|
| NRK | 1,318 |
| Bergen Phil Live | 492 |

---

## Future Considerations

1. **Hørespill category** - Separate radio drama from radio theater
2. **Full-text search** - Elasticsearch or similar
3. **Person roles on works** - Many-to-many with role types
4. **Premiere dates** - Track first performance dates
5. **Venue/theater entities** - Link to institutions
6. **User favorites/history** - Personalization features
7. **API access** - Public API for data access
8. **Accessibility** - WCAG compliance review
