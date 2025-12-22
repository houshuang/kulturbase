# Conductor Enrichment for Bergen Philharmonic Performances

This directory contains scripts to enrich Bergen Philharmonic Live (bergenphilive) concert performances with conductor data.

## Quick Start

```bash
# 1. Check current status
python3 scripts/check_bergenphilive_status.py

# 2. Test with a single concert
python3 scripts/test_single_concert.py

# 3. Test with first 3 performances (no changes)
python3 scripts/test_enrich_conductors.py

# 4. Run full enrichment (modifies YAML files)
python3 scripts/enrich_bergenphilive_conductors.py

# 5. Validate changes
python3 scripts/validate_data.py

# 6. Rebuild database
python3 scripts/build_database.py

# 7. Review and commit
git diff data/
git add data/
git commit -m "Add conductor credits to bergenphilive performances"
```

## Scripts

### check_bergenphilive_status.py
**Purpose:** Show current status of bergenphilive performances

**Output:**
- Total count of bergenphilive performances
- How many have credits
- How many have conductor credits
- Sample performances with/without conductors

**Usage:**
```bash
python3 scripts/check_bergenphilive_status.py
```

**When to use:** Before starting enrichment to understand current state

---

### test_single_concert.py
**Purpose:** Test Gemini API with one specific concert

**Output:**
- Full API request/response
- Shows if Google Search is working
- Shows raw conductor information returned

**Usage:**
```bash
python3 scripts/test_single_concert.py
```

**When to use:** First step - verify API is working before processing many concerts

---

### test_enrich_conductors.py
**Purpose:** Dry-run test on first 3 performances

**Output:**
- Processes first 3 bergenphilive performances
- Shows what conductor would be found for each
- **Does NOT modify any files**

**Usage:**
```bash
python3 scripts/test_enrich_conductors.py
```

**When to use:** Second step - verify the full pipeline works before running on all data

---

### enrich_bergenphilive_conductors.py
**Purpose:** Main enrichment script - processes ALL performances

**Output:**
- Processes all 228 bergenphilive performances
- Creates new person entries for conductors
- Updates performance YAML files with conductor credits
- Shows progress and summary

**Usage:**
```bash
python3 scripts/enrich_bergenphilive_conductors.py
```

**Duration:** ~8-10 minutes (2 second delay between API calls)

**When to use:** After verifying test scripts work correctly

**What it does:**
1. Loads all bergenphilive performances
2. For each performance:
   - Looks up concert URL from external_resources.yaml
   - Searches for conductor using Gemini + Google Search
   - Extracts conductor name from response
   - Finds or creates person entry
   - Updates performance YAML with conductor credit
3. Shows summary of results

**What it modifies:**
- `data/performances/*.yaml` - adds conductor credits
- `data/persons/*.yaml` - creates new conductor entries

---

## Workflow Details

### Step 1: Check Current Status
```bash
python3 scripts/check_bergenphilive_status.py
```

Example output:
```
Total bergenphilive performances: 228

Credit Status:
  Performances with any credits:    0
  Performances with conductor:      0
  Performances without credits:     228

Performances needing conductor enrichment: 228
```

### Step 2: Test API
```bash
python3 scripts/test_single_concert.py
```

This tests:
- Gemini API key is valid
- Google Search grounding works
- Can extract conductor information

### Step 3: Dry Run
```bash
python3 scripts/test_enrich_conductors.py
```

Example output:
```
[1/3] Dvořák: Fiolinkonsert (2025)
  URL: https://bergenphilive.no/alle-konsertopptak/2025/9/dvorak-fiolinkonsert/
  Searching...
  Raw response: Edward Gardner
  ✓ Found conductor: Edward Gardner

[2/3] Matre: Freude (2025)
  URL: https://bergenphilive.no/alle-konsertopptak/2025/9/matre-freude/
  Searching...
  Raw response: NOT_FOUND
  ✗ Could not extract conductor name
```

### Step 4: Run Full Enrichment
```bash
python3 scripts/enrich_bergenphilive_conductors.py
```

Example output:
```
Enriching bergenphilive performances with conductor data...
======================================================================

Loading data...
Found 228 bergenphilive performances
Found 3961 persons in database
Found 228 bergenphilive external resources

[1/228]
Processing: Dvořák: Fiolinkonsert (2025)
  URL: https://bergenphilive.no/alle-konsertopptak/2025/9/dvorak-fiolinkonsert/
  Searching for conductor...
  Gemini response: Edward Gardner...
  Found conductor: Edward Gardner
  Created new person: Edward Gardner (ID: 3962)
  ✓ Updated performance with conductor

[2/228]
Processing: Matre: Freude (2025)
  URL: https://bergenphilive.no/alle-konsertopptak/2025/9/matre-freude/
  Searching for conductor...
  Could not extract conductor name from response

...

======================================================================
Summary:
  Updated: 180 performances with conductor information
  Skipped: 48 performances (already had conductor or not found)

Next steps:
1. Review the changes: git diff data/
2. Validate: python3 scripts/validate_data.py
3. Rebuild database: python3 scripts/build_database.py
```

### Step 5: Review Changes
```bash
# See what was changed
git status

# Review performance updates
git diff data/performances/

# Review new persons created
git diff data/persons/

# See summary
git diff --stat data/
```

### Step 6: Validate
```bash
python3 scripts/validate_data.py
```

This checks:
- All person_id references exist
- Required fields are present
- No duplicate IDs

### Step 7: Rebuild Database
```bash
python3 scripts/build_database.py
```

Rebuilds SQLite database from the updated YAML files.

### Step 8: Commit
```bash
git add data/performances/
git add data/persons/
git commit -m "Add conductor credits to bergenphilive performances"
```

## Technical Details

### How It Works

1. **Data Loading**
   - Loads performances from `data/performances/*.yaml`
   - Filters for `source: bergenphilive`
   - Loads concert URLs from `data/external_resources.yaml`
   - Loads existing persons from `data/persons/*.yaml`

2. **Conductor Search**
   - Uses Gemini 3 Flash API with Google Search grounding
   - Searches for: "Bergen Filharmoniske [title] [year] dirigent"
   - Also searches the concert URL directly
   - Extracts conductor name from response

3. **Name Extraction**
   - Looks for patterns like "Conductor: Name" or "Dirigent: Name"
   - Handles "NOT_FOUND" responses
   - Cleans up name (removes parentheticals, etc.)
   - Validates name looks reasonable

4. **Person Lookup/Creation**
   - Searches existing persons (case-insensitive)
   - Matches on `name` or `normalized_name` fields
   - Creates new person if not found
   - Assigns next available person ID

5. **Performance Update**
   - Adds conductor to credits array
   - Format: `{person_id: 123, role: conductor}`
   - Saves updated YAML file

### API Details

**Endpoint:** `https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent`

**Authentication:** API key from `.env` file (`GEMINI_KEY`)

**Features Used:**
- Google Search grounding (`"tools": [{"google_search": {}}]`)
- Low temperature (0.1) for consistent results
- 30 second timeout per request

**Rate Limiting:**
- 2 seconds between requests
- Total time: ~8 minutes for 228 performances

### Data Structure

**Performance YAML:**
```yaml
id: 1381
work_id: 1304
source: bergenphilive
title: 'Dvořák: Fiolinkonsert'
medium: tv
venue: Bergen
year: 2025
description: 'Bergen Filharmoniske Orkester. Komponist: Dvořák. Innspilt: 2025-09-18'
credits:
- person_id: 3962
  role: conductor
```

**Person YAML:**
```yaml
id: 3962
name: Edward Gardner
normalized_name: edward gardner
```

## Expected Results

Based on Bergen Philharmonic's typical operations:

- **~180-200 performances** should get conductor information
- **~20-48 performances** may not have conductor info available online
- **~10-20 unique conductors** (Bergen Phil has regular principal conductors)

Common conductors expected:
- Edward Gardner (Chief Conductor 2015-2022)
- Marc Soustrot (Chief Conductor 2023-)
- Various guest conductors

## Troubleshooting

### "GEMINI_KEY not found in .env"
**Solution:** Create/update `.env` file with your Gemini API key:
```bash
echo "GEMINI_KEY=your_key_here" >> .env
```

### "Error calling Gemini: 429"
**Solution:** Rate limit hit. The script has 2-second delays. Increase if needed:
```python
time.sleep(5)  # Change from 2 to 5 seconds
```

### Duplicate Persons Created
**Cause:** Conductor name appears in different formats (e.g., "Edward Gardner" vs "E. Gardner")

**Solution:**
1. Note the duplicate IDs
2. Manually merge them after enrichment
3. Update all references to use single ID
4. Delete duplicate person file

### No Conductor Found
**Cause:** Concert info not available online, or Gemini couldn't find it

**Solution:**
- These performances will be skipped
- Can manually add conductor later if info becomes available
- Search bergenphilive.no directly for the concert

### API Timeout
**Cause:** Slow network or API response

**Solution:** Script will continue to next performance. Run again to retry failures.

## Limitations

1. **Web Search Dependency:** Requires information to be publicly available
2. **Name Variations:** May create duplicates if names vary
3. **Historical Data:** Older concerts may have less info available
4. **Language:** Works best with Norwegian and English conductor names

## Future Improvements

1. **Caching:** Cache Gemini responses to avoid re-querying
2. **Retry Logic:** Automatically retry failed searches
3. **Name Normalization:** Better matching for name variations
4. **Wikidata Integration:** Enrich conductor entries with birth/death years
5. **Multiple Roles:** Add soloists, composers in residence, etc.

## Support

For issues or questions:
1. Check this README
2. Review the main CLAUDE.md project guide
3. Test with the dry-run scripts first
4. Review git diffs carefully before committing
