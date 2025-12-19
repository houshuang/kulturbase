-- Database Audit and Fix Script
-- Generated: 2025-12-19
-- Database: kulturperler.db

.print "================================"
.print "DATABASE RELATIONSHIP AUDIT"
.print "================================"
.print ""

-- 1. Check and fix episode_persons with invalid episode_id
.print "1. Checking episode_persons with invalid episode_id..."
SELECT COUNT(*) as orphaned_episode_refs FROM episode_persons ep
WHERE NOT EXISTS (SELECT 1 FROM episodes e WHERE e.prf_id = ep.episode_id);

DELETE FROM episode_persons
WHERE NOT EXISTS (SELECT 1 FROM episodes e WHERE e.prf_id = episode_id);

.print "   ✓ Deleted orphaned episode_persons (invalid episode_id)"
.print ""

-- 2. Check and fix episode_persons with invalid person_id
.print "2. Checking episode_persons with invalid person_id..."
SELECT COUNT(*) as orphaned_person_refs FROM episode_persons ep
WHERE NOT EXISTS (SELECT 1 FROM persons p WHERE p.id = ep.person_id);

DELETE FROM episode_persons
WHERE NOT EXISTS (SELECT 1 FROM persons p WHERE p.id = person_id);

.print "   ✓ Deleted orphaned episode_persons (invalid person_id)"
.print ""

-- 3. Check and fix episode_resources with invalid episode_id
.print "3. Checking episode_resources with invalid episode_id..."
SELECT COUNT(*) as orphaned_episode_resource_refs FROM episode_resources er
WHERE NOT EXISTS (SELECT 1 FROM episodes e WHERE e.prf_id = er.episode_id);

DELETE FROM episode_resources
WHERE NOT EXISTS (SELECT 1 FROM episodes e WHERE e.prf_id = episode_id);

.print "   ✓ Deleted orphaned episode_resources (invalid episode_id)"
.print ""

-- 4. Check and fix episode_resources with invalid resource_id
.print "4. Checking episode_resources with invalid resource_id..."
SELECT COUNT(*) as orphaned_resource_refs FROM episode_resources er
WHERE NOT EXISTS (SELECT 1 FROM external_resources r WHERE r.id = er.resource_id);

DELETE FROM episode_resources
WHERE NOT EXISTS (SELECT 1 FROM external_resources r WHERE r.id = resource_id);

.print "   ✓ Deleted orphaned episode_resources (invalid resource_id)"
.print ""

-- 5. Report plays with invalid playwright_id (do not auto-fix)
.print "5. Checking plays with invalid playwright_id..."
SELECT COUNT(*) as plays_with_invalid_playwright FROM plays p
WHERE playwright_id IS NOT NULL
AND NOT EXISTS (SELECT 1 FROM persons per WHERE per.id = p.playwright_id);

.print "   ⚠ No auto-fix applied (needs review)"
.print ""

-- 6. Fix episodes with invalid play_id
.print "6. Checking episodes with invalid play_id..."
.print "   Episodes to fix:"
SELECT '   - ' || prf_id || ': ' || title || ' (play_id=' || play_id || ')'
FROM episodes
WHERE play_id IS NOT NULL
AND NOT EXISTS (SELECT 1 FROM plays p WHERE p.id = play_id);

UPDATE episodes
SET play_id = NULL
WHERE play_id IS NOT NULL
AND NOT EXISTS (SELECT 1 FROM plays p WHERE p.id = play_id);

.print "   ✓ Set play_id to NULL for orphaned references"
.print ""

-- 7. Fix duplicate episode_persons entries
.print "7. Checking duplicate episode_persons entries..."
.print "   Duplicate count before fix:"
SELECT COUNT(*) - COUNT(DISTINCT episode_id || '|' || person_id || '|' || COALESCE(role, '')) as duplicates
FROM episode_persons;

-- Keep only the first occurrence of each duplicate
DELETE FROM episode_persons
WHERE id NOT IN (
    SELECT MIN(id)
    FROM episode_persons
    GROUP BY episode_id, person_id, role
);

.print "   ✓ Removed duplicate episode_persons entries"
.print ""
.print "================================"
.print "AUDIT COMPLETE"
.print "================================"
