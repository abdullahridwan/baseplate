"""Step 2: download each candidate's model file (.rbxm) for scanning.

Needs a Roblox Open Cloud API key with the legacy-asset:manage scope, in the
ROBLOX_API_KEY environment variable (.env locally, a repo secret in the weekly job).
Skips files already downloaded for the same store version.

    python3 pipeline/vfx/fetch.py
"""

import gzip
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
FILES = OUT / "rbxm"
DELIVERY = "https://apis.roblox.com/asset-delivery-api/v1/assetId/{}"


def fetch(asset_id, key):
    req = urllib.request.Request(DELIVERY.format(asset_id), headers={"x-api-key": key})
    with urllib.request.urlopen(req, timeout=30) as res:
        location = json.loads(res.read())["location"]
    with urllib.request.urlopen(location, timeout=60) as res:
        body = res.read()
    return gzip.decompress(body) if body[:2] == b"\x1f\x8b" else body


def main():
    key = os.environ.get("ROBLOX_API_KEY")
    if not key:
        raise SystemExit("set ROBLOX_API_KEY (Open Cloud key with legacy-asset:manage)")
    FILES.mkdir(parents=True, exist_ok=True)
    candidates = json.loads((OUT / "candidates.json").read_text())
    failed = {}
    for n, a in enumerate(candidates, 1):
        stamp = a["updated"].replace(":", "")
        path = FILES / f"{a['id']}_{stamp}.rbxm"
        if path.exists():
            continue
        try:
            path.write_bytes(fetch(a["id"], key))
        except (urllib.error.URLError, KeyError, ValueError) as err:
            failed[a["id"]] = str(err)[:120]
        if n % 50 == 0:
            print(f"{n}/{len(candidates)}")
        time.sleep(0.2)
    (OUT / "fetch_errors.json").write_text(json.dumps(failed, indent=1))
    print(f"done, {len(failed)} failed")


if __name__ == "__main__":
    main()
