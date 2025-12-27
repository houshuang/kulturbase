# Nordic Theatre & Radio Theatre Import Plan

## Overview

This plan covers importing theatre and radio theatre content from Sweden, Denmark, and Finland (Swedish-language only) that is:
- Available to stream from Norway
- Full performances (not trailers/interviews)
- In Norwegian, Swedish, or Danish

## Data Model Changes Required

### Add `language` field

Add to `works`, `performances`, and `episodes` tables:

```yaml
language: "no"  # ISO 639-1 codes: no, sv, da, fi
```

**Values:**
- `no` - Norwegian (default for existing NRK content)
- `sv` - Swedish
- `da` - Danish
- `fi` - Finnish (only for Finland-Swedish content where appropriate)

### Implementation
1. Add `language TEXT` to schema in `build_database.py`
2. Add `language` field to TypeScript types
3. Add language filter to frontend browse page
4. Backfill existing content with `language: "no"`

---

## Source 1: Sveriges Radio (Swedish Radio) ⭐ HIGH PRIORITY

**API:** `https://api.sr.se/api/v2/`
**Accessibility:** ✅ Full API access, audio streamable from Norway
**Documentation:** https://api.sr.se/api/documentation/v2/

### Available Programs

| Program ID | Name | Episodes | Type |
|------------|------|----------|------|
| 4453 | Dramaklassiker | 111 | Classic radio theatre |
| 3171 | Drama för unga | 164 | Children's drama (ages 9-13) |
| 4976 | Sveriges Radio Drama | 19 | Contemporary drama |
| 6605 | Scenen – Shakespeare | 19 | Shakespeare adaptations |
| 4947 | P3 Serie | 60 | Crime/thriller series |
| **Total** | | **~373** | |

### API Endpoints

```python
# List all episodes for a program
GET https://api.sr.se/api/v2/episodes/index?programid={id}&format=json&pagination=false

# Get single episode
GET https://api.sr.se/api/v2/episodes/{episode_id}?format=json

# Episode fields:
# - id: unique episode ID (use as prf_id: "SR_{id}")
# - title
# - description
# - url: web URL to sverigesradio.se
# - publishdateutc: "/Date(timestamp)/" format
# - imageurl
# - listenpodfile.duration: seconds
# - listenpodfile.url: direct MP3 URL
```

### Import Script: `scripts/import_sr_drama.py`

```python
# Pseudo-code structure
1. Fetch all episodes from each program
2. For each episode:
   - Parse title to extract work name (e.g., "Hamlet, del 1" → work "Hamlet")
   - Check if work exists (match by title, author)
   - Create work if needed (with playwright lookup)
   - Create performance (grouping multi-part episodes)
   - Create episode YAML
3. Set language: "sv" for all
4. Set source: "sr" (Sveriges Radio)
5. Set medium: "radio"
```

### Work Matching Strategy

Many SR dramas are classic plays that may already exist in our database (e.g., Strindberg, Ibsen, Shakespeare). The import should:

1. **Exact match:** Title matches existing work
2. **Author match:** Same playwright + similar title
3. **Create new:** If no match, create work with playwright

**Example mapping:**
- "Kronbruden av Strindberg" → Link to existing "Kronbruden" by Strindberg
- "Hamlet" (Scenen) → Link to existing Shakespeare's "Hamlet"
- "Jeppe på berget av Holberg" → Link to existing Holberg work

---

## Source 2: Yle Arenan (Finland-Swedish) ⭐ MEDIUM PRIORITY

**URL:** https://arenan.yle.fi
**Accessibility:** ✅ Accessible from Norway (no geo-blocking detected)
**API:** ❌ No public API

### Known Content

| Series | Content | Notes |
|--------|---------|-------|
| Pärlor från Radioteatern | Swedish radio theatre | 2+ episodes found |
| Radioteater | Various productions | Manual search needed |

### Import Approach

1. **Manual discovery:** Search Yle Arenan for:
   - "radioteater"
   - "hörspel"
   - "teater"
   - "drama"

2. **Web scraping:** Yle uses React/Next.js. Would need to:
   - Intercept API calls from browser
   - Or use headless browser to extract content

3. **Episode format:**
   ```yaml
   prf_id: YLE_{program_id}
   source: yle
   language: sv
   medium: radio
   ```

### Limitations
- No bulk export capability
- Manual cataloging more realistic than automated import
- Start with "Pärlor från Radioteatern" as pilot

---

## Source 3: Archive.org (DR Bonanza) ⭐ HIGH PRIORITY

**URL:** https://archive.org/details/dr-bonanza-complete-archive
**Accessibility:** ✅ Full access, no restrictions
**API:** ✅ REST API available

### Content

DR Bonanza was Denmark's broadcast archive (shut down March 2024). The complete backup includes:
- Danish TV theatre productions
- Radio theatre (Radioteatret)
- Cultural programming

### API Example

```bash
curl "https://archive.org/advancedsearch.php?q=collection:dr-bonanza-complete-archive+AND+teater&fl[]=identifier,title,description,creator,date&output=json&rows=100"
```

### Import Strategy

1. **Search queries:**
   - `collection:dr-bonanza-complete-archive AND teater`
   - `collection:dr-bonanza-complete-archive AND radioteater`
   - `collection:dr-bonanza-complete-archive AND hørspil`
   - `collection:dr-bonanza-complete-archive AND skuespil`

2. **Metadata extraction:**
   ```yaml
   prf_id: DR_{identifier}
   source: dr_bonanza
   language: da
   medium: tv or radio (from metadata)
   ```

3. **Playwright matching:**
   - Danish titles may differ from Norwegian (e.g., "Et dukkehjem" vs "Et dukkehjem")
   - Use Wikidata IDs for matching across languages

---

## Source 4: OperaVision ⭐ LOW PRIORITY (non-theatre focus)

**URL:** https://operavision.eu
**Accessibility:** ✅ Free, no geo-blocking
**API:** ❌ No API

### Nordic Partners
- Norwegian Opera & Ballet
- Royal Swedish Opera
- Finnish National Opera

**Note:** Focus is opera/ballet, not theatre. Lower priority for this import but could enrich opera content.

---

## Work Linking Across Languages

### Challenge
Same play performed in different languages should link to the same work:
- Ibsen's "Et dukkehjem" (Norwegian) = "Ett dockhem" (Swedish) = "Et dukkehjem" (Danish)
- Shakespeare's "Hamlet" is "Hamlet" in all languages

### Solution

1. **Use Wikidata IDs:** Works table has `wikidata_id` field
   - Query Wikidata for canonical work
   - Link all performances to same work regardless of title language

2. **Title variants:** Store `original_title` for original language
   - Swedish "Fröken Julie" → original_title: "Fröken Julie"
   - Norwegian performance would use same work_id

3. **Create cross-reference during import:**
   ```python
   # Pseudo-code
   def find_or_create_work(title, playwright_name, language):
       # Try exact title match
       # Try Wikidata lookup
       # Try author + fuzzy title
       # Create new if no match
   ```

---

## Implementation Phases

### Phase 1: Schema Update
- [ ] Add `language` field to database schema
- [ ] Update TypeScript types
- [ ] Backfill existing content with `language: "no"`
- [ ] Add language filter to frontend

### Phase 2: Sveriges Radio Import (Highest value)
- [ ] Write `scripts/import_sr_drama.py`
- [ ] Import Dramaklassiker (111 episodes)
- [ ] Import Drama för unga (164 episodes)
- [ ] Import P3 Serie (60 episodes)
- [ ] Import Scenen – Shakespeare (19 episodes)
- [ ] Import Sveriges Radio Drama (19 episodes)
- [ ] Match works to existing playwrights (Strindberg, Ibsen, etc.)

### Phase 3: DR Bonanza Import
- [ ] Explore Archive.org collection structure
- [ ] Write `scripts/import_dr_bonanza.py`
- [ ] Import Danish theatre productions
- [ ] Import Danish radio theatre
- [ ] Match to existing works via Wikidata

### Phase 4: Yle Arenan (Manual)
- [ ] Manual search and cataloging
- [ ] Add Finland-Swedish radio theatre
- [ ] Focus on "Pärlor från Radioteatern"

---

## Episode/Performance Structure

### For multi-part productions (e.g., "Hamlet del 1-3")

```yaml
# Performance (groups the parts)
id: 3001
work_id: 123  # Links to "Hamlet"
title: "Hamlet - Scenen"
source: sr
language: sv
medium: radio
year: 2024

# Episode 1
prf_id: SR_2554264
title: "Hamlet, del 1"
performance_id: 3001
episode_number: 1

# Episode 2
prf_id: SR_2554265
title: "Hamlet, del 2"
performance_id: 3001
episode_number: 2
```

### For standalone productions

```yaml
# Performance
id: 3002
work_id: 456  # Links to "En dörr skall vara öppen eller stängd"
source: sr
language: sv
medium: radio

# Single episode
prf_id: SR_2554264
performance_id: 3002
```

---

## Estimated Content Volume

| Source | Episodes | Works | Priority |
|--------|----------|-------|----------|
| Sveriges Radio | ~373 | ~150-200 | HIGH |
| DR Bonanza | Unknown (100s-1000s?) | Unknown | HIGH |
| Yle Arenan | ~20-50 (manual) | ~15-30 | MEDIUM |
| **Total new** | **~500-1500+** | **~200-400** | |

Current database: 636 theatre works, 3862 NRK episodes

---

## Technical Notes

### Sveriges Radio API Rate Limits
- No documented rate limits
- Use pagination: `?page=1&size=100`
- Add delays between requests (1 sec)

### Archive.org API
- 100 results per page default
- Use `rows` parameter for more
- JSON output format: `&output=json`

### ID Conventions
- Sveriges Radio: `SR_{episode_id}`
- DR Bonanza: `DR_{identifier}`
- Yle: `YLE_{program_id}`

### Source field values
- `sr` - Sveriges Radio
- `dr_bonanza` - DR Bonanza archive
- `yle` - Yle Arenan
- `nrk` - NRK (existing)
