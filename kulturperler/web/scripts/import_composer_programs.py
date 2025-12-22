#!/usr/bin/env python3
"""
Import composer NRK programs from JSON into YAML files.

Source: /tmp/composer_nrk_programs.json
Target: data/nrk_about_programs/
"""

import json
import yaml
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / 'data'
SOURCE_FILE = Path('/tmp/composer_nrk_programs.json')


def load_person_mapping():
    """Build mapping from composer name to person_id."""
    persons_dir = DATA_DIR / 'persons'
    name_to_id = {}

    for f in persons_dir.glob('*.yaml'):
        with open(f) as fp:
            p = yaml.safe_load(fp)
            if p and p.get('name'):
                name_to_id[p['name'].lower()] = p['id']

    return name_to_id


def get_existing_programs():
    """Get set of existing program IDs."""
    programs_dir = DATA_DIR / 'nrk_about_programs'
    return {f.stem for f in programs_dir.glob('*.yaml')}


def save_yaml(path, data):
    """Save data as YAML file."""
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def main():
    print(f"Loading source data from {SOURCE_FILE}")
    with open(SOURCE_FILE) as f:
        data = json.load(f)

    # Combine both program categories
    all_programs = data.get('relevant_programs', []) + data.get('music_programs', [])
    print(f"  Total programs: {len(all_programs)}")

    # Load mappings
    name_to_id = load_person_mapping()
    existing = get_existing_programs()
    print(f"  Existing nrk_about_programs: {len(existing)}")

    # Build composer name to ID mapping for the searched composers
    composer_mapping = {}
    for composer in data.get('composers_searched', []):
        name = composer['name']
        lower_name = name.lower()
        if lower_name in name_to_id:
            composer_mapping[name] = name_to_id[lower_name]
        else:
            print(f"  WARNING: Composer not found: {name}")

    print(f"  Mapped {len(composer_mapping)} composers to person IDs")

    # Process programs
    output_dir = DATA_DIR / 'nrk_about_programs'
    created = 0
    skipped_existing = 0
    skipped_no_composer = 0
    seen_ids = set()

    for prog in all_programs:
        prf_id = prog['prf_id']

        # Skip duplicates within source
        if prf_id in seen_ids:
            continue
        seen_ids.add(prf_id)

        # Skip if already exists
        if prf_id in existing:
            skipped_existing += 1
            continue

        # Get person_id
        composer_name = prog.get('composer_name')
        person_id = composer_mapping.get(composer_name)
        if not person_id:
            skipped_no_composer += 1
            print(f"  Skipping {prf_id}: no person_id for '{composer_name}'")
            continue

        # Extract program_type and confidence from gemini_evaluation
        gemini_eval = prog.get('gemini_evaluation', {})
        program_type = gemini_eval.get('program_type', 'program')
        confidence = gemini_eval.get('confidence', 0.5)
        interest_score = int(confidence * 100)

        # Build YAML data
        yaml_data = {
            'id': prf_id,
            'person_id': person_id,
            'title': prog.get('title'),
            'description': prog.get('description'),
            'duration_seconds': prog.get('duration_seconds'),
            'year': prog.get('year'),
            'nrk_url': prog.get('nrk_url'),
            'image_url': prog.get('image_url'),
            'program_type': program_type,
            'interest_score': interest_score,
        }

        # Remove None values
        yaml_data = {k: v for k, v in yaml_data.items() if v is not None}

        # Save
        output_path = output_dir / f"{prf_id}.yaml"
        save_yaml(output_path, yaml_data)
        created += 1

    print()
    print(f"Results:")
    print(f"  Created: {created} new files")
    print(f"  Skipped (already exists): {skipped_existing}")
    print(f"  Skipped (no composer match): {skipped_no_composer}")
    print(f"  Total unique in source: {len(seen_ids)}")


if __name__ == '__main__':
    main()
