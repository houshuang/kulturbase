#!/usr/bin/env python3
"""
Fetch images from NRK API for programs missing image_url.
"""

import yaml
import requests
import time
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / 'data'
NRK_API_BASE = "https://psapi.nrk.no/programs"


def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_yaml(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def fetch_image_url(prf_id):
    """Fetch image URL from NRK API."""
    try:
        r = requests.get(f"{NRK_API_BASE}/{prf_id}", timeout=10)
        if r.status_code != 200:
            return None

        data = r.json()
        image = data.get('image', {})
        web_images = image.get('webImages', [])

        # Prefer 960px width, fall back to largest available
        for target_width in [960, 600, 1920, 300]:
            for img in web_images:
                if img.get('pixelWidth') == target_width:
                    return img.get('imageUrl')

        # If no match, return first available
        if web_images:
            return web_images[0].get('imageUrl')

        return None
    except Exception as e:
        print(f"  Error fetching {prf_id}: {e}")
        return None


def main():
    programs_dir = DATA_DIR / 'nrk_about_programs'

    # Find programs without images
    missing = []
    for f in sorted(programs_dir.glob('*.yaml')):
        prog = load_yaml(f)
        if not prog.get('image_url'):
            missing.append((f, prog))

    print(f"Found {len(missing)} programs without images")

    updated = 0
    not_found = 0

    for i, (filepath, prog) in enumerate(missing):
        prf_id = prog['id']
        print(f"[{i+1}/{len(missing)}] Fetching {prf_id}...", end=' ')

        image_url = fetch_image_url(prf_id)

        if image_url:
            prog['image_url'] = image_url
            save_yaml(filepath, prog)
            print(f"OK")
            updated += 1
        else:
            print(f"No image")
            not_found += 1

        # Rate limiting
        time.sleep(0.1)

    print()
    print(f"Results:")
    print(f"  Updated: {updated}")
    print(f"  No image found: {not_found}")


if __name__ == '__main__':
    main()
