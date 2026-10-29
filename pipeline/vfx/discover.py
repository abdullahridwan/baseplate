"""Step 1: find every free VFX model on the Creator Store.

Search caps each query at about 1000 results, so we run many queries over the
particle-effects category and merge them by asset ID. Uses only public endpoints.

    python3 pipeline/vfx/discover.py            # writes pipeline/vfx/out/candidates.json
    python3 pipeline/vfx/discover.py --max 200  # stop early (for a quick test run)
"""

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

SEARCH = "https://apis.roblox.com/toolbox-service/v2/assets:search"
THUMBS = "https://thumbnails.roblox.com/v1/assets"
CATEGORY = "visual-effects__particle-effects"
OUT = Path(__file__).resolve().parent / "out"

# What people actually search for. Each query adds up to ~1000 more assets.
QUERIES = [
    "vfx", "vfx pack", "particle", "effect", "explosion", "fire", "fireball", "smoke",
    "magic", "spell", "aura", "lightning", "electric", "sparkle", "sparks", "glow",
    "hit", "impact", "slash", "sword", "beam", "trail", "portal", "shockwave",
    "energy", "water", "ice", "wind", "heal", "dust", "rain", "snow", "confetti",
    "coin", "star", "dark", "light", "poison", "blood", "teleport", "charge", "orb",
]


def get_json(url, tries=4):
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=30) as res:
                return json.loads(res.read(), strict=False)  # descriptions contain raw control chars
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(2 ** attempt)


def search(query, limit):
    token = ""
    while True:
        params = {
            "searchCategoryType": "Model",
            "query": query,
            "maxPageSize": 100,
            "maxPriceCents": 0,
            "categoryPath": CATEGORY,
        }
        if token:
            params["pageToken"] = token
        page = get_json(f"{SEARCH}?{urllib.parse.urlencode(params)}")
        for item in page.get("creatorStoreAssets", []):
            yield item
        token = page.get("nextPageToken")
        limit -= 1
        if not token or limit <= 0:
            return
        time.sleep(0.3)


def flatten(item):
    a, c, v = item["asset"], item.get("creator", {}), item.get("voting", {})
    return {
        "id": a["id"],
        "name": a.get("name", ""),
        "store_description": a.get("description", ""),
        "creator": {"id": c.get("userId") or c.get("groupId"), "name": c.get("name"), "verified": c.get("verified", False)},
        "created": a.get("createTime"),
        "updated": a.get("updateTime"),  # changes on every new version: our pin
        "store_says": {
            "has_scripts": a.get("hasScripts"),
            "script_count": a.get("scriptCount", 0),
            "instance_counts": a.get("instanceCounts", {}),
            "triangles": a.get("objectMeshSummary", {}).get("triangles", 0),
        },
        "votes": {"up_percent": v.get("upVotePercent"), "count": v.get("voteCount")},
        "video_preview": (a.get("previewAssets") or {}).get("videoPreviewAssets", [])[:1],
    }


def add_thumbnails(assets):
    ids = list(assets)
    for i in range(0, len(ids), 100):
        batch = ",".join(map(str, ids[i:i + 100]))
        for t in get_json(f"{THUMBS}?assetIds={batch}&size=420x420&format=Png").get("data", []):
            if t.get("state") == "Completed":
                assets[t["targetId"]]["thumbnail"] = t["imageUrl"]
        time.sleep(0.3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=0, help="stop after this many assets")
    ap.add_argument("--pages", type=int, default=10, help="pages of 100 per query")
    args = ap.parse_args()

    assets = {}
    for q in QUERIES:
        before = len(assets)
        for item in search(q, args.pages):
            assets.setdefault(item["asset"]["id"], flatten(item))
        print(f"{q:12} +{len(assets) - before:5}  total {len(assets)}")
        if args.max and len(assets) >= args.max:
            break
    if args.max:
        assets = dict(list(assets.items())[: args.max])

    add_thumbnails(assets)
    OUT.mkdir(exist_ok=True)
    path = OUT / "candidates.json"
    path.write_text(json.dumps(sorted(assets.values(), key=lambda a: a["id"]), indent=1))
    print(f"wrote {len(assets)} assets to {path}")


if __name__ == "__main__":
    main()
