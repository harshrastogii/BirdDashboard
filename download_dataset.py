"""
Avian Observatory — Xeno-canto Dataset Downloader
PRT840 IT Thesis | Charles Darwin University
Downloads audio recordings + metadata for 25 NT bird species from Xeno-canto.
Uses direct download URLs (API v2 is retired, v3 requires key).
"""

import requests
import os
import csv
import time
import re
from urllib.parse import quote

# === 25 Target NT Bird Species ===
# Format: (common_name, scientific_name, conservation_status, habitat_group)
SPECIES = [
    # Threatened / Near-threatened (6)
    ("Gouldian Finch", "Erythrura gouldiae", "Endangered", "threatened"),
    ("Hooded Parrot", "Psephotellus dissimilis", "Near Threatened", "threatened"),
    ("Partridge Pigeon", "Geophaps smithii", "Vulnerable", "threatened"),
    ("Red Goshawk", "Erythrotriorchis radiatus", "Vulnerable", "threatened"),
    ("Masked Owl", "Tyto novaehollandiae", "Vulnerable", "threatened"),
    ("Bush Stone-curlew", "Burhinus grallarius", "Near Threatened", "threatened"),
    # Common Iconic (9)
    ("Laughing Kookaburra", "Dacelo novaeguineae", "Least Concern", "common"),
    ("Sulphur-crested Cockatoo", "Cacatua galerita", "Least Concern", "common"),
    ("Rainbow Bee-eater", "Merops ornatus", "Least Concern", "common"),
    ("Willie Wagtail", "Rhipidura leucophrys", "Least Concern", "common"),
    ("Magpie Goose", "Anseranas semipalmata", "Least Concern", "common"),
    ("Blue-winged Kookaburra", "Dacelo leachii", "Least Concern", "common"),
    ("Galah", "Eolophus roseicapilla", "Least Concern", "common"),
    ("Red-tailed Black-Cockatoo", "Calyptorhynchus banksii", "Least Concern", "common"),
    ("Tawny Frogmouth", "Podargus strigoides", "Least Concern", "common"),
    # Habitat / Seasonal Indicators (10)
    ("Great Bowerbird", "Chlamydera nuchalis", "Least Concern", "habitat"),
    ("Pheasant Coucal", "Centropus phasianinus", "Least Concern", "habitat"),
    ("Channel-billed Cuckoo", "Scythrops novaehollandiae", "Least Concern", "habitat"),
    ("Torresian Crow", "Corvus orru", "Least Concern", "habitat"),
    ("Black Kite", "Milvus migrans", "Least Concern", "habitat"),
    ("Rainbow Lorikeet", "Trichoglossus haematodus", "Least Concern", "habitat"),
    ("Barking Owl", "Ninox connivens", "Least Concern", "habitat"),
    ("Azure Kingfisher", "Ceyx azureus", "Least Concern", "habitat"),
    ("Zebra Finch", "Taeniopygia guttata", "Least Concern", "habitat"),
    ("Diamond Dove", "Geopelia cuneata", "Least Concern", "habitat"),
]

# How many recordings to download per species (aim for 80, accept whatever is available)
TARGET_PER_SPECIES = 80

# Base directories
BASE_DIR = os.path.expanduser("~/BirdDashboard/training_data")
METADATA_FILE = os.path.join(BASE_DIR, "dataset_metadata.csv")


def search_xeno_canto(scientific_name, page=1):
    """Search Xeno-canto for recordings of a species.
    Tries API v2 first (may still work for search), falls back to scraping.
    """
    # Try the search endpoint — even though v2 downloads are dead, search may work
    # Using the website's internal JSON endpoint
    query = quote(scientific_name)
    url = f"https://xeno-canto.org/api/2/recordings?query={query}&page={page}"
    
    headers = {"User-Agent": "Mozilla/5.0 (Avian Observatory - CDU Research)"}
    
    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            data = r.json()
            return data
        else:
            print(f"    API returned {r.status_code}, trying alternative search...")
            return None
    except Exception as e:
        print(f"    Search error: {e}")
        return None


def search_via_website(scientific_name):
    """Fallback: scrape recording IDs from the Xeno-canto website."""
    genus, species = scientific_name.split(" ", 1)
    url = f"https://xeno-canto.org/species/{genus}-{species}"
    headers = {"User-Agent": "Mozilla/5.0 (Avian Observatory - CDU Research)"}
    
    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code != 200:
            return []
        
        # Extract recording IDs from the page (they appear as /XXXXXX links)
        ids = re.findall(r'href="/(\d{4,7})"', r.text)
        # Remove duplicates while preserving order
        seen = set()
        unique_ids = []
        for rid in ids:
            if rid not in seen:
                seen.add(rid)
                unique_ids.append(rid)
        return unique_ids
    except Exception as e:
        print(f"    Website scrape error: {e}")
        return []


def download_recording(xc_id, save_path):
    """Download a single recording from Xeno-canto by ID."""
    url = f"https://xeno-canto.org/{xc_id}/download"
    headers = {"User-Agent": "Mozilla/5.0 (Avian Observatory - CDU Research)"}
    
    try:
        r = requests.get(url, allow_redirects=True, headers=headers, timeout=60)
        if len(r.content) > 5000:  # Valid audio file should be > 5KB
            with open(save_path, "wb") as f:
                f.write(r.content)
            return len(r.content)
        else:
            return 0
    except Exception as e:
        print(f"      Download error for XC{xc_id}: {e}")
        return 0


def get_recording_metadata(xc_id):
    """Try to get metadata for a recording from the website."""
    # We'll store basic metadata; full metadata would need API v3
    return {
        "xc_id": xc_id,
        "url": f"https://xeno-canto.org/{xc_id}",
    }


def process_species(common_name, scientific_name, conservation_status, habitat_group):
    """Download recordings for a single species."""
    folder_name = common_name.replace(" ", "_").replace("-", "_").replace("'", "")
    species_dir = os.path.join(BASE_DIR, folder_name)
    os.makedirs(species_dir, exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"  {common_name} ({scientific_name})")
    print(f"  Status: {conservation_status} | Group: {habitat_group}")
    print(f"{'='*60}")
    
    # Check how many we already have
    existing = [f for f in os.listdir(species_dir) if f.endswith(".mp3")]
    if len(existing) >= TARGET_PER_SPECIES:
        print(f"  Already have {len(existing)} recordings, skipping.")
        return len(existing), []
    
    needed = TARGET_PER_SPECIES - len(existing)
    print(f"  Have {len(existing)}, need {needed} more...")
    
    # Try API search first
    recording_ids = []
    data = search_xeno_canto(scientific_name)
    
    if data and "recordings" in data:
        num_recordings = int(data.get("numRecordings", 0))
        print(f"  Found {num_recordings} recordings via API")
        
        # Get IDs from first page
        for rec in data["recordings"]:
            recording_ids.append(rec["id"])
        
        # Get more pages if needed
        num_pages = int(data.get("numPages", 1))
        for page in range(2, min(num_pages + 1, 6)):  # Max 5 pages
            if len(recording_ids) >= TARGET_PER_SPECIES:
                break
            time.sleep(1)  # Rate limiting
            page_data = search_xeno_canto(scientific_name, page=page)
            if page_data and "recordings" in page_data:
                for rec in page_data["recordings"]:
                    recording_ids.append(rec["id"])
    else:
        # Fallback to website scraping
        print("  API unavailable, searching website...")
        recording_ids = search_via_website(scientific_name)
        print(f"  Found {len(recording_ids)} recording IDs from website")
    
    if not recording_ids:
        print(f"  WARNING: No recordings found for {common_name}!")
        return len(existing), []
    
    # Download recordings
    downloaded = 0
    metadata_rows = []
    
    for i, xc_id in enumerate(recording_ids[:TARGET_PER_SPECIES]):
        fname = f"{folder_name}_XC{xc_id}.mp3"
        fpath = os.path.join(species_dir, fname)
        
        # Skip if already downloaded
        if os.path.exists(fpath) and os.path.getsize(fpath) > 5000:
            downloaded += 1
            metadata_rows.append({
                "common_name": common_name,
                "scientific_name": scientific_name,
                "conservation_status": conservation_status,
                "habitat_group": habitat_group,
                "xc_id": xc_id,
                "filename": fname,
                "folder": folder_name,
                "file_size_bytes": os.path.getsize(fpath),
                "xc_url": f"https://xeno-canto.org/{xc_id}",
            })
            continue
        
        # Download
        size = download_recording(xc_id, fpath)
        if size > 0:
            downloaded += 1
            metadata_rows.append({
                "common_name": common_name,
                "scientific_name": scientific_name,
                "conservation_status": conservation_status,
                "habitat_group": habitat_group,
                "xc_id": xc_id,
                "filename": fname,
                "folder": folder_name,
                "file_size_bytes": size,
                "xc_url": f"https://xeno-canto.org/{xc_id}",
            })
            
            if downloaded % 10 == 0:
                print(f"    Downloaded {downloaded}/{min(len(recording_ids), TARGET_PER_SPECIES)}...")
        else:
            # Clean up failed download
            if os.path.exists(fpath):
                os.remove(fpath)
        
        # Rate limiting: 1 request per second
        time.sleep(1)
    
    total = len(existing) + downloaded
    print(f"  Done! {downloaded} new downloads, {total} total recordings")
    return total, metadata_rows


def main():
    print("=" * 60)
    print("  Avian Observatory — Dataset Downloader")
    print("  PRT840 IT Thesis | Charles Darwin University")
    print("=" * 60)
    print(f"\nTarget: {TARGET_PER_SPECIES} recordings per species")
    print(f"Species: {len(SPECIES)}")
    print(f"Save to: {BASE_DIR}")
    print()
    
    os.makedirs(BASE_DIR, exist_ok=True)
    
    all_metadata = []
    summary = []
    
    for common_name, scientific_name, status, group in SPECIES:
        count, metadata = process_species(common_name, scientific_name, status, group)
        all_metadata.extend(metadata)
        summary.append((common_name, status, count))
    
    # Save master metadata CSV
    if all_metadata:
        fieldnames = ["common_name", "scientific_name", "conservation_status", 
                       "habitat_group", "xc_id", "filename", "folder", 
                       "file_size_bytes", "xc_url"]
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
        status_tag = f"[{status}]" if status != "Least Concern" else ""
        print(f"  {name:.<40} {count:>4} files  {status_tag}")
        total_files += count
    
    print(f"\n  TOTAL: {total_files} recordings across {len(SPECIES)} species")
    
    # Check total disk usage
    total_size = 0
    for root, dirs, files in os.walk(BASE_DIR):
        for f in files:
            total_size += os.path.getsize(os.path.join(root, f))
    print(f"  Disk usage: {total_size / (1024*1024):.1f} MB")
    print(f"\n  Dataset ready at: {BASE_DIR}")


if __name__ == "__main__":
    main()
