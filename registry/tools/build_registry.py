"""Publish the registry to the website, like shadcn's /r/ folder.

    python3 registry/tools/build_registry.py          # write docs/r/
    python3 registry/tools/build_registry.py --check  # fail if docs/r/ is stale

Copies index.json and every item file into docs/r/, so agents and the CLI
fetch from https://abdullahridwan.github.io/baseplate/r/.
"""

import filecmp
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT.parent / "docs" / "r"
SITE = "https://abdullahridwan.github.io/baseplate/r/"


def expected():
    index = json.loads((ROOT / "index.json").read_text())
    index["baseUrl"] = SITE
    files = {"index.json": json.dumps(index, indent=2) + "\n"}
    for item in index["items"]:
        for f in item["files"]:
            files[f["src"]] = ROOT / f["src"]
    return files


def main():
    files = expected()
    if "--check" in sys.argv:
        stale = []
        for rel, src in files.items():
            dest = OUT / rel
            if not dest.is_file():
                stale.append(rel)
            elif isinstance(src, str):
                if dest.read_text() != src:
                    stale.append(rel)
            elif not filecmp.cmp(src, dest, shallow=False):
                stale.append(rel)
        for rel in stale:
            print("stale:", rel)
        print("docs/r is", "stale; run build_registry.py" if stale else "up to date")
        sys.exit(1 if stale else 0)

    if OUT.exists():
        shutil.rmtree(OUT)
    for rel, src in files.items():
        dest = OUT / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(src, str):
            dest.write_text(src)
        else:
            shutil.copyfile(src, dest)
    print(f"wrote {len(files)} files to docs/r/")


if __name__ == "__main__":
    main()
