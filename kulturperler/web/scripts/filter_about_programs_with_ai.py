#!/usr/bin/env python3
"""
Filter about_programs using OpenAI GPT to identify irrelevant matches.

For each person with about_programs, asks GPT to identify which programs
are actually about that specific person vs coincidental name matches.
"""

import os
import ssl
import yaml
import asyncio
import aiohttp
import time
import certifi
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path('data')
PERSONS_DIR = DATA_DIR / 'persons'
ABOUT_PROGRAMS_DIR = DATA_DIR / 'nrk_about_programs'

OPENAI_KEY = os.getenv('OPENAI_KEY')
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

# Rate limiting: 10 requests per second
REQUESTS_PER_SECOND = 10
REQUEST_INTERVAL = 1.0 / REQUESTS_PER_SECOND


def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)


def load_all_persons():
    """Load all persons into a dict by ID."""
    persons = {}
    for f in PERSONS_DIR.glob('*.yaml'):
        try:
            p = load_yaml(f)
            persons[p['id']] = p
        except:
            pass
    return persons


def load_about_programs_by_person():
    """Load all about_programs grouped by person_id."""
    by_person = defaultdict(list)
    for f in ABOUT_PROGRAMS_DIR.glob('*.yaml'):
        try:
            prog = load_yaml(f)
            prog['_file'] = f
            if prog.get('person_id'):
                by_person[prog['person_id']].append(prog)
        except:
            pass
    return by_person


def build_prompt(person, programs):
    """Build the prompt for GPT."""
    person_info = f"""Person: {person.get('name')}
Birth year: {person.get('birth_year', 'unknown')}
Death year: {person.get('death_year', 'unknown')}
Bio: {person.get('bio', 'No bio available')[:500]}
"""

    programs_info = []
    for i, prog in enumerate(programs):
        desc = prog.get('description', '')[:300]
        programs_info.append(f"""[{prog['id']}] "{prog.get('title', 'Untitled')}"
Description: {desc}
Year: {prog.get('year', 'unknown')}""")

    programs_text = "\n\n".join(programs_info)

    return f"""You are reviewing NRK TV/radio programs that have been linked to a specific person.
Your task is to identify which programs are ACTUALLY about this person, vs programs that
coincidentally share a name or are about someone else entirely.

{person_info}

Programs linked to this person:

{programs_text}

For each program, respond with ONLY the program ID followed by YES (is about this person)
or NO (not about this person, wrong match).

Example format:
PROG001: YES
PROG002: NO
PROG003: YES

Be strict - only say YES if the program is clearly about this specific person (the author/artist),
not about:
- Different people with similar names
- Oil platforms, ships, or places named after the person
- Unrelated people who happen to share a first or last name
- General topics that just mention the name in passing

Respond with one line per program:"""


async def call_openai(session, prompt, semaphore):
    """Call OpenAI API with rate limiting."""
    async with semaphore:
        headers = {
            "Authorization": f"Bearer {OPENAI_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 1000
        }

        try:
            async with session.post(OPENAI_URL, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data['choices'][0]['message']['content']
                else:
                    error = await resp.text()
                    print(f"  API error {resp.status}: {error[:200]}")
                    return None
        except Exception as e:
            print(f"  Request error: {e}")
            return None
        finally:
            await asyncio.sleep(REQUEST_INTERVAL)


def parse_response(response, programs):
    """Parse GPT response to get YES/NO for each program."""
    if not response:
        return {}

    results = {}
    for line in response.strip().split('\n'):
        line = line.strip()
        if ':' in line:
            parts = line.split(':', 1)
            prog_id = parts[0].strip()
            answer = parts[1].strip().upper()
            if 'YES' in answer:
                results[prog_id] = True
            elif 'NO' in answer:
                results[prog_id] = False

    return results


async def process_person(session, semaphore, person, programs):
    """Process one person's about_programs."""
    if len(programs) == 0:
        return []

    prompt = build_prompt(person, programs)
    response = await call_openai(session, prompt, semaphore)

    if not response:
        print(f"  Failed to get response for {person.get('name')}")
        return []

    results = parse_response(response, programs)

    # Find programs to remove
    to_remove = []
    for prog in programs:
        prog_id = prog['id']
        if prog_id in results and results[prog_id] == False:
            to_remove.append(prog)

    return to_remove


async def main(dry_run=False):
    print("Loading data...")
    persons = load_all_persons()
    by_person = load_about_programs_by_person()

    # Filter to persons with multiple about_programs (more likely to have bad matches)
    persons_to_check = {
        pid: progs for pid, progs in by_person.items()
        if len(progs) >= 1 and pid in persons
    }

    print(f"Found {len(persons_to_check)} persons with about_programs to review")

    # Rate limiting semaphore
    semaphore = asyncio.Semaphore(REQUESTS_PER_SECOND)

    all_to_remove = []

    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for person_id, programs in persons_to_check.items():
            person = persons[person_id]
            tasks.append((person, programs, process_person(session, semaphore, person, programs)))

        # Process in batches to show progress
        batch_size = 50
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i+batch_size]
            print(f"\nProcessing batch {i//batch_size + 1}/{(len(tasks) + batch_size - 1)//batch_size}...")

            results = await asyncio.gather(*[t[2] for t in batch])

            for (person, programs, _), to_remove in zip(batch, results):
                if to_remove:
                    print(f"  {person.get('name')}: removing {len(to_remove)}/{len(programs)} programs")
                    for prog in to_remove:
                        print(f"    - {prog['id']}: {prog.get('title', 'Untitled')[:50]}")
                    all_to_remove.extend(to_remove)

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Summary:")
    print(f"  Total programs to remove: {len(all_to_remove)}")

    if not dry_run and all_to_remove:
        print("\nRemoving files...")
        for prog in all_to_remove:
            prog['_file'].unlink()
            print(f"  Removed: {prog['_file'].name}")

    return all_to_remove


if __name__ == '__main__':
    import sys
    dry_run = '--dry-run' in sys.argv
    asyncio.run(main(dry_run=dry_run))
