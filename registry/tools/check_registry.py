"""Check registry/index.json against the files on disk.

    python3 registry/tools/check_registry.py

Fails if an item points at a missing file, names are duplicated within a kind,
a dependency doesn't exist, or a file in vfx/ or sfx/ isn't listed.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    index = json.loads((ROOT / "index.json").read_text())
    errors = []
    seen = set()
    names = {item["name"] for item in index["items"]}
    listed = set()

    for item in index["items"]:
        key = (item["kind"], item["name"])
        if key in seen:
            errors.append(f"duplicate {item['kind']} '{item['name']}'")
        seen.add(key)
        for dep in item["requires"]:
            if dep not in names:
                errors.append(f"{item['name']}: requires unknown item '{dep}'")
        for f in item["files"]:
            listed.add(f["src"])
            if not (ROOT / f["src"]).is_file():
                errors.append(f"{item['name']}: missing file {f['src']}")

    for folder in ("vfx", "sfx"):
        for path in sorted((ROOT / folder).iterdir()):
            rel = f"{folder}/{path.name}"
            if rel not in listed:
                errors.append(f"{rel} is not listed in index.json")

    for e in errors:
        print("error:", e)
    print(f"{len(index['items'])} items, {len(errors)} errors")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
