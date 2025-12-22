#!/usr/bin/env python3
"""Fetch images for NRK about programs that are missing them."""

import yaml
import requests
from pathlib import Path
import time

DATA_DIR = Path('data/nrk_about_programs')

def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)

def save_yaml(path, data):
    with open(path, 'w') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

def fetch_image_url(program_id):
    """Fetch image URL from NRK API."""
    url = f"https://psapi.nrk.no/programs/{program_id}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            image = data.get('image', {})
            web_images = image.get('webImages', [])
            # Prefer 960px width
            for img in web_images:
                if img.get('pixelWidth') == 960:
                    return img.get('imageUrl')
            # Fall back to any image
            if web_images:
                return web_images[-1].get('imageUrl')  # Usually largest
        elif r.status_code == 404:
            print(f"  Not found: {program_id}")
        else:
            print(f"  Error {r.status_code} for {program_id}")
    except Exception as e:
        print(f"  Exception for {program_id}: {e}")
    return None

def main():
    # Find programs without images
    programs_without_images = []
    for yaml_file in DATA_DIR.glob('*.yaml'):
        data = load_yaml(yaml_file)
        if not data.get('image_url'):
            programs_without_images.append(yaml_file)

    print(f"Found {len(programs_without_images)} programs without images")

    updated = 0
    not_found = 0

    for i, yaml_file in enumerate(programs_without_images):
        data = load_yaml(yaml_file)
        program_id = data['id']

        print(f"[{i+1}/{len(programs_without_images)}] Fetching {program_id}...")

        image_url = fetch_image_url(program_id)
        if image_url:
            data['image_url'] = image_url
            save_yaml(yaml_file, data)
            print(f"  Updated with image")
            updated += 1
        else:
            not_found += 1

        # Rate limiting
        time.sleep(0.1)

    print(f"\nDone! Updated {updated}, not found {not_found}")

if __name__ == '__main__':
    main()
