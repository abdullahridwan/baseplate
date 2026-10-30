"""Step 7: turn effect scans into the index agents search (registry/vfx-effects.json).

    python3 pipeline/vfx/name_effects.py pipeline/vfx/data/2026-10-30/effects.jsonl

Each usable effect inside a safe pack gets an agent name like `explosion/fire` or
`aura/electric-loop`: a category from a fixed list, then an element or colour, then
modifiers. The best effect (most votes, most layers) gets the shortest name. Names
never move: pipeline/vfx/names.lock.json maps every effect to the name it was given,
and a name whose effect stops being safe is retired, never reused.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK = Path(__file__).resolve().parent / "names.lock.json"
SAFE = ROOT / "registry" / "safe-vfx.json"
OUT = ROOT / "registry" / "vfx-effects.json"

CATEGORIES = ["hit", "explosion", "aura", "projectile", "trail", "pickup", "celebrate", "ambient", "hazard",
              "magic", "heal", "dash", "spawn", "death", "weather", "fire", "smoke"]
# word in effect, holder or pack name -> category
CATEGORY_WORDS = {
    "explo": "explosion", "boom": "explosion", "blast": "explosion", "nuke": "explosion", "bomb": "explosion",
    "hit": "hit", "impact": "hit", "break": "hit", "crash": "hit", "crack": "hit", "smash": "hit", "slam": "hit", "slash": "hit", "punch": "hit", "strike": "hit", "crit": "hit",
    "aura": "aura", "charge": "aura", "power": "aura", "chakra": "aura",
    "projectile": "projectile", "orb": "projectile", "ball": "projectile", "bullet": "projectile", "missile": "projectile",
    "trail": "trail",
    "coin": "pickup", "pickup": "pickup", "collect": "pickup", "gem": "pickup",
    "confetti": "celebrate", "firework": "celebrate", "win": "celebrate", "celebrat": "celebrate", "levelup": "celebrate",
    "ambient": "ambient", "firefl": "ambient", "dust": "ambient", "leaf": "ambient", "leaves": "ambient", "bubble": "ambient",
    "lava": "hazard", "volcan": "hazard", "magma": "hazard", "poison": "hazard", "acid": "hazard",
    "magic": "magic", "spell": "magic", "portal": "magic", "hole": "magic", "shield": "magic", "forcefield": "magic", "rune": "magic", "galaxy": "magic", "star": "magic",
    "heal": "heal", "holy": "heal",
    "dash": "dash", "wind": "dash", "speed": "dash",
    "spawn": "spawn", "teleport": "spawn", "summon": "spawn",
    "death": "death", "die": "death", "soul": "death",
    "rain": "weather", "snow": "weather", "storm": "weather",
    "fire": "fire", "flame": "fire", "torch": "fire", "campfire": "fire", "burn": "fire",
    "smoke": "smoke", "fog": "smoke", "mist": "smoke", "steam": "smoke",
}
ELEMENT_WORDS = {
    "fire": "fire", "flame": "fire", "burn": "fire", "lava": "fire", "magma": "fire",
    "ice": "ice", "frost": "ice", "snow": "ice", "freez": "ice",
    "electric": "electric", "lightning": "electric", "lighting": "electric", "thunder": "electric", "spark": "electric", "volt": "electric",
    "dark": "dark", "void": "dark", "shadow": "dark", "black": "dark",
    "holy": "holy", "light": "holy", "divine": "holy",
    "water": "water", "splash": "water", "bubble": "water",
    "poison": "poison", "acid": "poison", "toxic": "poison",
    "wind": "wind", "air": "wind",
    "earth": "earth", "rock": "earth", "dirt": "earth", "dust": "earth",
    "blood": "blood",
    "star": "star", "galaxy": "star", "cosmic": "star",
}


def color_name(hex_color):
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    hi, lo = max(r, g, b), min(r, g, b)
    if hi - lo < 0.15:
        return "white" if hi > 0.8 else "black" if hi < 0.2 else "grey"
    d = hi - lo
    h = 60 * ((g - b) / d % 6) if hi == r else 60 * ((b - r) / d + 2) if hi == g else 60 * ((r - g) / d + 4)
    for limit, name in ((15, "red"), (45, "orange"), (70, "yellow"), (160, "green"), (200, "cyan"), (255, "blue"),
                        (290, "purple"), (335, "pink"), (360, "red")):
        if h < limit:
            return name


def slug(s):
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def trigger(text, table):
    """The first whole word in text that starts with one of the table's keys, e.g. 'confetti', 'slash'."""
    text = text.lower()
    best = None
    for k in table:
        m = re.search(r"(?:^|[^a-z])(" + k + r"[a-z]*)", text)
        if m and (best is None or m.start(1) < best[0]):
            best = (m.start(1), m.group(1))
    return best[1] if best else None


def words_in(text, table):
    """Values for every key found in text, in the order they appear in the text."""
    text = text.lower()
    hits = []
    for k, v in table.items():
        m = re.search(r"(^|[^a-z])" + k, text)
        if m:
            hits.append((m.start(), v))
    return [v for _, v in sorted(hits)]


def layer(e):
    """What job one emitter does in the effect (see the roblox-vfx skill)."""
    life = e.get("life", [1, 1])[1]
    speed = e.get("speed", [0, 0])[1]
    le = e.get("le", 0)
    if e.get("orient") == "VelocityPerpendicular":
        return "ring"
    if e.get("orient") == "VelocityParallel" or speed >= 8:
        return "sparks"
    if le < 0.3 and life >= 0.8:
        return "smoke"
    if life <= 0.5 and speed < 2:
        return "flash"
    if le >= 0.7 and speed < 2:
        return "glow"
    return "particles"


# Path segments that say nothing about the effect.
GENERIC = {"part", "attachment", "main", "middle", "model", "folder", "effect", "effects", "core", "particle",
           "particles", "particleemitter", "emitter", "emitters", "vfx", "fx", "base", "packs", "pack", "free",
           "by", "the", "and", "of", "new", "ungroup", "me", "wip", "v", "a", "b", "c", "d", "e", "f", "g", "h",
           "meshpart", "workspace", "vfxattachment", "day", "kit", "ungroupme", "assets", "misc", "other", "template", "templates", "copy", "s"}
BODY = {"head", "torso", "leftarm", "rightarm", "leftleg", "rightleg", "humanoidrootpart", "uppertorso",
        "lowertorso", "leftupperarm", "rightupperarm", "leftlowerarm", "rightlowerarm", "lefthand", "righthand",
        "leftupperleg", "rightupperleg", "leftlowerleg", "rightlowerleg", "leftfoot", "rightfoot", "dummy", "rig"}
# Categories that keep running until stopped; everything else is a one-shot burst.
LOOPING = {"aura", "ambient", "fire", "smoke", "weather", "hazard", "trail"}


def label_words(fx, pack):
    """Meaningful words from the effect's own path, deepest first, minus the pack's own name."""
    pack_words = set(re.findall(r"[a-z]+", pack["name"].lower()))
    out = []
    for seg in reversed(fx["path"].split("/")[1:] or fx["path"].split("/")):
        seg = re.sub(r"#\d+$", "", seg)
        for w in re.findall(r"[a-z]+", re.sub(r"([a-z])([A-Z])", r"\1 \2", seg).lower()):
            if w not in GENERIC and w not in pack_words and len(w) > 1 and w not in out:
                out.append(w)
    return out


def describe_effect(fx, pack):
    em = [e for e in fx["emitters"] if "life" in e]
    limb = lambda s: re.sub(r"[^a-z]", "", s.lower()) in BODY
    if not em or limb(fx["name"]) or limb(fx["parent"]):
        return None  # nothing to play, or one limb of a character aura (needs the whole rig)
    labels = label_words(fx, pack)
    emitter_names = " ".join(e["name"] for e in em)
    near = " ".join(labels[:4]) + " | " + emitter_names  # the effect's own folder names outrank emitter names
    hay = near + " " + pack["name"]
    cats = words_in(near, CATEGORY_WORDS) or words_in(hay, CATEGORY_WORDS)
    elems = words_in(near, ELEMENT_WORDS) or words_in(hay, ELEMENT_WORDS)
    colors = Counter(color_name(c) for e in em for c in e.get("colors", [])[:2])
    colors = [c for c, _ in colors.most_common(2)]
    duration = round(max(e["life"][1] + (e.get("delay") or 0) for e in em), 2)
    peak = max((k[1] for e in em for k in e.get("size", [])), default=1)
    size = "small" if peak < 1.5 else "big" if peak > 6 else "medium"
    layers = list(dict.fromkeys(layer(e) for e in em))
    has_emit = any(e.get("emit") for e in em)
    if cats:
        category = cats[0]
    elif any(e.get("locked") for e in em) and not has_emit:
        category = "aura"
    else:
        category = "explosion" if size == "big" and "sparks" in layers else "hit" if duration < 1.2 else "ambient"
    # The word that set the category is the best name for the effect: celebrate/confetti, hit/slash, hazard/lava.
    word = (trigger(near, CATEGORY_WORDS) or trigger(hay, CATEGORY_WORDS)) if cats else None
    word = word[:-1] if word and word.endswith("s") and len(word) > 4 else word
    element_word = next((x for x in elems if x != category), None)
    if word and word != category and len(word) <= 12:
        element = word
        labels = ([element_word] if element_word and element_word != word else []) + labels
    else:
        element = element_word or (colors[0] if colors else "plain")
    loops = category in LOOPING and not has_emit
    fire = []
    if not loops:
        for e in em:
            m = re.search(r"\((\d+)\)", e["name"])  # packs often write the burst size in the name: "Sparks (30)"
            count = e.get("emit") or (int(m.group(1)) if m else max(1, min(40, round((e.get("rate") or 20) / 4))))
            fire.append({"emitter": e["name"], "emit": int(count), "delay": e.get("delay") or 0})
    used = {category, element, *colors}
    def same(w):
        return any(w == u or w.rstrip("s") == u.rstrip("s") for u in used)
    label = "-".join(w for w in dict.fromkeys(labels) if not same(w) and w not in BODY and w not in CATEGORY_WORDS)
    label = "-".join(label.split("-")[:2])[:24]
    source = next((s.split("#")[0] for s in reversed(fx["path"].split("/")[1:]) if s.split("#")[0].lower() not in GENERIC), None)
    tone = " and ".join(colors) if colors else "plain"
    text = f"{tone.capitalize()} {element if element not in colors else ''} {category} {'loop' if loops else 'burst'}"
    text = " ".join(text.split())
    if len(layers) > 1:
        text += " with " + ", ".join(layers[:-1]) + " and " + layers[-1]
    text += f", about {duration}s, {size}." + (f' Source: "{source}".' if source else "")
    return {
        "category": category, "element": element, "label": label, "kind": "loop" if loops else "burst",
        "loops": loops, "duration": duration, "size": size, "colors": colors, "layers": layers, "fire": fire,
        "description": text, "emitters": len(em),
        "quality": len(layers) + min(len(em), 6) / 2 + (2 if labels else 0),
    }


def clean(v):
    """Studio's JSON writes inf and nan as {"t": "numeric", "v": "inf"}; read them as big numbers."""
    if isinstance(v, dict):
        if v.get("t") == "numeric":
            return {"inf": 1e9, "-inf": -1e9}.get(v.get("v"), 0)
        return {k: clean(x) for k, x in v.items()}
    if isinstance(v, list):
        return [clean(x) for x in v]
    return v


def main():
    safe = {p["asset_id"]: p for p in json.loads(SAFE.read_text())["packs"] if p["status"] == "safe"}
    rows = []
    for line in Path(sys.argv[1]).read_text().splitlines():
        if line.strip():
            rows.extend(clean(json.loads(line)))
    lock = json.loads(LOCK.read_text()) if LOCK.exists() else {"names": {}, "retired": []}

    effects = []
    for row in rows:
        pack = safe.get(row.get("id"))
        if not pack or "effects" not in row:
            continue
        for fx in row["effects"]:
            meta = describe_effect(fx, pack)
            if not meta:
                continue
            effects.append({
                "key": f"{pack['asset_id']}/{fx['path']}",
                "asset_id": pack["asset_id"],
                "path": fx["path"],
                "pack": pack["name"],
                "pinned_version": pack["pinned_version"],
                "votes": (pack.get("votes") or {}).get("count") or 0,
                "source_name": fx["name"],
                "fingerprint": tuple(sorted((x["name"], str(x.get("texture")), str(x.get("life"))) for x in fx["emitters"])),
                **meta,
            })

    # Best first, so the best effect claims the shortest free name.
    effects.sort(key=lambda e: (-e["votes"] * (1 + e["quality"] / 10), e["key"]))
    # Packs re-upload each other's effects. Keep the best-ranked copy of each.
    seen = set()
    for e in effects:
        if e["fingerprint"] in seen:
            e["drop"] = True
        seen.add(e["fingerprint"])
    effects = [e for e in effects if not e.get("drop")]
    taken = set(lock["names"].values()) | set(lock["retired"])
    live_keys = {e["key"] for e in effects}
    for key, name in list(lock["names"].items()):
        if key not in live_keys:  # no longer safe or gone: retire the name for good
            lock["retired"].append(name)
            del lock["names"][key]
    numbered = Counter()
    for e in effects:
        if e["key"] in lock["names"]:
            e["name"] = lock["names"][e["key"]]
            continue
        base = f"{e['category']}/{e['element']}"
        tries = [base]
        if e["label"]:
            tries += [f"{base}-{e['label']}", f"{base}-{e['label']}-{e['size']}"]
        tries.append(f"{base}-{e['size']}")
        name = next((t for t in tries if t not in taken), None)
        if name is None and numbered[base] >= 3:
            e["drop"] = True  # the 4th+ lookalike under one name is noise for agents
            continue
        numbered[base] += name is None
        n = 2
        while name is None:
            if f"{base}-{n}" not in taken:
                name = f"{base}-{n}"
            n += 1
        taken.add(name)
        lock["names"][e["key"]] = name
        e["name"] = name

    effects = [e for e in effects if not e.get("drop")]
    for e in effects:
        e.pop("quality", None)
        e.pop("label", None)
        e.pop("fingerprint", None)
        e.pop("key", None)
    effects.sort(key=lambda e: e["name"])
    OUT.write_text(json.dumps({
        "name": "baseplate-vfx-effects",
        "version": 1,
        "about": "One entry per usable effect inside a safe, scanned Creator Store pack. `name` is the agent name: "
                 "category/element-modifiers. Not affiliated with Roblox Corporation.",
        "categories": CATEGORIES,
        "effects": effects,
    }, indent=1) + "\n")
    LOCK.write_text(json.dumps(lock, indent=1, sort_keys=True) + "\n")
    cats = Counter(e["category"] for e in effects)
    print(f"{len(effects)} effects from {len({e['asset_id'] for e in effects})} packs; {cats.most_common()}")


if __name__ == "__main__":
    main()
