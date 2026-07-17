"""
Avian Observatory — Xeno-canto Dataset Downloader (v2)
PRT840 IT Thesis | Charles Darwin University
Uses Xeno-canto API v3 with tag-based queries.
Downloads audio recordings + full metadata for 25 NT bird species.
"""

import requests
import os
import csv
import time
import json

# === Xeno-canto API v3 Key ===
API_KEY = "50ccb8cc85a01aa04adde72b4dc0d74b22e85092"

# === 25 Target NT Bird Species ===
# Format: (common_name, genus, species, conservation_status, habitat_group)
SPECIES = [
    # Threatened / Near-threatened (6)
    ("Gouldian Finch", "Erythrura", "gouldiae", "Endangered", "threatened"),
    ("Hooded Parrot", "Psephotellus", "dissimilis", "Near Threatened", "threatened"),
    ("Partridge Pigeon", "Geophaps", "smithii", "Vulnerable", "threatened"),
    ("Red Goshawk", "Erythrotriorchis", "radiatus", "Vulnerable", "threatened"),
    ("Masked Owl", "Tyto", "novaehollandiae", "Vulnerable", "threatened"),
    ("Bush Stone-curlew", "Burhinus", "grallarius", "Near Threatened", "threatened"),
    # Common Iconic (9)
    ("Laughing Kookaburra", "Dacelo", "novaeguineae", "Least Concern", "common"),
    ("Sulphur-crested Cockatoo", "Cacatua", "galerita", "Least Concern", "common"),
    ("Rainbow Bee-eater", "Merops", "ornatus", "Least Concern", "common"),
    ("Willie Wagtail", "Rhipidura", "leucophrys", "Least Concern", "common"),
    ("Magpie Goose", "Anseranas", "semipalmata", "Least Concern", "common"),
    ("Blue-winged Kookaburra", "Dacelo", "leachii", "Least Concern", "common"),
    ("Galah", "Eolophus", "roseicapilla", "Least Concern", "common"),
    ("Red-tailed Black-Cockatoo", "Calyptorhynchus", "banksii", "Least Concern", "common"),
    ("Tawny Frogmouth", "Podargus", "strigoides", "Least Concern", "common"),
    # Habitat / Seasonal Indicators (10)
    ("Great Bowerbird", "Chlamydera", "nuchalis", "Least Concern", "habitat"),
    ("Pheasant Coucal", "Centropus", "phasianinus", "Least Concern", "habitat"),
    ("Channel-billed Cuckoo", "Scythrops", "novaehollandiae", "Least Concern", "habitat"),
    ("Torresian Crow", "Corvus", "orru", "Least Concern", "habitat"),
    ("Black Kite", "Milvus", "migrans", "Least Concern", "habitat"),
    ("Rainbow Lorikeet", "Trichoglossus", "haematodus", "Least Concern", "habitat"),
    ("Barking Owl", "Ninox", "connivens", "Least Concern", "habitat"),
    ("Azure Kingfisher", "Ceyx", "azureus", "Least Concern", "habitat"),
    ("Zebra Finch", "Taeniopygia", "guttata", "Least Concern", "habitat"),
    ("Diamond Dove", "Geopelia", "cuneata", "Least Concern", "habitat"),
]

TARGET_PER_SPECIES = 80
BASE_DIR = os.path.expanduser("~/BirdDashboard/training_data")
METADATA_FILE = os.path.join(BASE_DIR, "dataset_metadata.csv")


def search_api_v3(genus, species_name, page=1):
    """Search Xeno-canto API v3 using tag-based query."""
    url = f"https://xeno-canto.org/api/3/recordings?query=gen:{genus}+sp:{species_name}&key={API_KEY}&page={page}"
    headers = {"User-Agent": "NT-Bird-Acoustic-Monitor/1.0 (CDU Research)"}
    
    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json()
        else:
            print(f"    API error {r.status_code}: {r.text[:200]}")
            return None
    except Exception as e:
        print(f"    Request error: {e}")
        return None


def download_recording(xc_id, save_path):
    """Download a single recording from Xeno-canto by ID."""
    url = f"https://xeno-canto.org/{xc_id}/download"
    headers = {"User-Agent": "NT-Bird-Acoustic-Monitor/1.0 (CDU Research)"}
    
    try:
        r = requests.get(url, allow_redirects=True, headers=headers, timeout=60)
        if len(r.content) > 5000:
            with open(save_path, "wb") as f:
                f.write(r.content)
            return len(r.content)
        else:
            return 0
    except Exception as e:
        print(f"      Download error for XC{xc_id}: {e}")
        return 0


def process_species(common_name, genus, species_name, conservation_status, habitat_group):
    """Search API and download recordings for a single species."""
    folder_name = common_name.replace(" ", "_").replace("-", "_").replace("'", "")
    species_dir = os.path.join(BASE_DIR, folder_name)
    os.makedirs(species_dir, exist_ok=True)
    
    scientific = f"{genus} {species_name}"
    print(f"\n{'='*60}")
    print(f"  {common_name} ({scientific})")
    print(f"  Status: {conservation_status} | Group: {habitat_group}")
    print(f"{'='*60}")
    
    # Check existing downloads
    existing = [f for f in os.listdir(species_dir) if f.endswith(".mp3")]
    if len(existing) >= TARGET_PER_SPECIES:
        print(f"  Already have {len(existing)} recordings, skipping.")
        return len(existing), []
    
    # Search API v3
    print(f"  Searching Xeno-canto API v3...")
    all_recordings = []
    
    data = search_api_v3(genus, species_name, page=1)
    if not data:
        print(f"  WARNING: API search failed for {common_name}")
        return len(existing), []
    
    num_total = int(data.get("numRecordings", 0))
    num_pages = int(data.get("numPages", 1))
    print(f"  Found {num_total} recordings ({num_pages} pages)")
    
    if num_total == 0:
        print(f"  WARNING: No recordings available for {common_name}")
        return len(existing), []
    
    # Collect recordings from API (prefer quality A and B)
    all_recordings.extend(data.get("recordings", []))
    
    # Get more pages if needed
    for page in range(2, min(num_pages + 1, 6)):
        if len(all_recordings) >= TARGET_PER_SPECIES:
            break
        time.sleep(0.5)
        page_data = search_api_v3(genus, species_name, page=page)
        if page_data and "recordings" in page_data:
            all_recordings.extend(page_data["recordings"])
    
    # Sort by quality (A first, then B, C, D, E)
    quality_order = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "": 5}
    all_recordings.sort(key=lambda r: quality_order.get(r.get("q", ""), 5))
    
    # Download recordings
    needed = TARGET_PER_SPECIES - len(existing)
    to_download = all_recordings[:needed]
    
    print(f"  Have {len(existing)}, downloading {len(to_download)} more...")
    
    downloaded = 0
    metadata_rows = []
    
    for i, rec in enumerate(to_download):
        xc_id = rec["id"]
        fname = f"{folder_name}_XC{xc_id}.mp3"
        fpath = os.path.join(species_dir, fname)
        
        # Skip if already exists
        if os.path.exists(fpath) and os.path.getsize(fpath) > 5000:
            downloaded += 1
            metadata_rows.append(build_metadata_row(rec, common_name, scientific,
                                                      conservation_status, habitat_group,
                                                      fname, folder_name, os.path.getsize(fpath)))
            continue
        
        # Download
        size = download_recording(xc_id, fpath)
        if size > 0:
            downloaded += 1
            metadata_rows.append(build_metadata_row(rec, common_name, scientific,
                                                      conservation_status, habitat_group,
                                                      fname, folder_name, size))
            if downloaded % 10 == 0:
                print(f"    Downloaded {downloaded}/{len(to_download)}...")
        else:
            if os.path.exists(fpath):
                os.remove(fpath)
        
        # Rate limiting
        time.sleep(1)
    
    total = len(existing) + downloaded
    print(f"  Done! {downloaded} new, {total} total recordings")
    return total, metadata_rows


def build_metadata_row(rec, common_name, scientific, status, group, fname, folder, size):
    """Build a metadata dict from an API recording object."""
    return {
        "common_name": common_name,
        "scientific_name": scientific,
        "conservation_status": status,
        "habitat_group": group,
        "xc_id": rec.get("id", ""),
        "quality": rec.get("q", ""),
        "recordist": rec.get("rec", ""),
        "country": rec.get("cnt", ""),
        "latitude": rec.get("lat", ""),
        "longitude": rec.get("lng", ""),
        "date": rec.get("date", ""),
        "time": rec.get("time", ""),
        "type": rec.get("type", ""),
        "length": rec.get("length", ""),
        "filename": fname,
        "folder": folder,
        "file_size_bytes": size,
        "xc_url": f"https://xeno-canto.org/{rec.get('id', '')}",
    }


def main():
    print("=" * 60)
    print("  Avian Observatory — Dataset Downloader v2")
    print("  PRT840 IT Thesis | Charles Darwin University")
    print("  Using Xeno-canto API v3")
    print("=" * 60)
    print(f"\nTarget: {TARGET_PER_SPECIES} recordings per species")
    print(f"Species: {len(SPECIES)}")
    print(f"Save to: {BASE_DIR}")
    
    os.makedirs(BASE_DIR, exist_ok=True)
    
    all_metadata = []
    summary = []
    
    for common_name, genus, sp, status, group in SPECIES:
        count, metadata = process_species(common_name, genus, sp, status, group)
        all_metadata.extend(metadata)
        summary.append((common_name, status, count))
    
    # Save master metadata CSV
    if all_metadata:
        fieldnames = ["common_name", "scientific_name", "conservation_status",
                       "habitat_group", "xc_id", "quality", "recordist", "country",
                       "latitude", "longitude", "date", "time", "type", "length",
                       "filename", "folder", "file_size_bytes", "xc_url"]
        with open(METADATA_FILE, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_metadata)
        print(f"\nMetadata saved to: {METADATA_FILE}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("  DOWNLOAD SUMMARY")
    print("=" * 60)
    total_files = 0
    for name, status, count in summary:
        tag = f"[{status}]" if status != "Least Concern" else ""
        print(f"  {name:.<40} {count:>4} files  {tag}")
        total_files += count
    
    print(f"\n  TOTAL: {total_files} recordings across {len(SPECIES)} species")
    
    total_size = 0
    for root, dirs, files in os.walk(BASE_DIR):
        for f in files:
            total_size += os.path.getsize(os.path.join(root, f))
    print(f"  Disk usage: {total_size / (1024*1024):.1f} MB")
    print(f"\n  Dataset ready at: {BASE_DIR}")


if __name__ == "__main__":
    main()
