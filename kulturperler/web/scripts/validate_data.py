#!/usr/bin/env python3
"""
Validate data integrity without building the database.

This is a fast check to ensure all cross-references are valid
and required fields are present before committing changes.
"""

import yaml
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).parent.parent / 'data'


def load_yaml(path):
    """Load YAML file."""
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_yaml_dir(dir_path):
    """Load all YAML files from a directory, returning dict keyed by filename."""
    data = {}
    for file in dir_path.glob('*.yaml'):
        content = load_yaml(file)
        data[file.name] = content
    return data


def validate():
    errors = []
    warnings = []

    print("Loading data...")

    # Load all entities
    persons = load_yaml_dir(DATA_DIR / 'persons')
    plays = load_yaml_dir(DATA_DIR / 'plays')
    episodes = load_yaml_dir(DATA_DIR / 'episodes')
    performances = load_yaml_dir(DATA_DIR / 'performances')
    nrk_programs = load_yaml_dir(DATA_DIR / 'nrk_about_programs')

    # Build ID sets for reference validation
    person_ids = {p['id'] for p in persons.values()}
    play_ids = {p['id'] for p in plays.values()}
    performance_ids = {p['id'] for p in performances.values()}

    print(f"  Loaded {len(persons)} persons, {len(plays)} plays, {len(episodes)} episodes, {len(performances)} performances")
    print()

    # Validate persons
    print("Validating persons...")
    for filename, person in persons.items():
        if not person.get('name'):
            errors.append(f"persons/{filename}: missing required field 'name'")
        if not person.get('id'):
            errors.append(f"persons/{filename}: missing required field 'id'")

    # Valid composer roles
    valid_composer_roles = {'composer', 'arranger', 'orchestrator', 'lyricist', 'adapter'}

    # Validate plays
    print("Validating plays...")
    for filename, play in plays.items():
        if not play.get('title'):
            errors.append(f"plays/{filename}: missing required field 'title'")
        if not play.get('id'):
            errors.append(f"plays/{filename}: missing required field 'id'")
        if play.get('playwright_id') and play['playwright_id'] not in person_ids:
            errors.append(f"plays/{filename}: playwright_id {play['playwright_id']} does not exist")
        # Validate composer_id (legacy single composer)
        if play.get('composer_id') and play['composer_id'] not in person_ids:
            errors.append(f"plays/{filename}: composer_id {play['composer_id']} does not exist")
        # Validate composers array (new multiple composers)
        for i, comp in enumerate(play.get('composers', [])):
            if not comp.get('person_id'):
                errors.append(f"plays/{filename}: composers[{i}] missing required field 'person_id'")
            elif comp['person_id'] not in person_ids:
                errors.append(f"plays/{filename}: composers[{i}].person_id {comp['person_id']} does not exist")
            if comp.get('role') and comp['role'] not in valid_composer_roles:
                warnings.append(f"plays/{filename}: composers[{i}].role '{comp['role']}' not in {valid_composer_roles}")

    # Validate performances
    print("Validating performances...")
    for filename, perf in performances.items():
        if not perf.get('id'):
            errors.append(f"performances/{filename}: missing required field 'id'")
        if perf.get('work_id') and perf['work_id'] not in play_ids:
            errors.append(f"performances/{filename}: work_id {perf['work_id']} does not exist")
        for i, credit in enumerate(perf.get('credits', [])):
            if credit.get('person_id') not in person_ids:
                errors.append(f"performances/{filename}: credit[{i}].person_id {credit.get('person_id')} does not exist")

    # Validate episodes
    print("Validating episodes...")
    for filename, episode in episodes.items():
        if not episode.get('prf_id'):
            errors.append(f"episodes/{filename}: missing required field 'prf_id'")
        if not episode.get('title'):
            errors.append(f"episodes/{filename}: missing required field 'title'")
        if episode.get('play_id') and episode['play_id'] not in play_ids:
            errors.append(f"episodes/{filename}: play_id {episode['play_id']} does not exist")
        if episode.get('performance_id') and episode['performance_id'] not in performance_ids:
            errors.append(f"episodes/{filename}: performance_id {episode['performance_id']} does not exist")
        for i, credit in enumerate(episode.get('credits', [])):
            if credit.get('person_id') not in person_ids:
                errors.append(f"episodes/{filename}: credit[{i}].person_id {credit.get('person_id')} does not exist")

    # Validate NRK about programs
    print("Validating NRK about programs...")
    for filename, prog in nrk_programs.items():
        if not prog.get('id'):
            errors.append(f"nrk_about_programs/{filename}: missing required field 'id'")
        if prog.get('person_id') and prog['person_id'] not in person_ids:
            errors.append(f"nrk_about_programs/{filename}: person_id {prog['person_id']} does not exist")

    # Check for duplicate IDs
    print("Checking for duplicates...")
    person_id_count = defaultdict(list)
    for filename, person in persons.items():
        person_id_count[person.get('id')].append(filename)
    for pid, files in person_id_count.items():
        if len(files) > 1:
            errors.append(f"Duplicate person id {pid}: {files}")

    play_id_count = defaultdict(list)
    for filename, play in plays.items():
        play_id_count[play.get('id')].append(filename)
    for pid, files in play_id_count.items():
        if len(files) > 1:
            errors.append(f"Duplicate play id {pid}: {files}")

    performance_id_count = defaultdict(list)
    for filename, perf in performances.items():
        performance_id_count[perf.get('id')].append(filename)
    for pid, files in performance_id_count.items():
        if len(files) > 1:
            errors.append(f"Duplicate performance id {pid}: {files}")

    # Report results
    print()
    if warnings:
        print(f"Warnings: {len(warnings)}")
        for warn in warnings[:20]:
            print(f"  ⚠️  {warn}")
        if len(warnings) > 20:
            print(f"  ... and {len(warnings) - 20} more warnings")
        print()

    if errors:
        print(f"VALIDATION FAILED: {len(errors)} error(s)")
        for err in errors[:50]:  # Limit output
            print(f"  ❌ {err}")
        if len(errors) > 50:
            print(f"  ... and {len(errors) - 50} more errors")
        return False
    else:
        print("✅ Validation passed!")
        print(f"  Persons: {len(persons)}")
        print(f"  Plays: {len(plays)}")
        print(f"  Episodes: {len(episodes)}")
        print(f"  Performances: {len(performances)}")
        print(f"  NRK About Programs: {len(nrk_programs)}")
        return True


if __name__ == '__main__':
    import sys
    success = validate()
    sys.exit(0 if success else 1)
