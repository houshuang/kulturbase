#!/usr/bin/env python3
"""
Audit script for kulturperler database content quality issues.
Performs auto-fixes and generates a review file for uncertain issues.
"""

import sqlite3
import re
from datetime import datetime

DB_PATH = "/Users/stian/src/nrk/kulturperler/web/static/kulturperler.db"
REVIEW_FILE = "/Users/stian/src/nrk/kulturperler/data/audit_review.md"

def normalize_whitespace(text):
    """Remove extra whitespace, leading/trailing spaces."""
    if not text:
        return text
    # Replace multiple spaces with single space
    text = re.sub(r' {2,}', ' ', text)
    # Strip leading/trailing whitespace
    text = text.strip()
    return text

def fix_encoding_issues(text):
    """Fix common UTF-8 encoding problems."""
    if not text:
        return text
    replacements = {
        'Ã¦': 'æ',
        'Ã¸': 'ø',
        'Ã¥': 'å',
        'Ã\x86': 'Æ',
        'Ã\x98': 'Ø',
        'Ã\x85': 'Å',
        'Ã©': 'é',
        'Ã¼': 'ü',
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    issues_fixed = 0
    issues_for_review = []

    print("=" * 70)
    print("KULTURPERLER DATABASE QUALITY AUDIT")
    print("=" * 70)
    print(f"Database: {DB_PATH}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    # Get counts
    cursor.execute("SELECT COUNT(*) FROM episodes")
    total_episodes = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM plays")
    total_plays = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM persons")
    total_persons = cursor.fetchone()[0]

    print(f"Total records: {total_episodes} episodes, {total_plays} plays, {total_persons} persons")
    print()

    # ========================================================================
    # 1. ENCODING ISSUES
    # ========================================================================
    print("1. CHECKING FOR ENCODING ISSUES...")
    print("-" * 70)

    # Check episodes
    cursor.execute("""
        SELECT prf_id, title FROM episodes
        WHERE title LIKE '%Ã%' OR title LIKE '%â%' OR title LIKE '%Â%'
    """)
    encoding_episodes = cursor.fetchall()

    # Check plays
    cursor.execute("""
        SELECT id, title FROM plays
        WHERE title LIKE '%Ã%' OR title LIKE '%â%' OR title LIKE '%Â%'
    """)
    encoding_plays = cursor.fetchall()

    # Check persons
    cursor.execute("""
        SELECT id, name FROM persons
        WHERE name LIKE '%Ã%' OR name LIKE '%â%' OR name LIKE '%Â%'
    """)
    encoding_persons = cursor.fetchall()

    for prf_id, title in encoding_episodes:
        fixed = fix_encoding_issues(title)
        if fixed != title:
            cursor.execute("UPDATE episodes SET title = ? WHERE prf_id = ?", (fixed, prf_id))
            print(f"  FIXED episode {prf_id}: '{title}' -> '{fixed}'")
            issues_fixed += 1

    for play_id, title in encoding_plays:
        fixed = fix_encoding_issues(title)
        if fixed != title:
            cursor.execute("UPDATE plays SET title = ? WHERE id = ?", (fixed, play_id))
            print(f"  FIXED play {play_id}: '{title}' -> '{fixed}'")
            issues_fixed += 1

    for person_id, name in encoding_persons:
        fixed = fix_encoding_issues(name)
        if fixed != name:
            cursor.execute("UPDATE persons SET name = ? WHERE id = ?", (fixed, person_id))
            print(f"  FIXED person {person_id}: '{name}' -> '{fixed}'")
            issues_fixed += 1

    if encoding_episodes or encoding_plays or encoding_persons:
        print(f"  Total encoding issues fixed: {len(encoding_episodes) + len(encoding_plays) + len(encoding_persons)}")
    else:
        print("  No encoding issues found.")
    print()

    # ========================================================================
    # 2. WHITESPACE ISSUES
    # ========================================================================
    print("2. CHECKING FOR WHITESPACE ISSUES...")
    print("-" * 70)

    # Episodes with whitespace issues
    cursor.execute("""
        SELECT prf_id, title FROM episodes
        WHERE title LIKE '%  %' OR title LIKE ' %' OR title LIKE '% '
    """)
    ws_episodes = cursor.fetchall()

    for prf_id, title in ws_episodes:
        fixed = normalize_whitespace(title)
        if fixed != title:
            cursor.execute("UPDATE episodes SET title = ? WHERE prf_id = ?", (fixed, prf_id))
            print(f"  FIXED episode {prf_id}: '{title}' -> '{fixed}'")
            issues_fixed += 1

    # Plays with whitespace issues
    cursor.execute("""
        SELECT id, title FROM plays
        WHERE title LIKE '%  %' OR title LIKE ' %' OR title LIKE '% '
    """)
    ws_plays = cursor.fetchall()

    for play_id, title in ws_plays:
        fixed = normalize_whitespace(title)
        if fixed != title:
            cursor.execute("UPDATE plays SET title = ? WHERE id = ?", (fixed, play_id))
            print(f"  FIXED play {play_id}: '{title}' -> '{fixed}'")
            issues_fixed += 1

    # Persons with whitespace issues
    cursor.execute("""
        SELECT id, name FROM persons
        WHERE name LIKE '%  %' OR name LIKE ' %' OR name LIKE '% '
    """)
    ws_persons = cursor.fetchall()

    for person_id, name in ws_persons:
        fixed = normalize_whitespace(name)
        if fixed != name:
            cursor.execute("UPDATE persons SET name = ? WHERE id = ?", (fixed, person_id))
            print(f"  FIXED person {person_id}: '{name}' -> '{fixed}'")
            issues_fixed += 1

    if ws_episodes or ws_plays or ws_persons:
        print(f"  Total whitespace issues fixed: {len(ws_episodes) + len(ws_plays) + len(ws_persons)}")
    else:
        print("  No whitespace issues found.")
    print()

    # ========================================================================
    # 3. NULL/EMPTY CRITICAL FIELDS
    # ========================================================================
    print("3. CHECKING FOR NULL/EMPTY CRITICAL FIELDS...")
    print("-" * 70)

    # Episodes with NULL/empty titles (CRITICAL)
    cursor.execute("SELECT prf_id FROM episodes WHERE title IS NULL OR title = ''")
    null_episode_titles = cursor.fetchall()

    if null_episode_titles:
        print(f"  CRITICAL: {len(null_episode_titles)} episodes with NULL/empty titles!")
        issues_for_review.append({
            'type': 'CRITICAL',
            'description': f'{len(null_episode_titles)} episodes with NULL/empty titles',
            'items': [f"Episode {prf_id}" for prf_id, in null_episode_titles]
        })
    else:
        print("  OK: No episodes with NULL/empty titles.")

    # Persons with NULL/empty names (CRITICAL)
    cursor.execute("SELECT id FROM persons WHERE name IS NULL OR name = ''")
    null_person_names = cursor.fetchall()

    if null_person_names:
        print(f"  CRITICAL: {len(null_person_names)} persons with NULL/empty names!")
        issues_for_review.append({
            'type': 'CRITICAL',
            'description': f'{len(null_person_names)} persons with NULL/empty names',
            'items': [f"Person ID {pid}" for pid, in null_person_names]
        })
    else:
        print("  OK: No persons with NULL/empty names.")
    print()

    # ========================================================================
    # 4. VERY SHORT DESCRIPTIONS
    # ========================================================================
    print("4. CHECKING FOR VERY SHORT DESCRIPTIONS...")
    print("-" * 70)

    cursor.execute("""
        SELECT prf_id, title, description, LENGTH(description) as len
        FROM episodes
        WHERE description IS NOT NULL AND LENGTH(description) < 20
        ORDER BY LENGTH(description)
    """)
    short_descs = cursor.fetchall()

    if short_descs:
        print(f"  Found {len(short_descs)} episodes with descriptions < 20 characters")
        # Only report significant ones (less than 10 chars)
        very_short = [d for d in short_descs if d[3] < 10]
        if very_short:
            issues_for_review.append({
                'type': 'SHORT_DESCRIPTION',
                'description': f'{len(very_short)} episodes with descriptions < 10 characters',
                'items': [f"{prf_id}: '{title}' - '{desc}' ({length} chars)"
                         for prf_id, title, desc, length in very_short[:20]]
            })
            print(f"  Flagged {len(very_short)} very short descriptions (< 10 chars) for review")
    else:
        print("  No very short descriptions found.")
    print()

    # ========================================================================
    # 5. TRUNCATED DESCRIPTIONS
    # ========================================================================
    print("5. CHECKING FOR TRUNCATED DESCRIPTIONS...")
    print("-" * 70)

    cursor.execute("""
        SELECT prf_id, title, description
        FROM episodes
        WHERE description LIKE '%...'
    """)
    truncated = cursor.fetchall()

    if truncated:
        print(f"  Found {len(truncated)} episodes with descriptions ending in '...'")
        # Report a sample for review
        issues_for_review.append({
            'type': 'TRUNCATED_DESCRIPTION',
            'description': f'{len(truncated)} episodes with descriptions ending in "..."',
            'items': [f"{prf_id}: '{title}' - Description ends with: ...{desc[-50:]}"
                     for prf_id, title, desc in truncated[:20]]
        })
    else:
        print("  No truncated descriptions found.")
    print()

    # ========================================================================
    # 6. ALL CAPS OR ALL LOWERCASE TITLES
    # ========================================================================
    print("6. CHECKING FOR ALL CAPS OR ALL LOWERCASE TITLES...")
    print("-" * 70)

    # Check for ALL CAPS (excluding short titles and those with special chars)
    cursor.execute("""
        SELECT prf_id, title FROM episodes
        WHERE title = UPPER(title)
        AND LENGTH(title) > 5
        AND title NOT LIKE '%:%'
    """)
    caps_titles = cursor.fetchall()

    if caps_titles:
        print(f"  Found {len(caps_titles)} ALL CAPS titles")
        issues_for_review.append({
            'type': 'ALL_CAPS',
            'description': f'{len(caps_titles)} ALL CAPS episode titles',
            'items': [f"{prf_id}: '{title}'" for prf_id, title in caps_titles[:20]]
        })
    else:
        print("  No ALL CAPS titles found.")

    # Check for all lowercase (but Norwegian starting letters like æ, å, ø are OK)
    cursor.execute("""
        SELECT prf_id, title FROM episodes
        WHERE title = LOWER(title)
        AND LENGTH(title) > 5
        AND SUBSTR(title, 1, 1) NOT IN ('æ', 'å', 'ø')
    """)
    lower_titles = cursor.fetchall()

    if lower_titles:
        print(f"  Found {len(lower_titles)} all lowercase titles")
        issues_for_review.append({
            'type': 'ALL_LOWERCASE',
            'description': f'{len(lower_titles)} all lowercase episode titles',
            'items': [f"{prf_id}: '{title}'" for prf_id, title in lower_titles[:20]]
        })
    else:
        print("  No problematic all lowercase titles found.")
    print()

    # ========================================================================
    # 7. INCONSISTENT NAMING PATTERNS
    # ========================================================================
    print("7. CHECKING FOR INCONSISTENT EPISODE NUMBERING...")
    print("-" * 70)

    # Find various patterns
    patterns = {
        'colon': "title LIKE '%:%'",
        'del': "title LIKE '%Del %'",
        'part': "title LIKE '%Part %'",
        'parens': "title LIKE '%(%)%'",
    }

    pattern_counts = {}
    for pattern_name, where_clause in patterns.items():
        cursor.execute(f"SELECT COUNT(*) FROM episodes WHERE {where_clause}")
        count = cursor.fetchone()[0]
        pattern_counts[pattern_name] = count

    print(f"  Episode numbering patterns found:")
    for pattern_name, count in pattern_counts.items():
        print(f"    - {pattern_name}: {count} episodes")

    # Get sample of each for review
    cursor.execute("""
        SELECT prf_id, title FROM episodes
        WHERE title LIKE '%:%' OR title LIKE '%Del %'
           OR title LIKE '%Part %' OR title LIKE '%(%)%'
        ORDER BY title
        LIMIT 50
    """)
    pattern_samples = cursor.fetchall()

    if pattern_samples:
        issues_for_review.append({
            'type': 'INCONSISTENT_NUMBERING',
            'description': 'Mixed episode numbering patterns detected',
            'items': [f"{prf_id}: '{title}'" for prf_id, title in pattern_samples]
        })
    print()

    # ========================================================================
    # COMMIT AND GENERATE REVIEW FILE
    # ========================================================================
    conn.commit()
    conn.close()

    print("=" * 70)
    print("AUDIT SUMMARY")
    print("=" * 70)
    print(f"Total issues auto-fixed: {issues_fixed}")
    print(f"Total issues flagged for review: {len(issues_for_review)}")
    print()

    # Write review file
    if issues_for_review:
        with open(REVIEW_FILE, 'w', encoding='utf-8') as f:
            f.write(f"# Kulturperler Database Audit Review\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            f.write(f"## Summary\n\n")
            f.write(f"- Auto-fixed issues: {issues_fixed}\n")
            f.write(f"- Issues requiring review: {len(issues_for_review)}\n\n")

            for issue in issues_for_review:
                f.write(f"## {issue['type']}\n\n")
                f.write(f"{issue['description']}\n\n")
                for item in issue['items']:
                    f.write(f"- {item}\n")
                f.write("\n")

        print(f"Review file written to: {REVIEW_FILE}")
    else:
        print("No issues requiring review. No review file generated.")

    print()
    print("AUDIT COMPLETE")

if __name__ == "__main__":
    main()
