"""Step 5: write the safe VFX index the MCP reads (registry/safe-vfx.json), then run
registry/tools/build_registry.py to publish it to docs/r/.

    python3 pipeline/vfx/export_safe.py pipeline/vfx/data/2026-10-28/assets.json

Only packs with verdict "safe" go in. Flagged packs go to registry/vfx-flagged.json for
the report page, with neutral wording and no creator names. See DIRECTION.md for the
data model.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# word in name or effect names -> (tag, use case)
VOCAB = {
    "fire": ("fire", "fire attack"), "flame": ("fire", "fire attack"), "burn": ("fire", "burning"),
    "explo": ("explosion", "explosion"), "boom": ("explosion", "explosion"), "blast": ("explosion", "explosion"),
    "smoke": ("smoke", "smoke"), "dust": ("dust", "dust or debris"), "debris": ("debris", "dust or debris"),
    "spark": ("sparks", "hit sparks"), "hit": ("impact", "hit or damage"), "impact": ("impact", "hit or damage"),
    "slash": ("slash", "sword swing"), "sword": ("slash", "sword swing"), "cut": ("slash", "sword swing"),
    "magic": ("magic", "spell cast"), "spell": ("magic", "spell cast"), "aura": ("aura", "character aura"),
    "lightning": ("lightning", "electric attack"), "electric": ("lightning", "electric attack"), "thunder": ("lightning", "electric attack"),
    "water": ("water", "water or splash"), "splash": ("water", "water or splash"), "rain": ("rain", "weather"),
    "snow": ("snow", "weather"), "ice": ("ice", "freeze"), "frost": ("ice", "freeze"),
    "heal": ("heal", "healing"), "holy": ("holy", "healing"), "light": ("light", "glow"), "glow": ("glow", "glow"),
    "dark": ("dark", "dark power"), "void": ("dark", "dark power"), "shadow": ("dark", "dark power"),
    "portal": ("portal", "teleport"), "teleport": ("portal", "teleport"), "beam": ("beam", "laser or beam"),
    "laser": ("beam", "laser or beam"), "trail": ("trail", "movement trail"), "wind": ("wind", "dash or wind"),
    "dash": ("wind", "dash or wind"), "shock": ("shockwave", "ground slam"), "wave": ("shockwave", "ground slam"),
    "confetti": ("confetti", "win or celebrate"), "firework": ("firework", "win or celebrate"), "star": ("stars", "reward"),
    "sparkle": ("sparkle", "reward"), "coin": ("coin", "reward"), "heart": ("hearts", "love or friend"),
    "blood": ("blood", "damage"), "poison": ("poison", "poison"), "energy": ("energy", "power up"),
    "orb": ("orb", "projectile"), "ball": ("orb", "projectile"), "projectile": ("projectile", "projectile"),
    "charge": ("charge", "power up"), "leaf": ("leaves", "ambient"), "firefl": ("fireflies", "ambient"),
    "galaxy": ("space", "ambient"), "black hole": ("space", "dark power"), "anime": ("anime", "anime ability"),
}


def tags_and_uses(entry):
    hay = " ".join([entry["name"]] + [e["name"] for e in entry.get("effects", [])]).lower()
    tags, uses = [], []
    for word, (tag, use) in VOCAB.items():
        if word in hay:
            tags.append(tag)
            uses.append(use)
    kinds = {e["class"] for e in entry.get("effects", [])}
    if "Beam" in kinds:
        tags.append("beam")
    tags.append("vfx")
    return sorted(set(tags)), sorted(set(uses)) or ["general effect"]


def main():
    src = json.loads(Path(sys.argv[1]).read_text())
    scan_date = src["generated"][:10]
    rules = [
        "hidden require by asset ID, loadstring, getfenv, or encoded code",
        "code that reaches outside the game (HttpService, InsertService, purchase prompts, teleports)",
        "a script hidden inside an effect object",
        "a fake Studio window that asks you to paste a command",
        "a listing that says no scripts while the pack has scripts",
        "scripts together with server remotes",
    ]
    packs, flagged = [], []
    for a in src["assets"]:
        if a["verdict"] == "safe":
            tags, uses = tags_and_uses(a)
            packs.append({
                "name": a["name"].strip()[:80],
                "asset_id": a["id"],
                "pinned_version": a["pin"]["updated"],
                "status": "safe",
                "scan_date": scan_date,
                "description": a["description"],
                "tags": tags,
                "use_cases": uses,
                "contains": a.get("contains"),
                "votes": a.get("votes"),
                "install": (
                    f"Insert asset {a['id']} with the Roblox Studio MCP. Check the store's last-updated time still equals "
                    f"{a['pin']['updated']}; if not, don't use it until it is re-scanned. Strip any scripts, then move "
                    "the effects onto your Attachment. Burst emitters: keep Enabled off and call Emit(n)."
                ),
            })
        elif a["verdict"] == "flagged":
            flagged.append({k: a[k] for k in ("id", "name", "pin", "observed", "creator_removed", "listing_says_no_scripts", "contains", "store_url") if k in a})
    packs.sort(key=lambda p: -((p["votes"] or {}).get("count") or 0))
    index = {
        "name": "baseplate-safe-vfx",
        "version": 1,
        "about": (
            "Scanned free Creator Store VFX packs. Only packs with status safe are offered by find_vfx. A pack is safe "
            "only at its pinned_version (the store's last-updated time) on its scan_date, under scan_rules. "
            "Not affiliated with Roblox Corporation."
        ),
        "scan_rules": rules,
        "scan_date": scan_date,
        "scanned": len(src["assets"]),
        "counts": src["counts"],
        "recheck": "Request a re-check from the VFX report page: https://abdullahridwan.github.io/baseplate/vfx-report.html",
        "packs": packs,
    }
    text = json.dumps(index, indent=1) + "\n"
    reg = ROOT / "registry"
    (reg / "safe-vfx.json").write_text(text)
    (reg / "vfx-assets.json").write_text(Path(sys.argv[1]).read_text())
    (reg / "vfx-rules.md").write_text((Path(__file__).parent / "RULES.md").read_text())
    (reg / "vfx-flagged.json").write_text(json.dumps({
        "scan_date": scan_date, "scanned": len(src["assets"]), "notice": src.get("notice"), "packs": flagged}, indent=1) + "\n")
    print(f"{len(packs)} safe, {len(flagged)} flagged, of {len(src['assets'])} scanned on {scan_date}")


if __name__ == "__main__":
    main()
