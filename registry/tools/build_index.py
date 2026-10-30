"""Build registry/index.json from the effect specs and sound recipes.

    python3 registry/tools/build_index.py

gen_vfx.py and gen_sfx.py hold the catalog (descriptions, tags, categories,
volumes); this turns it into the one file agents, the CLI and the site read.
"""

import json
from pathlib import Path

from gen_sfx import SOUNDS
from gen_vfx import EFFECTS, preview

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://baseplatehq.github.io/baseplate/r/"


def sound_line(name, meta):
    pitch = f", pitchVariance = {meta['pitchVariance']:g}" if meta["pitchVariance"] else ""
    return f'{name} = {{ id = "ASSET_ID", volume = {meta["volume"]:g}{pitch} }},'


def main():
    items = [{
        "name": "juice", "kind": "runtime", "category": "Runtime",
        "description": "The runtime every item needs: Juice.play, Juice.vfx, Juice.attach, Juice.sfx, Juice.music.",
        "tags": ["runtime"], "requires": [],
        "files": [{"src": "juice/init.luau", "dest": "src/shared/Juice/init.luau"},
                  {"src": "juice/Sounds.luau", "dest": "src/shared/Juice/Sounds.luau"}],
        "after": ["Skip copying a file that already exists; never overwrite the user's Sounds.luau."],
        "license": "MIT",
    }]
    for name, spec in EFFECTS.items():
        usage = f'local stop = Juice.attach("{name}", target)' if spec["loop"] else f'Juice.vfx("{name}", target)'
        items.append({
            "name": name, "kind": "vfx", "category": spec["category"], "description": spec["description"],
            "tags": spec["tags"], "requires": ["juice"],
            "files": [{"src": f"vfx/{name}.luau", "dest": f"src/shared/Juice/Effects/{name}.luau"}],
            "usage": usage, "after": [], "license": "MIT", "preview": preview(spec),
        })
    for name, meta in SOUNDS.items():
        items.append({
            "name": name, "kind": "sfx", "category": meta["category"], "description": meta["description"],
            "tags": meta["tags"], "requires": ["juice"],
            "files": [{"src": f"sfx/{name}.ogg", "dest": f"assets/sfx/{name}.ogg"}],
            "sound": {"volume": meta["volume"], "pitchVariance": meta["pitchVariance"]},
            "usage": f'Juice.sfx("{name}")',
            "after": [
                f"Ask the user to upload assets/sfx/{name}.ogg as an Audio asset (Creator Hub > Creations > Upload, "
                "or Open Cloud Assets API) and give you its asset ID.",
                f"Add this line inside the Sounds table in src/shared/Juice/Sounds.luau, with the real ID: {sound_line(name, meta)}",
            ],
            "license": "CC0-1.0",
        })
    index = {
        "name": "baseplate", "version": 2, "baseUrl": SITE,
        "about": "Agent-native VFX and sounds for Roblox. Copy files from baseUrl+src to dest in the user's project, "
                 "then do each 'after' step. Install 'requires' first.",
        "items": items,
    }
    (ROOT / "index.json").write_text(json.dumps(index, indent=2) + "\n")
    vfx = sum(i["kind"] == "vfx" for i in items)
    print(f"index.json: {vfx} effects, {len(items) - vfx - 1} sounds")


if __name__ == "__main__":
    main()
