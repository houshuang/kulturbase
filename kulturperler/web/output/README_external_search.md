# External Platform Search - Processing Guide

Generated: 2025-12-21

## Overview

This search identified Norwegian classical music content (opera, ballet, symphony, theatre) available on external platforms outside NRK. The goal is to find complete performances that could be added to the Kulturperler database as external resources.

## Output Files

### Primary Data Files

| File | Format | Contents |
|------|--------|----------|
| `youtube_gemini_search.json` | JSON | 50 YouTube videos found via Gemini search |
| `external_archive_finds.json` | JSON | 73 Archive.org items (38 classified as complete) |
| `external_youtube_finds.json` | JSON | Empty (DuckDuckGo approach failed) |
| `external_vimeo_finds.json` | JSON | Empty (DuckDuckGo approach failed) |

### Reports (Human-Readable)

| File | Contents |
|------|----------|
| `report_external_sources.txt` | **MASTER REPORT** - All platforms combined |
| `report_youtube_finds.txt` | YouTube results categorized by type |

### NRK Classical Music Reports (from earlier processing)

| File | Contents |
|------|----------|
| `report_operas.txt` | NRK opera performances |
| `report_ballets.txt` | NRK ballet performances |
| `report_symphonies.txt` | NRK symphony performances |
| `report_orchestral.txt` | NRK orchestral works |
| `report_norwegian_translations.txt` | Foreign operas sung in Norwegian (historically significant) |
| `report_play_links.txt` | Performances linked to existing plays in database |
| `classical_classified.json` | Gemini classifications of NRK content |
| `classical_performances.json` | Grouped multi-part performances |

## Data Structures

### youtube_gemini_search.json
```json
{
  "generated": "ISO timestamp",
  "total_videos": 50,
  "videos": [
    {
      "title": "Video title",
      "url": "https://www.youtube.com/watch?v=...",
      "channel": "Channel name",
      "duration": "1:39:57",
      "views": "12K views",
      "search_query": "Original search query"
    }
  ]
}
```

### external_archive_finds.json
```json
[
  {
    "identifier": "archive-org-id",
    "title": "Item title",
    "description": "Full description",
    "creator": "Creator/uploader",
    "date": "Upload date",
    "url": "https://archive.org/details/...",
    "query": "Search query used",
    "classification": {
      "is_complete_performance": true/false,
      "type": "opera|ballet|symphony|theatre|other",
      "is_norwegian": true/false,
      "work_title": "Name of the work",
      "composer_playwright": "Creator name",
      "performing_company": "Orchestra/company name",
      "reasoning": "Why classified this way"
    }
  }
]
```

## Key Findings

### YouTube (50 videos)
**High-value content:**
- Den Norske Opera & Ballett official channel: Nøtteknekkeren (1:39:57), Svanesjøen, Giselle, Onegin
- Trondheim Symfoniorkester: Full Beethoven 5 & 6, Rachmaninov 2
- Oslo Philharmonic: Nordheim works, Halvorsen
- Johan Svendsen symphonies (118K+ views)
- Grieg Piano Concerto (1.5M views)

**Note:** Some YouTube URLs from Gemini have malformed video IDs (very long strings). These need validation before use.

### Archive.org (38 complete performances)
**NRK archival content (not on NRK.no):**
- Stemmen (1963) - Poulenc opera with Wenche Foss
- Pendlerne (1974) - Theatre
- Kjære løgnhals (1964) - Theatre

**Norwegian National Ballet:**
- Ghosts (2017) - Ballet based on Ibsen's Gengangere

**Bergen Philharmonic:**
- Wagner Parsifal (2023 concert staging)
- Beethoven, Berlioz, Grieg symphonies

### Streaming Platforms Discovered
1. **OperaVision** (operavision.eu) - FREE, EU-funded
   - 10+ Den Norske Opera productions
   - Time-limited availability

2. **bergenphilive.no** - FREE
   - 200+ Bergen Philharmonic concerts
   - Complete Mahler & Sibelius cycles
   - Norwegian composers: Grieg, Sæverud, Svendsen

3. **Symphony.live** - Subscription
   - Bergen Philharmonic partnership

## Cross-References to Existing Plays

These external finds link to plays already in the database:

| External Content | Play ID | Play Title |
|-----------------|---------|------------|
| Ghosts ballet (Archive.org) | #564, #820 | Gengangere |
| BBC Ghosts 1973 (Archive.org) | #564, #820 | Gengangere |
| Peer Gynt music (various) | #264 | Peer Gynt |
| An Enemy of the People (Archive.org) | TBD | En folkefiende |

## Processing Recommendations

### Step 1: Validate YouTube URLs
```python
# Many URLs from Gemini have malformed IDs
# Valid format: youtube.com/watch?v=XXXXXXXXXXX (11 chars)
# Invalid: very long base64-like strings

import re
valid_pattern = r'youtube\.com/watch\?v=[\w-]{11}$'
```

### Step 2: Filter by Duration
For complete performances, prioritize:
- Ballets: 60+ minutes
- Operas: 90+ minutes
- Symphonies: 25+ minutes
- Theatre: 60+ minutes

### Step 3: Deduplicate
Check against existing `external_resources.yaml` to avoid duplicates.

### Step 4: Add to Database
Create entries in `data/external_resources.yaml`:
```yaml
- id: next_available_id
  play_id: 264  # if linked to a play
  title: "Peer Gynt - Bergen Philharmonic"
  url: "https://..."
  source: "youtube"  # or archive_org, operavision, bergenphilive
  type: "performance"
  duration_minutes: 45
  notes: "Full concert recording"
```

## Limitations

1. **YouTube search via Gemini**: Some URLs are hallucinated/malformed. Always validate video IDs.

2. **No direct YouTube/Vimeo API**: DuckDuckGo site: search was blocked. Used Gemini's Google Search grounding instead.

3. **Archive.org classification**: Gemini classifications may have errors. Manual review recommended for additions.

4. **OperaVision time limits**: Content availability changes. URLs may expire.

5. **Missing platforms**: Did not search Medici.tv, Marquee TV (subscription), Stage+ (subscription).

6. **Language detection**: Some content marked "Norwegian" may be international performances with Norwegian connections.

## Scripts Used

| Script | Purpose |
|--------|---------|
| `scripts/search_external_platforms.py` | Archive.org search + DuckDuckGo (failed for YT/Vimeo) |
| `scripts/search_youtube_gemini.py` | YouTube search via Gemini 2.0 Flash + Google Search |
| `scripts/classify_with_gemini.py` | NRK content classification |
| `scripts/generate_classical_reports.py` | Report generation |

## Next Steps

1. Run validation script on YouTube URLs
2. Manual review of top candidates
3. Check bergenphilive.no for specific works to add
4. Monitor OperaVision for new Den Norske Opera uploads
5. Consider adding Medici.tv search (requires different approach)
