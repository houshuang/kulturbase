# Kulturperler Database Content Quality Audit

Generated: 2025-12-19T23:03:44

## Executive Summary

**Database:** `/Users/stian/src/nrk/kulturperler/web/static/kulturperler.db`
**Total Records:** 2,367 episodes | 854 plays | 3,201 persons

### Auto-Fixed Issues: 27
- 2 episode titles with extra whitespace
- 14 play titles with trailing/extra whitespace
- 10 person names with trailing/extra whitespace
- 1 person name with trailing period

### Issues Requiring Review: 4 categories

---

## 1. Whitespace Issues (FIXED)

### Episodes (2 fixed)
- `MKTT77001077`: 'Syv  svarte perler' → 'Syv svarte perler'
- `MKTT62002062`: 'På flukt med  99 valper' → 'På flukt med 99 valper'

### Plays (14 fixed)
- ID 18: 'Hvem er den mystiske Eric Norton? ' → 'Hvem er den mystiske Eric Norton?'
- ID 67: 'Watson-søsknene havner i en mystisk verden ' → 'Watson-søsknene havner i en mystisk verden'
- ID 72: 'Er statsadvokaten en morder? ' → 'Er statsadvokaten en morder?'
- ID 93: 'En vanskelig sak for politiet i Amsterdam ' → 'En vanskelig sak for politiet i Amsterdam'
- ID 97: 'Spennende teknothriller fra den kalde krigen ' → 'Spennende teknothriller fra den kalde krigen'
- ID 121: 'Evig aktuell og skremmende dystopi ' → 'Evig aktuell og skremmende dystopi'
- ID 170: 'Foreldreløse Joschko drømmer om å se verden ' → 'Foreldreløse Joschko drømmer om å se verden'
- ID 193: 'Norges nasjonalforbryter er på vill flukt ' → 'Norges nasjonalforbryter er på vill flukt'
- ID 202: 'En terroraksjon rammer Stortinget ' → 'En terroraksjon rammer Stortinget'
- ID 214: 'Johannes blir bortført – inn i TV-en! ' → 'Johannes blir bortført – inn i TV-en!'
- ID 239: 'Hva skjedde på festen for mer enn 20 år siden? ' → 'Hva skjedde på festen for mer enn 20 år siden?'
- ID 292: 'Elina er ensom og finner trøst i skogen ' → 'Elina er ensom og finner trøst i skogen'
- ID 327: 'En uventet gjest blir vitne til et mord ' → 'En uventet gjest blir vitne til et mord'
- ID 332: 'Et mystisk dødsfall, narkotika og sorte messer ' → 'Et mystisk dødsfall, narkotika og sorte messer'

### Persons (11 fixed)
- ID 1859: 'Terje Emberland ' → 'Terje Emberland'
- ID 2602: 'Judy Nyambura Karanja ' → 'Judy Nyambura Karanja'
- ID 2606: 'Jephte Mukuta ' → 'Jephte Mukuta'
- ID 2607: 'Elvic Kongolo ' → 'Elvic Kongolo'
- ID 2614: 'Anthony Kibet ' → 'Anthony Kibet'
- ID 2616: 'Mary Wairimu Thagichu ' → 'Mary Wairimu Thagichu'
- ID 2617: 'Lawrence Nyanzi ' → 'Lawrence Nyanzi'
- ID 2619: 'Kevin Mbugua ' → 'Kevin Mbugua'
- ID 2703: 'Åsmund Feidje. ' → 'Åsmund Feidje' (also had trailing period)
- ID 2970: ' Lillo-Stenberg' → 'Lillo-Stenberg'

---

## 2. Critical Field Issues

### NULL/Empty Titles
✅ **No issues found**
- All episodes have titles
- All persons have names

---

## 3. Truncated Descriptions (38 episodes)

Episodes with descriptions ending in "..." that may be cut off mid-sentence:

### Sample (showing first 10):
1. `ODRR62760207`: 'Dragsug' - "...et noe i sagnet om at tjernet drar folk til seg..."
2. `MKTT83005883`: 'Gjennom det svarte hullet' - "...det farligste oppdraget skal gå til Lestermann ..."
3. `MKTT83005583`: 'Forskningsskipet Jernstjernen' - "... et mønster som fører til Vegas, kompaniets by ..."
4. `MKTT94001594`: 'Den drepende løgnen' - "...hatt den tidligere, har nå lovet å fortelle alt..."
5. `MKTT94001494`: 'Døden på visitt' - "... Reinskau opp i TV5 med et særdeles viktig funn..."
6. `MKTT94001294`: 'Jakt på mordmotivet' - "... hennes gamle venn kriminalbetjent Reinskau opp..."
7. `MKTT94002394`: 'Farvel, min elskede' - "...edre enn Henrik Lønn til å takle hunndyr i pels..."
8. `MKTT94002194`: 'Den store søvnen' - "...som ligger bak en ung pikes merkelige oppførsel..."
9. `MKTT85000685`: 'Den hemmelighetsfulle arv: Den evige kamp' - "...åde mot Hermines hjerte og baron Kermars formue..."
10. `MKTT85000585`: 'Den hemmelighetsfulle arv: En sol går ned i Bretagne' - "... sine egne medhjelpere, noe Baccarat får erfare..."

**Action needed:** Manual review to determine if these are intentional cliffhangers or data truncation issues. If truncated, source data should be reviewed for complete descriptions.

---

## 4. Norwegian Title Capitalization (FALSE POSITIVE)

The following 7 titles were initially flagged as "all lowercase" but are actually **properly capitalized Norwegian titles** starting with special characters (Æ, Å, Ø) or numbers. **No action needed.**

- `FTEA00004789`: 'Ælle menneskja mine' (correctly starts with Æ)
- `FTEA00002180`: 'Århundrets kjærlighetssaga' (correctly starts with Å)
- `FTEA00005969`: 'Ærefrykt for livet' (correctly starts with Æ)
- `FTEA61001061`: 'Østersen og perlen' (correctly starts with Ø)
- `MKDR72020413`: 'Å ta farvel er å dø litt' (correctly starts with Å)
- `MKTT74006874`: 'Æresord' (correctly starts with Æ)
- `MKTT10001310`: '17. mai' (correctly starts with number)

---

## 5. Inconsistent Episode Numbering Patterns

Multiple patterns detected across the database:

### Pattern Distribution:
- **Colon format** (e.g., "1:2", "2:5"): 108 episodes
- **Parentheses format** (e.g., "(1:2)", "(4:9)"): 20 episodes
- **"Del" format** (e.g., "Del 1", "Del 2"): 2 episodes
- **Subtitle format** (e.g., "Title: Subtitle"): Many episodes

### Sample Episodes with Different Patterns:

**Colon format (most common):**
- Peer Gynt 1:2
- Peer Gynt 2:2
- Galskapens stillhet 1:2
- De unges forbund 1:5 through 5:5

**Parentheses format:**
- Knut Gribbs bedrifter – Isdronningen (1:2)
- Knut Gribbs bedrifter – Isdronningen (2:2)
- Bassenget (4:9)
- Forfølgelsen (5:9)

**Subtitle/series format:**
- Den lille heksen: Dansen går videre
- Den lille heksen: En svart søndag
- Den hemmelighetsfulle arv: De to brødre
- Farlig selskap: Bare en liten tilfeldighet

**Note:** This inconsistency reflects different eras and production practices. Standardization would require manual editorial decisions about which format to prefer, and may not be necessary if these reflect the original NRK titles.

---

## 6. Duplicate Person Records (CRITICAL)

Found 3 sets of duplicate person records that should be merged:

### Åsmund Feidje (2 records)
- **ID 775:** Åsmund Feidje (no metadata)
- **ID 2703:** Åsmund Feidje (no metadata)
- **Action:** Merge these records and update all `episode_persons` references
- **Note:** According to separate audit, these have 4 overlapping episodes

### Lars Norén (2 records)
- **ID 3117:** Lars Norén (1944-2021, no wikidata)
- **ID 3134:** Lars Norén (1944-2021, no wikidata)
- **Action:** Merge these records and update all `episode_persons` references
- **Note:** According to separate audit, both are orphaned (no episode associations)

### Bertolt Brecht (2 records)
- **ID 3094:** Bertolt Brecht (1898-1956, no wikidata)
- **ID 3210:** Bertolt Brecht (1898-1956, wikidata: Q38757)
- **Action:** Merge into ID 3210 (has wikidata), update all references

---

## 7. Duplicate Episode Titles (Expected)

Many episodes share the same title, representing different productions/versions of the same play:

### Top Duplicates:
- "Kometkameratene og den røde solen": 10 episodes
- "Annas jul": 10 episodes
- "Marie og julesnapperen": 9 episodes
- "Brand": 9 episodes
- "Agnes Cecilia": 9 episodes
- "Over de høie fjelle": 8 episodes
- "Spionen": 7 episodes
- "Olav og Ingunn": 7 episodes
- "Jane Eyre": 7 episodes
- "Matilda": 6 episodes

**Note:** This is expected for popular plays with multiple productions over the years. Should verify that episodes are correctly linked to the same `play_id` where appropriate.

---

## 8. No Encoding Issues Found

✅ **Good news:** No UTF-8 encoding issues detected (no Ã¦, Ã¸, Ã¥ character corruption)

---

## 9. No ALL CAPS Issues Found

✅ **No episodes with problematic ALL CAPS titles detected**

---

## 10. Additional Statistics

### Medium Distribution
- **Radio:** 1,757 episodes (74.2%)
- **TV:** 610 episodes (25.8%)

### Description Quality
- Episodes with descriptions ending in "...": 38 (1.6%)
- Episodes with very short descriptions (< 20 chars): 0
- Episodes with NULL descriptions: Not checked (may be acceptable for some episodes)

---

## Recommendations

### High Priority:
1. **Merge duplicate person records** (Åsmund Feidje, Lars Norén, Bertolt Brecht)
2. **Review 38 truncated descriptions** to determine if they need completion

### Medium Priority:
3. **Verify play_id linkage** for episodes with identical titles
4. **Consider standardizing episode numbering** format if consistency is desired

### Low Priority:
5. **Document the Norwegian title capitalization rules** in the application to prevent false positives in future audits

---

## SQL Queries for Follow-up

### Merge duplicate persons (example for Åsmund Feidje):
```sql
-- Update all references to use ID 775
UPDATE episode_persons SET person_id = 775 WHERE person_id = 2703;
-- Delete duplicate
DELETE FROM persons WHERE id = 2703;
```

### Find episodes that might need play_id verification:
```sql
SELECT title, COUNT(*) as count, GROUP_CONCAT(play_id) as play_ids
FROM episodes
GROUP BY title
HAVING COUNT(*) > 1 AND COUNT(DISTINCT play_id) > 1;
```

---

**Audit completed:** 2025-12-19
