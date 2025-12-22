# Bergen Philharmonic Conductor Enrichment

## Overview

This document describes the process for enriching Bergen Philharmonic Live (bergenphilive) concert performances with conductor information.

## Current State

- **228 bergenphilive performances** in `data/performances/*.yaml`
- All have `source: bergenphilive`
- All currently have empty `credits: []` arrays
- Each performance is linked to a concert URL in `data/external_resources.yaml`

## Approach

The enrichment process:

1. **Load Data**
   - Load all bergenphilive performances from `data/performances/`
   - Load external resources from `data/external_resources.yaml` to get concert URLs
   - Load existing persons from `data/persons/`

2. **Find Conductor Information**
   - For each performance, look up its concert URL from external_resources
   - Use Gemini 3 Flash with Google Search grounding to find conductor info
   - The API searches the concert URL and web for conductor/dirigent information

3. **Create or Update Person Entries**
   - Extract conductor name from Gemini response
   - Search for existing person entry by name (case-insensitive)
   - If not found, create new person entry in `data/persons/`

4. **Update Performance Credits**
   - Add conductor credit to performance YAML:
     ```yaml
     credits:
     - person_id: <id>
       role: conductor
     ```
   - Save updated YAML file

## Scripts

### 1. test_single_concert.py

**Purpose:** Test the Gemini API with a single concert to verify it works.

**Usage:**
```bash
python3 scripts/test_single_concert.py
```

This will test with "Dvořák: Fiolinkonsert" and show the full API response.

### 2. test_enrich_conductors.py

**Purpose:** Test the enrichment logic on the first 3 performances without making changes.

**Usage:**
```bash
python3 scripts/test_enrich_conductors.py
```

This will:
- Load the first 3 bergenphilive performances
- Look up their URLs
- Search for conductor information
- Display results WITHOUT modifying any files

### 3. enrich_bergenphilive_conductors.py

**Purpose:** Main script to enrich ALL bergenphilive performances with conductor data.

**Usage:**
```bash
python3 scripts/enrich_bergenphilive_conductors.py
```

This will:
- Process all 228 bergenphilive performances
- Create new person entries for conductors not in the database
- Update performance YAML files with conductor credits
- Show progress and summary statistics

**Rate Limiting:** 2 seconds between API calls (approx. 8 minutes total)

## Workflow

### Step 1: Test Single Concert
```bash
python3 scripts/test_single_concert.py
```

Verify that the Gemini API is working and returning conductor information.

### Step 2: Test on Sample Data
```bash
python3 scripts/test_enrich_conductors.py
```

Test the full enrichment logic on just 3 performances to verify:
- URLs are being looked up correctly
- Conductor names are being extracted
- The logic works end-to-end

### Step 3: Run Full Enrichment
```bash
python3 scripts/enrich_bergenphilive_conductors.py
```

Process all 228 performances. This will:
- Take approximately 8-10 minutes (with rate limiting)
- Create new person entries as needed
- Update performance YAML files
- Show progress for each performance

### Step 4: Review Changes
```bash
git diff data/performances/
git diff data/persons/
```

Review the changes to ensure they look correct:
- Check that conductor credits were added
- Verify person entries look correct
- Check for any unexpected changes

### Step 5: Validate
```bash
python3 scripts/validate_data.py
```

Run validation to ensure:
- All person_id references are valid
- Required fields are present
- No duplicate IDs

### Step 6: Rebuild Database
```bash
python3 scripts/build_database.py
```

Rebuild the SQLite database from the updated YAML files.

### Step 7: Commit Changes
```bash
git add data/performances/
git add data/persons/
git commit -m "Add conductor credits to bergenphilive performances"
```

## Data Structure

### Performance YAML Before
```yaml
id: 1381
work_id: 1304
source: bergenphilive
title: 'Dvořák: Fiolinkonsert'
medium: tv
venue: Bergen
year: 2025
description: 'Bergen Filharmoniske Orkester. Komponist: Dvořák. Innspilt: 2025-09-18'
credits: []
```

### Performance YAML After
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
- person_id: 3968
  role: conductor
```

### New Person Entry
```yaml
id: 3968
name: Edward Gardner
normalized_name: edward gardner
```

## Expected Results

- **Updated Performances:** Performances with conductor information found
- **Skipped Performances:** Performances where conductor info couldn't be found or already had conductor
- **New Persons:** New conductor entries created (estimated 10-20 conductors)

## Troubleshooting

### API Key Issues
If you see "Error: GEMINI_KEY not found in .env", ensure `.env` file has:
```
GEMINI_KEY=your_key_here
```

### Rate Limiting
If you hit rate limits, the script has a 2-second delay between requests. You can increase this in the script if needed.

### Conductor Not Found
Some concerts may not have conductor information available online. These will be skipped with a message.

### Name Matching Issues
The script does case-insensitive matching for existing persons. If a conductor appears under a slightly different name, a duplicate may be created. These can be manually merged later.

## Notes

- The script uses Gemini 3 Flash with Google Search grounding
- Concert URLs from bergenphilive.no are used when available
- The script is conservative - it only adds data, never removes existing credits
- All changes are visible in git diffs before committing
- YAML files remain the source of truth
