import requests

# Xeno-canto recording IDs for NT/Australian birds
# We'll download from the recording pages directly
recordings = [
    {"id": "820587", "name": "Laughing_Kookaburra"},
    {"id": "803548", "name": "Rainbow_Bee-eater"},
    {"id": "746498", "name": "Sulphur-crested_Cockatoo"},
]

for rec in recordings:
    url = f"https://xeno-canto.org/{rec['id']}/download"
    fname = f"sample_audio/{rec['name']}_{rec['id']}.mp3"
    print(f"Downloading {rec['name']} (XC{rec['id']})...")
    r = requests.get(url, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
    if len(r.content) > 1000:
        with open(fname, "wb") as f:
            f.write(r.content)
        print(f"  Saved: {fname} ({len(r.content)} bytes)")
    else:
        print(f"  Failed - got {len(r.content)} bytes, skipping")

print("\nDone! Checking files:")
import os
for f in os.listdir("sample_audio"):
    size = os.path.getsize(f"sample_audio/{f}")
    print(f"  {f}: {size:,} bytes")
