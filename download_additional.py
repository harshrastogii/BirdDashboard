"""
NT Bird Acoustic Monitor — Download Additional Recordings
PRT840 IT Thesis | Charles Darwin University

Downloads additional recordings for weak species from Xeno-canto API v3.
- Willie Wagtail: 71 additional recordings (have 80, available 151)
- Helmeted Friarbird: 10 additional recordings (have 80, available 90)
"""

import os
import requests
import time
import json

KEY = "50ccb8cc85a01aa04adde72b4dc0d74b22e85092"
BASE_DIR = os.path.expanduser("~/BirdDashboard/training_data")

# Species to download additional recordings for
SPECIES = [
    {
        "name": "Willie Wagtail",
        "folder": "Willie_Wagtail",
        "query": "gen:Rhipidura+sp:leucophrys",
        "have": 80,
    },
    {
        "name": "Helmeted Friarbird",
        "folder": "Helmeted_Friarbird",
        "query": "gen:Philemon+sp:buceroides",
        "have": 80,
    },
]


def get_existing_ids(folder_path):
    """Get XC IDs of recordings we already have."""
    existing = set()
    if os.path.exists(folder_path):
        for f in os.listdir(folder_path):
            if f.endswith(".mp3"):
                # Extract XC ID from filename like "Willie_Wagtail_XC1234567.mp3"
                parts = f.replace(".mp3", "").split("_")
                for part in parts:
                    if part.startswith("XC"):
                        existing.add(part.replace("XC", ""))
                    elif part.isdigit() and len(part) > 4:
                        existing.add(part)
    return existing


def download_additional(species_info):
    """Download recordings we don't already have."""
    name = species_info["name"]
    folder = species_info["folder"]
    query = species_info["query"]
    folder_path = os.path.join(BASE_DIR, folder)
    os.makedirs(folder_path, exist_ok=True)

    print(f"\n{'=' * 60}")
    print(f"  {name}")
    print(f"{'=' * 60}")

    # Get existing IDs
    existing_ids = get_existing_ids(folder_path)
    existing_files = [f for f in os.listdir(folder_path) if f.endswith(".mp3")]
    print(f"  Existing recordings: {len(existing_files)}")
    print(f"  Existing IDs found: {len(existing_ids)}")

    # Fetch all recordings from API
    print(f"  Fetching recording list from Xeno-canto...")
    page = 1
    all_recordings = []

    while True:
        url = f"https://xeno-canto.org/api/3/recordings?query={query}&key={KEY}&page={page}"
        try:
            r = requests.get(url, timeout=30)
            data = r.json()
            recordings = data.get("recordings", [])
            all_recordings.extend(recordings)

            num_pages = int(data.get("numPages", 1))
            print(f"    Page {page}/{num_pages}: {len(recordings)} recordings")

            if page >= num_pages:
                break
            page += 1
            time.sleep(1)
        except Exception as e:
            print(f"    Error fetching page {page}: {e}")
            break

    print(f"  Total available: {len(all_recordings)}")

    # Filter out recordings we already have
    new_recordings = []
    for rec in all_recordings:
        rec_id = str(rec.get("id", ""))
        if rec_id not in existing_ids:
            new_recordings.append(rec)

    print(f"  New recordings to download: {len(new_recordings)}")

    if not new_recordings:
        print(f"  Nothing new to download!")
        return 0

    # Download new recordings
    downloaded = 0
    failed = 0

    for i, rec in enumerate(new_recordings):
        rec_id = rec.get("id", "unknown")
        file_url = rec.get("file", "")

        if not file_url:
            print(f"    [{i+1}/{len(new_recordings)}] XC{rec_id}: No download URL, skipping")
            failed += 1
            continue

        # Make sure URL has https
        if file_url.startswith("//"):
            file_url = "https:" + file_url

        filename = f"{folder}_XC{rec_id}.mp3"
        filepath = os.path.join(folder_path, filename)

        if os.path.exists(filepath):
            print(f"    [{i+1}/{len(new_recordings)}] XC{rec_id}: Already exists, skipping")
            continue

        try:
            print(f"    [{i+1}/{len(new_recordings)}] Downloading XC{rec_id}...", end=" ")
            audio_r = requests.get(file_url, timeout=60)

            if audio_r.status_code == 200 and len(audio_r.content) > 1000:
                with open(filepath, "wb") as f:
                    f.write(audio_r.content)
                size_kb = len(audio_r.content) / 1024
                print(f"OK ({size_kb:.0f} KB)")
                downloaded += 1
            else:
                print(f"Failed (status {audio_r.status_code}, size {len(audio_r.content)})")
                failed += 1

        except Exception as e:
            print(f"Error: {e}")
            failed += 1

        # Rate limit — be nice to Xeno-canto
        time.sleep(1.5)

    # Final count
    final_files = [f for f in os.listdir(folder_path) if f.endswith(".mp3")]
    print(f"\n  Summary for {name}:")
    print(f"    Downloaded: {downloaded}")
    print(f"    Failed: {failed}")
    print(f"    Total recordings now: {len(final_files)}")

    return downloaded


def main():
    print("=" * 60)
    print("  NT Bird Acoustic Monitor — Download Additional Recordings")
    print("  PRT840 IT Thesis | Charles Darwin University")
    print("=" * 60)

    total_downloaded = 0
    for species in SPECIES:
        total_downloaded += download_additional(species)

    print(f"\n{'=' * 60}")
    print(f"  DOWNLOAD COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Total new recordings downloaded: {total_downloaded}")
    print(f"\n  Next step: Retrain the model with the expanded dataset")
    print(f"  Run: python3 train_model_v4.py")


if __name__ == "__main__":
    main()
