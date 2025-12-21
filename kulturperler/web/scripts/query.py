#!/usr/bin/env python3
"""
CLI utility for querying the YAML data.

For complex queries, rebuild the database and use sqlite3 directly.
This utility is for quick lookups and data exploration.
"""

import yaml
import sys
import argparse
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / 'data'


def load_yaml(path):
    """Load YAML file."""
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_yaml_dir(dir_path):
    """Load all YAML files from a directory."""
    data = []
    for file in sorted(dir_path.glob('*.yaml')):
        content = load_yaml(file)
        content['_file'] = file.name
        data.append(content)
    return data


def format_person(p):
    """Format person for display."""
    years = ""
    if p.get('birth_year') or p.get('death_year'):
        years = f" ({p.get('birth_year', '?')}-{p.get('death_year', '?')})"
    return f"[{p['id']}] {p['name']}{years}"


def format_play(p, persons_by_id=None):
    """Format play for display."""
    playwright = ""
    if p.get('playwright_id') and persons_by_id:
        pw = persons_by_id.get(p['playwright_id'])
        if pw:
            playwright = f" by {pw['name']}"
    year = f" ({p['year_written']})" if p.get('year_written') else ""
    return f"[{p['id']}] {p['title']}{playwright}{year}"


def format_episode(e):
    """Format episode for display."""
    year = f" ({e['year']})" if e.get('year') else ""
    duration = ""
    if e.get('duration_seconds'):
        mins = e['duration_seconds'] // 60
        duration = f" [{mins}min]"
    return f"[{e['prf_id']}] {e['title']}{year}{duration}"


def cmd_find_person(args):
    """Find persons by name."""
    query = args.query.lower()
    persons = load_yaml_dir(DATA_DIR / 'persons')
    matches = [p for p in persons if query in p['name'].lower()]

    if not matches:
        print(f"No persons found matching '{args.query}'")
        return

    print(f"Found {len(matches)} person(s):")
    for p in matches[:args.limit]:
        print(f"  {format_person(p)}")
        if p.get('bio'):
            bio_preview = p['bio'][:100].replace('\n', ' ')
            print(f"    {bio_preview}...")


def cmd_find_play(args):
    """Find plays by title."""
    query = args.query.lower()
    plays = load_yaml_dir(DATA_DIR / 'plays')
    persons = load_yaml_dir(DATA_DIR / 'persons')
    persons_by_id = {p['id']: p for p in persons}

    matches = [p for p in plays if query in p['title'].lower()]

    if not matches:
        print(f"No plays found matching '{args.query}'")
        return

    print(f"Found {len(matches)} play(s):")
    for p in matches[:args.limit]:
        print(f"  {format_play(p, persons_by_id)}")
        if p.get('synopsis'):
            synopsis_preview = p['synopsis'][:100].replace('\n', ' ')
            print(f"    {synopsis_preview}...")


def cmd_show_person(args):
    """Show detailed info for a person."""
    path = DATA_DIR / 'persons' / f"{args.id}.yaml"
    if not path.exists():
        print(f"Person {args.id} not found")
        return

    p = load_yaml(path)
    print(f"Person: {p['name']}")
    print(f"  ID: {p['id']}")
    if p.get('birth_year'):
        print(f"  Born: {p['birth_year']}")
    if p.get('death_year'):
        print(f"  Died: {p['death_year']}")
    if p.get('nationality'):
        print(f"  Nationality: {p['nationality']}")
    if p.get('wikipedia_url'):
        print(f"  Wikipedia: {p['wikipedia_url']}")
    if p.get('sceneweb_url'):
        print(f"  Sceneweb: {p['sceneweb_url']}")
    if p.get('bio'):
        print(f"  Bio: {p['bio'][:500]}...")


def cmd_show_play(args):
    """Show detailed info for a play."""
    path = DATA_DIR / 'plays' / f"{args.id}.yaml"
    if not path.exists():
        print(f"Play {args.id} not found")
        return

    p = load_yaml(path)
    persons = load_yaml_dir(DATA_DIR / 'persons')
    persons_by_id = {per['id']: per for per in persons}

    print(f"Play: {p['title']}")
    print(f"  ID: {p['id']}")
    if p.get('original_title') and p['original_title'] != p['title']:
        print(f"  Original title: {p['original_title']}")
    if p.get('playwright_id'):
        pw = persons_by_id.get(p['playwright_id'])
        if pw:
            print(f"  Playwright: {pw['name']} [{p['playwright_id']}]")
    if p.get('year_written'):
        print(f"  Year written: {p['year_written']}")
    if p.get('wikipedia_url'):
        print(f"  Wikipedia: {p['wikipedia_url']}")
    if p.get('sceneweb_url'):
        print(f"  Sceneweb: {p['sceneweb_url']}")
    if p.get('synopsis'):
        print(f"  Synopsis: {p['synopsis']}")


def cmd_show_episode(args):
    """Show detailed info for an episode."""
    path = DATA_DIR / 'episodes' / f"{args.id}.yaml"
    if not path.exists():
        print(f"Episode {args.id} not found")
        return

    e = load_yaml(path)
    persons = load_yaml_dir(DATA_DIR / 'persons')
    persons_by_id = {per['id']: per for per in persons}

    print(f"Episode: {e['title']}")
    print(f"  PRF ID: {e['prf_id']}")
    if e.get('year'):
        print(f"  Year: {e['year']}")
    if e.get('duration_seconds'):
        mins = e['duration_seconds'] // 60
        print(f"  Duration: {mins} minutes")
    if e.get('medium'):
        print(f"  Medium: {e['medium']}")
    if e.get('nrk_url'):
        print(f"  NRK URL: {e['nrk_url']}")
    if e.get('play_id'):
        print(f"  Play ID: {e['play_id']}")
    if e.get('description'):
        print(f"  Description: {e['description'][:300]}...")

    credits = e.get('credits', [])
    if credits:
        print(f"\n  Credits ({len(credits)}):")
        # Group by role
        by_role = {}
        for c in credits:
            role = c.get('role', 'unknown')
            if role not in by_role:
                by_role[role] = []
            by_role[role].append(c)

        for role in ['playwright', 'director', 'actor', 'composer', 'other']:
            if role in by_role:
                print(f"    {role.title()}s:")
                for c in by_role[role][:10]:
                    person = persons_by_id.get(c['person_id'], {})
                    name = person.get('name', f"[{c['person_id']}]")
                    char = f" as {c['character_name']}" if c.get('character_name') else ""
                    print(f"      - {name}{char}")
                if len(by_role[role]) > 10:
                    print(f"      ... and {len(by_role[role]) - 10} more")


def cmd_stats(args):
    """Show statistics about the data."""
    persons = list((DATA_DIR / 'persons').glob('*.yaml'))
    plays = list((DATA_DIR / 'plays').glob('*.yaml'))
    episodes = list((DATA_DIR / 'episodes').glob('*.yaml'))
    performances = list((DATA_DIR / 'performances').glob('*.yaml'))
    nrk_programs = list((DATA_DIR / 'nrk_about_programs').glob('*.yaml'))

    print("Data Statistics:")
    print(f"  Persons: {len(persons)}")
    print(f"  Plays: {len(plays)}")
    print(f"  Episodes: {len(episodes)}")
    print(f"  Performances: {len(performances)}")
    print(f"  NRK About Programs: {len(nrk_programs)}")

    # Count plays with various enrichment
    plays_data = load_yaml_dir(DATA_DIR / 'plays')
    with_playwright = sum(1 for p in plays_data if p.get('playwright_id'))
    with_synopsis = sum(1 for p in plays_data if p.get('synopsis'))
    with_year = sum(1 for p in plays_data if p.get('year_written'))

    print(f"\n  Plays enrichment:")
    print(f"    With playwright: {with_playwright} ({100*with_playwright/len(plays_data):.1f}%)")
    print(f"    With synopsis: {with_synopsis} ({100*with_synopsis/len(plays_data):.1f}%)")
    print(f"    With year written: {with_year} ({100*with_year/len(plays_data):.1f}%)")


def cmd_list_plays(args):
    """List all plays."""
    plays = load_yaml_dir(DATA_DIR / 'plays')
    persons = load_yaml_dir(DATA_DIR / 'persons')
    persons_by_id = {p['id']: p for p in persons}

    if args.no_playwright:
        plays = [p for p in plays if not p.get('playwright_id')]
        print(f"Plays without playwright ({len(plays)}):")
    elif args.no_synopsis:
        plays = [p for p in plays if not p.get('synopsis')]
        print(f"Plays without synopsis ({len(plays)}):")
    else:
        print(f"All plays ({len(plays)}):")

    for p in plays[:args.limit]:
        print(f"  {format_play(p, persons_by_id)}")


def main():
    parser = argparse.ArgumentParser(description='Query kulturperler data')
    parser.add_argument('--limit', '-n', type=int, default=20, help='Limit results')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # find-person
    fp = subparsers.add_parser('find-person', help='Find persons by name')
    fp.add_argument('query', help='Search query')

    # find-play
    fpl = subparsers.add_parser('find-play', help='Find plays by title')
    fpl.add_argument('query', help='Search query')

    # show-person
    sp = subparsers.add_parser('show-person', help='Show person details')
    sp.add_argument('id', type=int, help='Person ID')

    # show-play
    spl = subparsers.add_parser('show-play', help='Show play details')
    spl.add_argument('id', type=int, help='Play ID')

    # show-episode
    se = subparsers.add_parser('show-episode', help='Show episode details')
    se.add_argument('id', help='Episode PRF ID')

    # stats
    subparsers.add_parser('stats', help='Show data statistics')

    # list-plays
    lp = subparsers.add_parser('list-plays', help='List plays')
    lp.add_argument('--no-playwright', action='store_true', help='Only plays without playwright')
    lp.add_argument('--no-synopsis', action='store_true', help='Only plays without synopsis')

    args = parser.parse_args()

    if args.command == 'find-person':
        cmd_find_person(args)
    elif args.command == 'find-play':
        cmd_find_play(args)
    elif args.command == 'show-person':
        cmd_show_person(args)
    elif args.command == 'show-play':
        cmd_show_play(args)
    elif args.command == 'show-episode':
        cmd_show_episode(args)
    elif args.command == 'stats':
        cmd_stats(args)
    elif args.command == 'list-plays':
        cmd_list_plays(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
