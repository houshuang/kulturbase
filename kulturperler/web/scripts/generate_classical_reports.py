#!/usr/bin/env python3
"""
Phase 6: Generate comprehensive text reports.

Creates human-readable reports organized by genre, language, etc.
Outputs: Multiple .txt files in output/
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

OUTPUT_DIR = Path(__file__).parent.parent / "output"
PERFORMANCES_FILE = OUTPUT_DIR / "classical_performances.json"
CLASSIFIED_FILE = OUTPUT_DIR / "classical_classified.json"
PLAY_LINKS_FILE = OUTPUT_DIR / "classical_play_links.json"


def format_duration(seconds):
    """Format duration in human-readable form."""
    if not seconds:
        return "?"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours}h{minutes}m"
    return f"{minutes}m"


def format_performance(perf, include_episodes=True):
    """Format a performance for text output."""
    lines = []

    work = perf.get('work_title') or 'Unknown Work'
    original = perf.get('work_title_original')
    composer = perf.get('composer') or 'Unknown Composer'
    genre = perf.get('genre', 'unknown')
    language = perf.get('performance_language', 'unknown')
    is_norwegian = perf.get('is_norwegian_translation', False)
    based_on = perf.get('based_on_literary_work')
    year = perf.get('year', '?')
    medium = perf.get('medium', 'tv').upper()
    duration = format_duration(perf.get('total_duration_seconds'))
    series = perf.get('series_title', '')

    lines.append(f"=== {work} ===")
    if original and original.lower() != work.lower():
        lines.append(f"Original title: {original}")
    lines.append(f"Composer: {composer}")
    lines.append(f"Genre: {genre}")

    if language != 'instrumental':
        if is_norwegian:
            lines.append(f"Language: NORWEGIAN (translated) *** HISTORICALLY SIGNIFICANT ***")
        else:
            lines.append(f"Language: {language}")
    else:
        lines.append(f"Language: Instrumental")

    if based_on:
        lines.append(f"Based on: {based_on}")

    # Play links
    play_links = perf.get('play_links', [])
    if play_links:
        lines.append(f"Linked to plays:")
        for link in play_links[:3]:
            lines.append(f"  -> #{link.get('play_id')}: {link.get('play_title')} by {link.get('playwright_name')}")

    lines.append("")
    lines.append(f"Performance ({year}, {medium}, {duration}):")
    lines.append(f"  Series: {series}")

    if include_episodes:
        episodes = perf.get('episodes', [])
        for ep in episodes:
            ep_title = ep.get('title', 'Untitled')
            ep_duration = format_duration(ep.get('duration_seconds'))
            is_intro = ep.get('is_introduction', False)
            part_num = ep.get('part_number')

            marker = "[INTRO] " if is_intro else f"[Part {part_num}] " if part_num else ""
            lines.append(f"    - {marker}{ep_title} [{ep_duration}]")
            lines.append(f"      ID: {ep.get('prf_id')}")
            lines.append(f"      URL: {ep.get('nrk_url')}")

    lines.append("")
    return "\n".join(lines)


def generate_genre_report(performances, genre, filename):
    """Generate report for a specific genre."""
    filtered = [p for p in performances if p.get('genre') == genre]

    if not filtered:
        return

    # Sort by work title, then year
    filtered.sort(key=lambda x: (x.get('work_title') or '', x.get('year') or 0))

    with open(OUTPUT_DIR / filename, 'w', encoding='utf-8') as f:
        f.write(f"# NRK {genre.upper()} PERFORMANCES\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Total: {len(filtered)} performances\n")
        f.write("=" * 60 + "\n\n")

        # Group by composer
        by_composer = defaultdict(list)
        for p in filtered:
            composer = p.get('composer') or 'Unknown'
            by_composer[composer].append(p)

        for composer in sorted(by_composer.keys()):
            f.write(f"\n{'='*60}\n")
            f.write(f"COMPOSER: {composer}\n")
            f.write(f"{'='*60}\n\n")

            for perf in by_composer[composer]:
                f.write(format_performance(perf))
                f.write("\n" + "-" * 40 + "\n\n")

    print(f"  Written: {filename} ({len(filtered)} performances)")


def generate_norwegian_translations_report(performances):
    """Generate report for Norwegian translations."""
    filtered = [p for p in performances if p.get('is_norwegian_translation')]

    if not filtered:
        print("  No Norwegian translations found")
        return

    filtered.sort(key=lambda x: (x.get('genre') or '', x.get('composer') or '', x.get('year') or 0))

    with open(OUTPUT_DIR / "report_norwegian_translations.txt", 'w', encoding='utf-8') as f:
        f.write("# NORWEGIAN TRANSLATIONS OF FOREIGN WORKS\n")
        f.write("# (Historically Significant Performances)\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Total: {len(filtered)} performances\n")
        f.write("=" * 60 + "\n\n")

        for perf in filtered:
            f.write(format_performance(perf))
            f.write("\n" + "-" * 40 + "\n\n")

    print(f"  Written: report_norwegian_translations.txt ({len(filtered)} performances)")


def generate_documentaries_report(classified_data):
    """Generate report for documentaries and discussions."""
    documentaries = classified_data.get('documentaries', [])

    if not documentaries:
        print("  No documentaries found")
        return

    with open(OUTPUT_DIR / "report_about_programs.txt", 'w', encoding='utf-8') as f:
        f.write("# PROGRAMS ABOUT CLASSICAL MUSIC\n")
        f.write("# (Documentaries, Discussions, Educational Content)\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Total: {len(documentaries)} programs\n")
        f.write("=" * 60 + "\n\n")

        for item in documentaries:
            cls = item.get('classification', {})
            f.write(f"=== {item.get('title')} ===\n")
            f.write(f"Series: {item.get('series_title')}\n")
            f.write(f"Year: {item.get('year', '?')}\n")
            f.write(f"Duration: {format_duration(item.get('duration_seconds'))}\n")
            f.write(f"Description: {item.get('description', '')[:200]}\n")
            if cls.get('work_title'):
                f.write(f"About: {cls.get('work_title')} by {cls.get('composer')}\n")
            f.write(f"URL: {item.get('nrk_url')}\n")
            f.write(f"ID: {item.get('prf_id')}\n")
            f.write("\n" + "-" * 40 + "\n\n")

    print(f"  Written: report_about_programs.txt ({len(documentaries)} programs)")


def generate_multipart_report(performances):
    """Generate report for multi-part performances."""
    multipart = [p for p in performances if p.get('part_count', 1) > 1 or p.get('has_introduction')]

    if not multipart:
        print("  No multi-part performances found")
        return

    multipart.sort(key=lambda x: -(x.get('part_count', 1)))

    with open(OUTPUT_DIR / "report_multipart.txt", 'w', encoding='utf-8') as f:
        f.write("# MULTI-PART PERFORMANCES\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Total: {len(multipart)} performances\n")
        f.write("=" * 60 + "\n\n")

        for perf in multipart:
            f.write(format_performance(perf))
            f.write("\n" + "-" * 40 + "\n\n")

    print(f"  Written: report_multipart.txt ({len(multipart)} performances)")


def generate_play_links_report(play_links_data):
    """Generate report for performances linked to plays."""
    linked = play_links_data.get('linked_performances', [])

    if not linked:
        print("  No play links found")
        return

    with open(OUTPUT_DIR / "report_play_links.txt", 'w', encoding='utf-8') as f:
        f.write("# PERFORMANCES LINKED TO PLAYS\n")
        f.write("# (Ballets and Operas based on plays in the database)\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Total: {len(linked)} performances\n")
        f.write("=" * 60 + "\n\n")

        for perf in linked:
            f.write(format_performance(perf))
            f.write("\n" + "-" * 40 + "\n\n")

    print(f"  Written: report_play_links.txt ({len(linked)} performances)")


def generate_expiring_soon_report(performances):
    """Generate report for content expiring soon (1-2 years)."""
    now = datetime.now()
    threshold_2y = now + timedelta(days=730)

    expiring = []
    for perf in performances:
        for ep in perf.get('episodes', []):
            # Note: We'd need expiry info in the episode data
            # For now, skip this since we filtered to 1+ year in extraction
            pass

    # For now, just create an empty placeholder
    with open(OUTPUT_DIR / "report_expiring_soon.txt", 'w', encoding='utf-8') as f:
        f.write("# CONTENT EXPIRING SOON\n")
        f.write("# (Available for 1-2 years only - prioritize for archival)\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("\n")
        f.write("Note: All content in the main dataset has been filtered to have 1+ year availability.\n")
        f.write("This report would list content expiring in the next 1-2 years if that data were tracked.\n")

    print(f"  Written: report_expiring_soon.txt (placeholder)")


def generate_summary_report(performances, classified_data):
    """Generate overall summary report."""
    stats = classified_data.get('statistics', {})
    perf_count = len(performances)

    # Count by genre
    genre_counts = defaultdict(int)
    for p in performances:
        genre_counts[p.get('genre', 'unknown')] += 1

    # Count by composer
    composer_counts = defaultdict(int)
    for p in performances:
        composer_counts[p.get('composer') or 'Unknown'] += 1

    # Count Norwegian translations
    norwegian_trans = sum(1 for p in performances if p.get('is_norwegian_translation'))

    # Count by year decade
    decade_counts = defaultdict(int)
    for p in performances:
        year = p.get('year')
        if year:
            decade = (year // 10) * 10
            decade_counts[f"{decade}s"] += 1

    with open(OUTPUT_DIR / "report_summary.txt", 'w', encoding='utf-8') as f:
        f.write("# CLASSICAL MUSIC CONTENT - SUMMARY REPORT\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("=" * 60 + "\n\n")

        f.write("## OVERVIEW\n")
        f.write(f"Total episodes processed: {stats.get('total_input', 0)}\n")
        f.write(f"Classical performances: {stats.get('classical_performances', 0)}\n")
        f.write(f"Documentaries/discussions: {stats.get('documentaries', 0)}\n")
        f.write(f"Introductions: {stats.get('introductions', 0)}\n")
        f.write(f"Not classical: {stats.get('not_classical', 0)}\n")
        f.write(f"\nGrouped performances: {perf_count}\n")
        f.write(f"Norwegian translations: {norwegian_trans}\n\n")

        f.write("## BY GENRE\n")
        for genre, count in sorted(genre_counts.items(), key=lambda x: -x[1]):
            f.write(f"  {genre}: {count}\n")
        f.write("\n")

        f.write("## TOP COMPOSERS\n")
        for composer, count in sorted(composer_counts.items(), key=lambda x: -x[1])[:20]:
            f.write(f"  {composer}: {count}\n")
        f.write("\n")

        f.write("## BY DECADE\n")
        for decade, count in sorted(decade_counts.items()):
            f.write(f"  {decade}: {count}\n")
        f.write("\n")

        f.write("## FILES GENERATED\n")
        for report_file in sorted(OUTPUT_DIR.glob("report_*.txt")):
            f.write(f"  - {report_file.name}\n")

    print(f"  Written: report_summary.txt")


def main():
    print("=" * 60)
    print("Phase 6: Generating Reports")
    print("=" * 60)

    # Load data
    performances = []
    classified_data = {}
    play_links_data = {}

    if PERFORMANCES_FILE.exists():
        with open(PERFORMANCES_FILE) as f:
            data = json.load(f)
            performances = data.get('performances', [])
        print(f"Loaded {len(performances)} performances")
    else:
        print(f"WARNING: {PERFORMANCES_FILE} not found")

    if CLASSIFIED_FILE.exists():
        with open(CLASSIFIED_FILE) as f:
            classified_data = json.load(f)
        print(f"Loaded classification data")
    else:
        print(f"WARNING: {CLASSIFIED_FILE} not found")

    if PLAY_LINKS_FILE.exists():
        with open(PLAY_LINKS_FILE) as f:
            play_links_data = json.load(f)
        print(f"Loaded play links data")

    print("\nGenerating reports...")

    # Generate genre-specific reports
    print("\n[1/8] Genre reports...")
    generate_genre_report(performances, 'opera', 'report_operas.txt')
    generate_genre_report(performances, 'operetta', 'report_operettas.txt')
    generate_genre_report(performances, 'ballet', 'report_ballets.txt')
    generate_genre_report(performances, 'symphony', 'report_symphonies.txt')
    generate_genre_report(performances, 'orchestral', 'report_orchestral.txt')
    generate_genre_report(performances, 'concerto', 'report_concertos.txt')
    generate_genre_report(performances, 'chamber', 'report_chamber.txt')

    print("\n[2/8] Norwegian translations...")
    generate_norwegian_translations_report(performances)

    print("\n[3/8] Documentaries and discussions...")
    generate_documentaries_report(classified_data)

    print("\n[4/8] Multi-part performances...")
    generate_multipart_report(performances)

    print("\n[5/8] Play links...")
    generate_play_links_report(play_links_data)

    print("\n[6/8] Expiring content...")
    generate_expiring_soon_report(performances)

    print("\n[7/8] Summary report...")
    generate_summary_report(performances, classified_data)

    # Full performance list
    print("\n[8/8] Full performance list...")
    with open(OUTPUT_DIR / "report_all_performances.txt", 'w', encoding='utf-8') as f:
        f.write("# ALL CLASSICAL PERFORMANCES\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Total: {len(performances)} performances\n")
        f.write("=" * 60 + "\n\n")

        for perf in sorted(performances, key=lambda x: (x.get('genre') or '', x.get('work_title') or '')):
            f.write(format_performance(perf))
            f.write("\n" + "-" * 40 + "\n\n")

    print(f"  Written: report_all_performances.txt ({len(performances)} performances)")

    print("\n" + "=" * 60)
    print("REPORT GENERATION COMPLETE")
    print("=" * 60)
    print(f"\nAll reports written to: {OUTPUT_DIR}")

    # List generated files
    print("\nGenerated files:")
    for f in sorted(OUTPUT_DIR.glob("report_*.txt")):
        size = f.stat().st_size
        print(f"  {f.name} ({size:,} bytes)")


if __name__ == "__main__":
    main()
