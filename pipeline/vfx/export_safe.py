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
    "lava": ("lava", "lava or hazard"), "volcan": ("lava", "lava or hazard"), "magma": ("lava", "lava or hazard"),
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


def color_name(hex_color):
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    hi, lo = max(r, g, b), min(r, g, b)
    if hi - lo < 0.15:
        return "white" if hi > 0.8 else "black" if hi < 0.2 else "grey"
    d = hi - lo
    h = (60 * ((g - b) / d % 6) if hi == r else 60 * ((b - r) / d + 2) if hi == g else 60 * ((r - g) / d + 4))
    for limit, name in ((15, "red"), (45, "orange"), (70, "yellow"), (160, "green"), (200, "cyan"), (255, "blue"), (290, "purple"), (335, "pink"), (360, "red")):
        if h < limit:
            return name


def plain_description(entry, tags):
    """What a person would say about the pack, so search words match."""
    words = [t for t in tags if t != "vfx"]
    kind = (", ".join(words[:-1]) + " and " + words[-1] if len(words) > 1 else words[0]) if words else "general"
    colors = list(dict.fromkeys(color_name(e["color"]) for e in entry.get("effects", []) if e.get("color")))[:3]
    n = (entry.get("contains") or {}).get("effects", 0)
    text = f"A {kind} effects pack with {n} effect{'s' * (n != 1)}"
    if colors:
        text += ", in " + (", ".join(colors[:-1]) + " and " + colors[-1] if len(colors) > 1 else colors[0])
    if any(e["class"] == "Beam" for e in entry.get("effects", [])):
        text += ", including beams"
    return text + "."


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
                "description": plain_description(a, tags),
                "tags": tags,
                "use_cases": uses,
                "contains": a.get("contains"),
                "votes": a.get("votes"),
                "install": (
                    f"Before inserting, check the store page's last-updated time still equals {a['pin']['updated']}; if it "
                    f"changed, the pack was edited after the scan, so don't use it. Then insert asset {a['id']} with the "
                    "Roblox Studio MCP. Strip any scripts, then move "
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
        "recheck": "Request a re-check from the VFX report page: https://baseplatehq.github.io/baseplate/vfx-report.html",
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
