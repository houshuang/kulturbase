# Kulturperler Database Relationship Audit - Summary

**Audit Date**: 2025-12-19
**Database**: /Users/stian/src/nrk/kulturperler/web/static/kulturperler.db
**Review File**: /Users/stian/src/nrk/kulturperler/data/audit_review.md

---

## Executive Summary

The database relationship audit has been successfully completed. A total of **1,051 issues** were found and automatically fixed. All foreign key relationships are now valid, and the database passes all integrity checks.

### Issues Fixed

- **2 episodes** with invalid play_id references (set to NULL)
- **1,048 duplicate** episode_persons entries (removed)
- **1 invalid** performance_persons entry (deleted)

### Issues Requiring Manual Review

**0** - All issues were automatically resolved

---

## Detailed Audit Results

### 1. episode_persons with invalid episode_id
- **Result**: 0 issues found
- **Status**: Clean

### 2. episode_persons with invalid person_id
- **Result**: 0 issues found
- **Status**: Clean

### 3. episode_resources with invalid episode_id
- **Result**: 0 issues found
- **Status**: Clean

### 4. episode_resources with invalid resource_id
- **Result**: 0 issues found
- **Status**: Clean

### 5. plays with invalid playwright_id
- **Result**: 0 issues found
- **Status**: Clean

### 6. episodes with invalid play_id
- **Result**: 2 issues found and fixed
- **Action**: Set play_id to NULL for orphaned references
- **Fixed Episodes**:
  - `FTEA00006883`: 'Innledning' (play_id=493 -> NULL)
  - `FTEA01005182`: 'Innledning' (play_id=497 -> NULL)
- **Note**: Plays with IDs 493 and 497 do not exist in the database

### 7. Duplicate episode_persons entries
- **Result**: 1,048 duplicates found and removed
- **Action**: Removed duplicate entries, keeping only the first occurrence of each unique combination of (episode_id, person_id, role)
- **Affected Episodes**: Multiple episodes from series including:
  - MKDR series: 62020110, 62020210, 62020310, 62040112-612, 62140111-411, 62560112-212
  - MKTT series: 62030114-714, 62080117-317, 62090114-314, 72020113-413, 72030111-211, 72500116-616
  - OBDR and ODRR series episodes

### 8. performance_persons with invalid person_id
- **Result**: 1 issue found and fixed
- **Action**: Deleted orphaned performance_persons entry
- **Details**: Performance 103 ('Evig Natt') had a reference to non-existent person_id=1700. The performance already had correct playwright entries (person_id 1701, 1702), so the invalid entry (id=5892) was deleted.

---

## Additional Checks Performed

All relationship tables were verified for foreign key integrity:

| Table | Invalid episode_id | Invalid person_id | Invalid other refs | Status |
|-------|-------------------|-------------------|-------------------|---------|
| episode_persons | 0 | 0 | - | Clean |
| episode_resources | 0 | - | 0 (resource_id) | Clean |
| episode_tags | 0 | - | 0 (tag_id) | Clean |
| performance_persons | - | 0 | 0 (performance_id) | Clean |
| play_tags | - | - | 0 (play_id, tag_id) | Clean |
| play_resources | - | - | 0 (play_id, resource_id) | Clean |
| person_resources | - | 0 | 0 (resource_id) | Clean |

---

## Final Database Statistics

- **episode_persons**: 28,265 (after removing 1,048 duplicates)
- **episodes**: 2,367
- **persons**: 3,204
- **plays**: 854
- **episode_resources**: 522
- **external_resources**: 525
- **performances**: ~100+
- **performance_persons**: ~5,900+ (after removing 1 invalid entry)

---

## Verification

All fixes have been verified using:
1. Individual foreign key checks for each relationship
2. SQLite `PRAGMA foreign_key_check` (returns empty = all valid)
3. Manual verification of sample data

**Database Integrity**: All foreign key relationships are now valid and consistent.

---

## Files Modified

1. `/Users/stian/src/nrk/kulturperler/web/static/kulturperler.db` - Database with fixes applied
2. `/Users/stian/src/nrk/kulturperler/data/audit_review.md` - Detailed audit review (updated)
3. `/Users/stian/src/nrk/kulturperler/audit_fix.sql` - SQL script for future reference

---

## Recommendations

1. The database is now clean and ready for production use
2. Consider implementing foreign key constraints in the database schema if not already enabled
3. Monitor for duplicate entries during data import processes
4. The missing plays (IDs 493, 497) may need to be recreated if the episodes should reference them

---

## Next Steps

The database has passed all relationship audits. No manual intervention required.
