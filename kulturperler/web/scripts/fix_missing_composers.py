#!/usr/bin/env python3
"""
Fix works that have wikidata_id but missing composer_id.

Fetches composer from Wikidata (P86 property) and links to persons table.
"""

import yaml
import requests
import time
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / 'data'
RATE_LIMIT = 0.2


def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_yaml(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def get_wikidata_entity(qid):
    """Get full Wikidata entity data."""
    url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
    headers = {'User-Agent': 'Kulturperler/1.0 (https://kulturperler.no)'}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return data.get('entities', {}).get(qid)
    except Exception:
        pass
    return None


def get_composer_qid(entity):
    """Get composer QID from P86 property."""
    claims = entity.get('claims', {})
    if 'P86' not in claims:
        return None

    for claim in claims['P86']:
        mainsnak = claim.get('mainsnak', {})
        datavalue = mainsnak.get('datavalue', {})
        if datavalue.get('type') == 'wikibase-entityid':
            return datavalue.get('value', {}).get('id')
    return None


def get_label(entity, lang='en'):
    """Get label from Wikidata entity."""
    labels = entity.get('labels', {})
    if lang in labels:
        return labels[lang].get('value')
    if 'en' in labels:
        return labels['en'].get('value')
    if 'no' in labels:
        return labels['no'].get('value')
    return None


def load_persons_by_wikidata():
    """Load persons indexed by wikidata_id."""
    index = {}  # wikidata_id -> person_id
    for f in (DATA_DIR / 'persons').glob('*.yaml'):
        p = load_yaml(f)
        if p and p.get('wikidata_id'):
            index[p['wikidata_id']] = p['id']
    return index


def load_persons_by_name():
    """Load persons indexed by normalized name."""
    index = {}  # normalized_name -> person_id
    for f in (DATA_DIR / 'persons').glob('*.yaml'):
        p = load_yaml(f)
        if p:
            name = p.get('normalized_name') or p.get('name', '').lower()
            if name:
                index[name] = p['id']
    return index


def get_next_person_id():
    """Get the next available person ID."""
    max_id = 0
    for f in (DATA_DIR / 'persons').glob('*.yaml'):
        p = load_yaml(f)
        if p:
            max_id = max(max_id, p['id'])
    return max_id + 1


def create_composer(name, wikidata_id):
    """Create a new composer person entry."""
    person_id = get_next_person_id()
    person = {
        'id': person_id,
        'name': name,
        'normalized_name': name.lower(),
        'wikidata_id': wikidata_id,
    }
    path = DATA_DIR / 'persons' / f'{person_id}.yaml'
    save_yaml(path, person)
    print(f"  Created person {person_id}: {name}")
    return person_id


def main():
    print("Fixing works missing composer_id...")

    # Load indexes
    persons_by_wikidata = load_persons_by_wikidata()
    persons_by_name = load_persons_by_name()
    print(f"Loaded {len(persons_by_wikidata)} persons with wikidata_id")

    # Find works with wikidata_id but no composer_id
    works_to_fix = []
    for f in sorted((DATA_DIR / 'plays').glob('*.yaml')):
        w = load_yaml(f)
        if w and w.get('category') == 'konsert':
            if w.get('wikidata_id') and not w.get('composer_id'):
                works_to_fix.append({
                    'id': w['id'],
                    'wikidata_id': w['wikidata_id'],
                    'title': w.get('title', ''),
                    'file': f,
                    'data': w,
                })

    print(f"Found {len(works_to_fix)} works to fix")

    stats = {
        'fixed': 0,
        'created_composers': 0,
        'no_composer_found': 0,
    }

    for i, work in enumerate(works_to_fix):
        if i % 50 == 0:
            print(f"Processing {i+1}/{len(works_to_fix)}...")

        work_qid = work['wikidata_id']

        # Get work entity from Wikidata
        entity = get_wikidata_entity(work_qid)
        time.sleep(RATE_LIMIT)

        if not entity:
            continue

        # Get composer QID
        composer_qid = get_composer_qid(entity)
        if not composer_qid:
            stats['no_composer_found'] += 1
            continue

        # Check if composer exists in our persons table
        composer_id = persons_by_wikidata.get(composer_qid)

        if not composer_id:
            # Composer not found, need to create
            composer_entity = get_wikidata_entity(composer_qid)
            time.sleep(RATE_LIMIT)

            if composer_entity:
                composer_name = get_label(composer_entity)
                if composer_name:
                    # Check if person exists by name
                    composer_id = persons_by_name.get(composer_name.lower())

                    if not composer_id:
                        # Create new composer
                        composer_id = create_composer(composer_name, composer_qid)
                        persons_by_wikidata[composer_qid] = composer_id
                        persons_by_name[composer_name.lower()] = composer_id
                        stats['created_composers'] += 1

        if composer_id:
            # Update work with composer_id
            work['data']['composer_id'] = composer_id
            save_yaml(work['file'], work['data'])
            stats['fixed'] += 1
            print(f"  [{work['id']}] {work['title'][:40]} -> composer {composer_id}")

    print(f"\nResults:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == '__main__':
    main()
