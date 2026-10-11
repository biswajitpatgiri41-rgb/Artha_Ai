import json
import glob

print("RAW:")
for f in glob.glob("data/raw/fred/*.json"):
    d = json.load(open(f))
    if isinstance(d, dict) and "data" in d:
        print(f"  {f}: {len(d.get('data', []))} obs")
    else:
        print(f"  {f}: metadata file")

print("\nINTERIM:")
for f in glob.glob("data/interim/*.json"):
    d = json.load(open(f))
    if isinstance(d, dict):
        print(f"  {f}: {d.get('observation_count')} obs")
    else:
        print(f"  {f}: list of {len(d)} items")

print("\nMANIFESTS:")
for f in glob.glob("data/manifests/*.json"):
    d = json.load(open(f))
    print(f"  {f}: series={d.get('series_id')}, status={d.get('status')}, checksum={d.get('checksum_sha256', 'N/A')[:16]}...")