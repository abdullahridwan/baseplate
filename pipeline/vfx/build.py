"""Step 4: turn candidates + scan results into the registry file agents read.

    python3 pipeline/vfx/build.py   # reads out/candidates.json and out/scans.json

Writes docs/r/vfx-assets.json: every asset with its verdict (see RULES.md),
what's inside, a short description and how to use it.
"""

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
REGISTRY = HERE.parent.parent / "docs" / "r" / "vfx-assets.json"
NOTICE = (
    "Automated scan of each listed version on the date shown. Flagged means the model matched one or more "
    "written rules; it is not a finding about any person's intent. Assets change, so check the pinned "
    "version. Not affiliated with or endorsed by Roblox Corporation."
)
COUNT_KEYS = ["effects", "parts", "scripts", "remotes", "guis", "lights", "sounds", "total"]


def normalize(row):
    """Scan rows come compact from Studio or full from Lune; make them one shape."""
    if "err" in row or "error" in row:
        return {"error": row.get("err") or row.get("error")}
    if isinstance(row.get("c"), list):
        counts = dict(zip(COUNT_KEYS, row["c"]))
        findings = row.get("f", [])
        effects = []
        for e in row.get("e", []):
            name, cls, color, tex = (e.split("|") + ["", "", "", ""])[:4]
            effects.append({"name": name, "class": cls, "color": color or None, "texture": int(tex) if tex else None})
    else:
        counts = row["counts"]
        findings = sorted({f"{f['rule']}:{f['what']}" for f in row.get("findings", [])})
        effects = [
            {"name": e["name"], "class": e["class"], "color": e.get("color"),
             "texture": int(m.group()) if (m := re.search(r"\d+", e.get("texture") or "")) else None}
            for e in row.get("effects", [])[:6]
        ]
    return {"counts": counts, "findings": findings, "effects": effects}


def verdict(asset, scan):
    if "error" in scan:
        return "error", []
    c = scan["counts"]
    findings = [
        f for f in scan["findings"]
        # A fake tool window is harmless without a script to run it.
        if not (f.startswith("M4:") and c["scripts"] == 0)
        # Flicker and sound scripts live inside lights and sounds in plenty of honest old models.
        and not re.match(r"M3:.* inside a (PointLight|SpotLight|SurfaceLight|Sound)$", f)
    ]
    if c["scripts"] and "no script" in asset["store_description"].lower():
        findings.append(f"M5:listing says 'no scripts' but it has {c['scripts']}")
    if findings:
        return "flagged", findings
    if c["effects"] == 0:
        return "not_vfx", []
    if c["scripts"] or c["remotes"]:
        return "has_scripts", []
    return "safe", []


def plain(findings):
    """Factual, neutral wording for the public file: what we observed, never a claim about intent."""
    out, words = [], []
    for f in findings:
        rule, what = f.split(":", 1)
        if rule == "M4":
            words.append(re.search(r"'(.+)'", what).group(1))
            continue
        m = re.match(r"(\w+) hidden inside a (\w+)", what)
        if m:
            what = f"A {m.group(1)} is placed inside a {m.group(2)}"
        elif rule == "M6":
            what = "Contains scripts together with RemoteEvent or RemoteFunction objects"
        elif rule == "M5":
            what = "Listing says \u201cno scripts\u201d; the model contains " + what.rsplit(" ", 1)[1]
        else:
            what = "Code uses " + what
        out.append({"rule": rule, "observed": what})
    if words:
        out.append({"rule": "M4", "observed": "Includes an on-screen window with the words: " + ", ".join(dict.fromkeys(words))})
    return list({o["observed"]: o for o in out}.values())


def describe(asset, scan):
    """A one-line description an agent can match on without inserting the asset."""
    c = scan["counts"]
    names = [e["name"] for e in scan["effects"] if e["name"]]
    kinds = Counter(e["class"] for e in scan["effects"])
    colors = sorted({e["color"] for e in scan["effects"] if e["color"]})[:4]
    parts = [f"{c['effects']} effect{'s' * (c['effects'] != 1)}"]
    if kinds:
        parts.append("(" + ", ".join(f"{n} {k}" for k, n in kinds.most_common()) + ")")
    if names:
        parts.append("named " + ", ".join(dict.fromkeys(names[:5])))
    if colors:
        parts.append("colors " + " ".join(colors))
    parts.append(f"on {c['parts']} part{'s' * (c['parts'] != 1)}")
    if c["lights"]:
        parts.append(f"with {c['lights']} light{'s' * (c['lights'] != 1)}")
    return " ".join(parts) + "."


def main():
    candidates = {a["id"]: a for a in json.loads((OUT / "candidates.json").read_text())}
    scans = {row["i"] if "i" in row else row["id"]: row for row in json.loads((OUT / "scans.json").read_text())}

    assets = []
    for aid, a in candidates.items():
        if aid not in scans:
            continue
        scan = normalize(scans[aid])
        v, findings = verdict(a, scan)
        entry = {
            "id": aid,
            "name": a["name"],
            "verdict": v,
            "pin": {"updated": a["updated"]},
            "thumbnail": a.get("thumbnail"),
            "votes": a["votes"],
            "store_url": f"https://create.roblox.com/store/asset/{aid}",
        }
        if v == "flagged":
            # No creator names on flagged entries: accounts get compromised, and we report objects, not people.
            entry["observed"] = plain(findings)
            entry["creator_removed"] = (a["creator"]["name"] or "").startswith("Content Deleted")
            entry["listing_says_no_scripts"] = "no script" in a["store_description"].lower()
        else:
            entry["creator"] = a["creator"]
        if "counts" in scan:
            entry["contains"] = scan["counts"]
            entry["effects"] = scan["effects"]
            entry["description"] = describe(a, scan)
        if v == "safe":
            entry["use"] = (
                f"Insert asset {aid}, move its effects onto your part or Attachment. "
                "Continuous emitters play while Enabled; for a burst, set Enabled = false and call emitter:Emit(n)."
            )
        assets.append(entry)

    tally = Counter(a["verdict"] for a in assets)
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps({
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rules": "https://baseplatehq.github.io/baseplate/r/vfx-rules.md",
        "notice": NOTICE,
        "counts": dict(tally),
        "assets": sorted(assets, key=lambda a: (a["verdict"] != "safe", -(a["votes"]["count"] or 0))),
    }, indent=1))
    print(f"{len(assets)} assets -> {REGISTRY}")
    for k, n in tally.most_common():
        print(f"  {k:12} {n}")


if __name__ == "__main__":
    main()
