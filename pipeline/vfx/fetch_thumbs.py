"""Download each pack's Creator Store thumbnail for the components site.

    python3 pipeline/vfx/fetch_thumbs.py

Roblox thumbnail URLs expire and can't be loaded cross-site, so the site serves
its own copies from registry/vfx-thumbs/<asset_id>.png (150x150).
"""

import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "registry" / "vfx-thumbs"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "baseplate-pipeline"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def main():
    effects = json.loads((ROOT / "registry" / "vfx-effects.json").read_text())["effects"]
    ids = sorted({e["asset_id"] for e in effects})
    OUT.mkdir(parents=True, exist_ok=True)
    keep = {f"{i}.png" for i in ids}
    for f in OUT.iterdir():
        if f.name not in keep:
            f.unlink()
    todo = [i for i in ids if not (OUT / f"{i}.png").exists()]
    for k in range(0, len(todo), 50):
        batch = ",".join(map(str, todo[k : k + 50]))
        data = json.loads(get(f"https://thumbnails.roblox.com/v1/assets?assetIds={batch}&size=150x150&format=Png"))["data"]
        for t in data:
            if t.get("state") == "Completed" and t.get("imageUrl"):
                (OUT / f"{t['targetId']}.png").write_bytes(get(t["imageUrl"]))
    print(f"{len(list(OUT.iterdir()))} of {len(ids)} pack thumbnails in {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
