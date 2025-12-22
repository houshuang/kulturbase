#!/usr/bin/env python3
"""
Fetch missing NRK episode images via PSAPI and update YAML files.
Tracks progress in a file to allow resuming if interrupted.
"""

import os
import sys
import json
import time
import requests
from pathlib import Path

EPISODES_DIR = Path(__file__).parent.parent / "data" / "episodes"
PROGRESS_FILE = Path(__file__).parent / ".image_fetch_progress.json"

def load_progress():
    """Load progress from file."""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {"completed": [], "failed": [], "not_found": []}

def save_progress(progress):
    """Save progress to file."""
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)

def find_episodes_without_images():
    """Find all NRK episodes without image_url."""
    episodes = []
    for yaml_file in EPISODES_DIR.glob("*.yaml"):
        content = yaml_file.read_text()
        lines = content.split("\n")

        # Check if it's NRK source and has no image_url
        is_nrk = any(line.strip() == "source: nrk" for line in lines)
        has_image = any(line.strip().startswith("image_url:") for line in lines)

        if is_nrk and not has_image:
            # Extract prf_id from first line
            for line in lines:
                if line.startswith("prf_id:"):
                    prf_id = line.split(":", 1)[1].strip()
                    episodes.append((yaml_file, prf_id))
                    break

    return episodes

def fetch_image_url(prf_id):
    """Fetch image URL from NRK PSAPI."""
    url = f"https://psapi.nrk.no/playback/metadata/program/{prf_id}"
    headers = {
        "Accept": "application/json",
        "User-Agent": "Kulturperler/1.0"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()

        # Try various image paths
        preplay = data.get("preplay", {})
        poster = preplay.get("poster", {})

        # Get the best quality image
        images = poster.get("images", [])
        for img in images:
            if img.get("width", 0) >= 800:
                return img.get("url")

        # Fallback to any image
        if images:
            return images[-1].get("url")

        # Try alternative path
        if "posterImage" in data:
            return data["posterImage"]

        return None

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return None
        raise
    except Exception as e:
        print(f"  Error: {e}")
        return None

def update_yaml_with_image(yaml_file, image_url):
    """Add image_url to the YAML file."""
    content = yaml_file.read_text()
    lines = content.split("\n")

    # Find the right place to insert image_url (after duration_seconds if exists, otherwise before nrk_url)
    new_lines = []
    inserted = False

    for i, line in enumerate(lines):
        new_lines.append(line)

        if not inserted:
            # Insert after duration_seconds
            if line.startswith("duration_seconds:"):
                new_lines.append(f"image_url: {image_url}")
                inserted = True
            # Or before nrk_url if no duration
            elif line.startswith("nrk_url:") and not inserted:
                # Insert before nrk_url
                new_lines.pop()  # Remove the nrk_url line we just added
                new_lines.append(f"image_url: {image_url}")
                new_lines.append(line)  # Add nrk_url back
                inserted = True

    # If still not inserted, add at end
    if not inserted:
        # Remove trailing empty lines
        while new_lines and not new_lines[-1].strip():
            new_lines.pop()
        new_lines.append(f"image_url: {image_url}")
        new_lines.append("")

    yaml_file.write_text("\n".join(new_lines))

def main():
    print("Finding NRK episodes without images...")
    episodes = find_episodes_without_images()
    print(f"Found {len(episodes)} episodes to process")

    progress = load_progress()
    completed_ids = set(progress["completed"])
    failed_ids = set(progress["failed"])
    not_found_ids = set(progress["not_found"])

    # Filter out already processed
    to_process = [(f, prf_id) for f, prf_id in episodes
                  if prf_id not in completed_ids
                  and prf_id not in failed_ids
                  and prf_id not in not_found_ids]

    print(f"Already processed: {len(completed_ids)} completed, {len(failed_ids)} failed, {len(not_found_ids)} not found")
    print(f"Remaining to process: {len(to_process)}")

    if not to_process:
        print("Nothing to do!")
        return

    for i, (yaml_file, prf_id) in enumerate(to_process, 1):
        print(f"[{i}/{len(to_process)}] {prf_id}...", end=" ", flush=True)

        try:
            image_url = fetch_image_url(prf_id)

            if image_url:
                update_yaml_with_image(yaml_file, image_url)
                progress["completed"].append(prf_id)
                print(f"✓ Found image")
            else:
                progress["not_found"].append(prf_id)
                print("✗ No image available")

        except Exception as e:
            progress["failed"].append(prf_id)
            print(f"✗ Error: {e}")

        save_progress(progress)

        # Be nice to the API
        time.sleep(0.3)

    print(f"\nDone! Completed: {len(progress['completed'])}, Not found: {len(progress['not_found'])}, Failed: {len(progress['failed'])}")

if __name__ == "__main__":
    main()
