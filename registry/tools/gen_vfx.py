"""Generate Baseplate's effects from one spec per effect.

Each spec below becomes:
  - registry/vfx/<name>.luau   the ParticleEmitter settings Juice builds in-game
  - a "preview" block in index.json, which the website animates

so the game and the preview can't drift apart. Re-run after editing a spec:

    python3 registry/tools/gen_vfx.py
    python3 registry/tools/build_index.py

Units are studs and seconds. Colors are hex. `size` and `transp` are
(time, value) keypoints over each particle's lifetime, like NumberSequence.
"""

from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "vfx"

TEXTURES = {
    "spark": "rbxasset://textures/particles/sparkles_main.dds",
    "smoke": "rbxasset://textures/particles/smoke_main.dds",
    "fire": "rbxasset://textures/particles/fire_main.dds",
}


def E(
    name, texture="spark", emit=None, rate=None, color=("#ffffff",), light=1.0,
    life=(0.5, 0.8), speed=(5, 10), spread=180, direction="Top", acc=(0, 0, 0),
    drag=0, spin=False, size=((0, 1), (1, 0)), transp=((0, 0), (1, 1)),
    squash=None, ring=False, locked=False, streak=False,
    z=0, brightness=1, delay=0, jitter=0,
):
    """One ParticleEmitter. Use emit= for a burst, rate= for a loop.

    Layering knobs (see plugins/baseplate/skills/roblox-vfx/SKILL.md):
      z          ZOffset: flashes and cores in front (2 to 3), smoke at the back (0)
      brightness >1 for flashes and glows
      delay      seconds before a burst fires, to stagger layers (flash, then sparks, then smoke)
      jitter     random size per particle, as a fraction of the size (the NumberSequence envelope)
      streak     fly along the velocity (VelocityParallel), for sparks and shards
    """
    assert (emit is None) != (rate is None), name
    return dict(
        name=name, texture=texture, emit=emit, rate=rate, color=list(color), light=light,
        life=life, speed=speed, spread=spread, direction=direction, acc=acc, drag=drag,
        spin=spin, size=size, transp=transp, squash=squash, ring=ring, locked=locked, streak=streak,
        z=z, brightness=brightness, delay=delay, jitter=jitter,
    )


# ---- building blocks: the same few shapes, recoloured, cover most effects ----

def sparkles(color, n=14, speed=(8, 14), life=(0.35, 0.6), size=0.6, up=0, drag=6, name="Sparkles", **kw):
    kw.setdefault("z", 1)
    return E(name, emit=n, color=color, life=life, speed=speed, drag=drag, acc=(0, up, 0), spin=True, jitter=0.3,
             brightness=2, size=((0, size), (1, 0)), transp=((0, 0), (0.7, 0.2), (1, 1)), **kw)


def glow(color, start=1.5, end=3.5, life=0.25, alpha=0.3, name="Glow", **kw):
    # the flash or core layer: one bright particle, drawn in front of everything else
    kw.setdefault("z", 2)
    kw.setdefault("brightness", 3)
    return E(name, emit=1, color=color, life=(life, life), speed=(0, 0), spin=True,
             size=((0, start), (1, end)), transp=((0, alpha), (1, 1)), **kw)


def ring(color, end=8, life=0.5, alpha=0.2, name="Ring", start=1):
    # tiny upward speed so VelocityPerpendicular lays the ring flat on the ground
    return E(name, emit=1, color=color, life=(life, life), speed=(0.01, 0.01), spread=0, brightness=2,
             size=((0, start), (1, end)), transp=((0, alpha), (1, 1)), ring=True)


def streaks(color, n=10, speed=(20, 32), life=(0.15, 0.3), size=0.4, squash=-1.5, drag=10, name="Streaks", **kw):
    kw.setdefault("z", 1)
    return E(name, emit=n, color=color, life=life, speed=speed, drag=drag, streak=True, brightness=2, jitter=0.25,
             size=((0, size), (1, 0)), transp=((0, 0), (0.7, 0), (1, 1)), squash=squash, **kw)


def smoke(color, n=8, start=2, end=6, life=(1, 1.8), speed=(2, 6), up=2, alpha=0.4, name="Smoke", **kw):
    # the aftermath layer: fades in, sits behind the bright layers, fires just after the flash
    kw.setdefault("delay", 0.04)
    return E(name, texture="smoke", emit=n, color=color, light=0, life=life, speed=speed, drag=2, jitter=0.3,
             acc=(0, up, 0), spin=True, size=((0, start), (1, end)), transp=((0, 1), (0.1, alpha), (1, 1)), **kw)


def rise(color, n=24, speed=(4, 9), life=(0.9, 1.4), size=0.7, spread=25, name="Rise", **kw):
    kw.setdefault("z", 1)
    return E(name, emit=n, color=color, life=life, speed=speed, spread=spread, acc=(0, 4, 0), spin=True, jitter=0.25,
             size=((0, 0.2), (0.3, size), (1, 0)), transp=((0, 0), (1, 1)), **kw)


def debris(color, n=10, speed=(10, 18), size=0.5, name="Debris", texture="smoke", **kw):
    kw.setdefault("delay", 0.02)
    return E(name, texture=texture, emit=n, color=color, light=0, life=(0.5, 0.9), speed=speed, spread=60, jitter=0.3,
             acc=(0, -40, 0), spin=True, size=((0, size), (1, size * 0.6)), transp=((0, 0), (0.8, 0), (1, 1)), **kw)


def light(color, brightness=3, range_=12, duration=0.3):
    return dict(color=color, brightness=brightness, range=range_, duration=duration)


GOLD, ORANGE, WHITE = "#ffd65a", "#ffb020", "#ffffff"
RARITY = {
    "rare": ("#6ab4ff", "#2f6bff"),
    "epic": ("#d58cff", "#8a2bff"),
    "legendary": ("#ffe680", "#ff9a1f"),
}
RAINBOW = ["#ff506e", "#ffc828", "#3cdc78", "#3ca0ff", "#be5aff"]


def fx(category, description, tags, *emitters, light=None, loop=False, duration=None, surface=False):
    """surface=True emits from the target part's whole volume (auras) instead of its centre point."""
    return dict(category=category, description=description, tags=tags,
                emitters=list(emitters), light=light, loop=loop, duration=duration, surface=surface)


# ---- the catalog --------------------------------------------------------------
# Ordered roughly by how common the effect is across today's top games
# (Steal An Egg / Steal a Brainrot, Murder Mystery 2, Adopt Me!, Grow a Garden,
# Blox Fruits, 99 Nights in the Forest, Brookhaven) plus obbies, tycoons, simulators.

EFFECTS = {
    # Rewards
    "coin_pickup": fx("Rewards", "Gold sparkle burst with a soft glow.", ["coin", "pickup", "collect", "gold"],
        sparkles(["#ffec8c", ORANGE], up=6), glow([GOLD])),
    "gem_pickup": fx("Rewards", "Cool cyan glints that pop and spin.", ["gem", "diamond", "pickup", "currency"],
        sparkles(["#bff6ff", "#28b4ff"], n=12, size=0.7, up=4), glow(["#7fe3ff"], end=3)),
    "cash_burst": fx("Rewards", "Green cash sparks fountain up and fall.", ["cash", "money", "income", "tycoon", "steal"],
        E("Cash", emit=18, color=["#9dff8a", "#2fbf4a"], light=0.4, life=(0.8, 1.2), speed=(12, 20), spread=30,
          acc=(0, -35, 0), spin=True, size=((0, 0.5), (1, 0.4)), transp=((0, 0), (0.8, 0), (1, 1))),
        glow(["#7dff8a"], end=3)),
    "confetti": fx("Rewards", "Colourful confetti that pops up and flutters down.", ["win", "celebrate", "unlock", "reward"],
        *[E(f"Confetti{i + 1}", emit=12, color=[c], light=0.3, life=(1.8, 2.6), speed=(25, 40), spread=35,
            acc=(0, -30, 0), drag=2.5, spin=True, size=((0, 0.45), (1, 0.45)), transp=((0, 0), (0.85, 0), (1, 1)))
          for i, c in enumerate(RAINBOW)]),
    "level_up": fx("Rewards", "Rising blue sparkles with an expanding ring.", ["level", "upgrade", "rank", "xp"],
        rise(["#96e6ff", "#3c78ff"], n=30), ring(["#aadcff"]), glow(["#c8ecff"], start=2, end=4, life=0.3)),
    "rebirth": fx("Rewards", "Purple-gold column and double ring. For rebirths and prestige.", ["rebirth", "prestige", "simulator"],
        rise(["#ffe680", "#a050ff"], n=40, speed=(8, 14), size=0.9, spread=15),
        ring(["#d9a6ff"], end=12, life=0.7), ring(["#ffe680"], end=7, life=0.45, name="InnerRing"),
        light=light("#c58bff", 4, 16, 0.8)),
    "purchase": fx("Rewards", "Quick white-gold pop for a successful buy.", ["purchase", "buy", "shop", "upgrade"],
        sparkles([WHITE, GOLD], n=10, speed=(6, 10), size=0.5), ring(["#fff2b0"], end=5, life=0.35)),
    "chest_open": fx("Rewards", "Golden light bursting upward out of a chest.", ["chest", "loot", "crate", "open"],
        rise(["#fff3b0", ORANGE], n=26, speed=(10, 16), spread=20), glow([GOLD], start=2, end=5, life=0.4),
        light=light("#ffcf5a", 5, 14, 0.7)),
    "firework": fx("Rewards", "A firework burst in the sky with falling sparks.", ["firework", "win", "celebrate", "event"],
        E("Burst", emit=40, color=["#ffffff", "#ff5a8c"], life=(0.8, 1.2), speed=(24, 30), drag=3,
          acc=(0, -8, 0), size=((0, 0.6), (1, 0)), transp=((0, 0), (1, 1)), squash=-0.8),
        glow(["#ffd0e0"], start=3, end=7, life=0.2)),

    # Pets and eggs
    "egg_hatch": fx("Pets & eggs", "Shell-white puff and sparkles as an egg cracks open.", ["egg", "hatch", "pet", "steal an egg"],
        smoke(["#fffaf0", "#e8e0d0"], n=10, start=1.5, end=4, life=(0.5, 0.8), speed=(6, 10), alpha=0.2),
        sparkles([WHITE, "#fff0a0"], n=16, speed=(10, 16)), glow([WHITE], end=5, life=0.3)),
    "rarity_rare": fx("Pets & eggs", "Blue reveal for a rare drop.", ["rarity", "rare", "reveal", "pet", "unbox"],
        sparkles(list(RARITY["rare"]), n=16), ring([RARITY["rare"][0]], end=6)),
    "rarity_epic": fx("Pets & eggs", "Purple reveal with a rising swirl for an epic drop.", ["rarity", "epic", "reveal", "pet", "unbox"],
        sparkles(list(RARITY["epic"]), n=20), rise(list(RARITY["epic"]), n=14), ring([RARITY["epic"][0]], end=7),
        light=light("#b46bff", 3, 12, 0.5)),
    "rarity_legendary": fx("Pets & eggs", "Gold rays, sparkles and a big ring for a legendary.", ["rarity", "legendary", "reveal", "pet", "unbox"],
        streaks(list(RARITY["legendary"]), n=16, speed=(14, 20), life=(0.5, 0.7), size=0.8, squash=-2.5, drag=4, name="Rays"),
        sparkles(list(RARITY["legendary"]), n=24, speed=(10, 18)), ring(["#ffe680"], end=10, life=0.6),
        light=light("#ffc04a", 5, 18, 0.9)),
    "rarity_mythic": fx("Pets & eggs", "Rainbow burst and rings for the rarest drops.", ["rarity", "mythic", "secret", "rainbow", "reveal"],
        *[sparkles([c], n=8, speed=(12, 20), name=f"Spark{i + 1}") for i, c in enumerate(RAINBOW)],
        ring(["#ff9ad5"], end=12, life=0.7), ring(["#9ad5ff"], end=8, life=0.5, name="InnerRing"),
        light=light("#ffffff", 5, 18, 1)),
    "pet_aura": fx("Pets & eggs", "Gentle sparkles orbiting a pet. Loops.", ["pet", "aura", "shiny", "loop"],
        E("Sparkle", rate=6, color=["#fff6c0", GOLD], life=(0.8, 1.2), speed=(0.5, 1.5),
          acc=(0, 1, 0), spin=True, size=((0, 0), (0.4, 0.35), (1, 0)), transp=((0, 0.1), (1, 1)), locked=True),
        loop=True, surface=True),
    "mutation_shimmer": fx("Pets & eggs", "Rainbow shimmer for mutated or shiny items. Loops.", ["mutation", "shiny", "rainbow", "grow a garden", "loop"],
        E("Shimmer", rate=10, color=RAINBOW, life=(0.8, 1.2), speed=(1, 2), acc=(0, 2, 0), spin=True,
          size=((0, 0), (0.4, 0.4), (1, 0)), transp=((0, 0), (1, 1)), locked=True),
        loop=True, surface=True),
    "steal_grab": fx("Pets & eggs", "Purple twirl and flash as you grab someone's item.", ["steal", "grab", "steal a brainrot", "steal an egg"],
        E("Twirl", emit=24, color=["#e0b0ff", "#7a2cff"], life=(0.35, 0.55), speed=(6, 12), drag=8,
          acc=(0, 8, 0), spin=True, size=((0, 0.6), (1, 0)), transp=((0, 0), (1, 1))),
        glow(["#b070ff"], start=4, end=0.5, life=0.35), light=light("#9a4dff", 3, 10, 0.5)),

    # Combat
    "hit": fx("Combat", "Sharp white-orange impact sparks with a flash.", ["hit", "impact", "damage", "combat"],
        streaks([WHITE, "#ff8c28"]), glow(["#fff5dc"], start=2, end=3, life=0.1, alpha=0.1, name="Flash")),
    "crit_hit": fx("Combat", "Bigger red-gold impact with a shock ring.", ["critical", "crit", "hit", "combat"],
        streaks([WHITE, "#ff3b3b"], n=16, speed=(28, 40), size=0.55), glow(["#ffe0a0"], start=3, end=5, life=0.12, alpha=0.05, name="Flash"),
        ring(["#ffd080"], end=7, life=0.25), light=light("#ff7a3b", 4, 12, 0.25)),
    "slash": fx("Combat", "A fast arc of white streaks for sword swings.", ["slash", "sword", "swing", "melee", "knife"],
        streaks(["#ffffff", "#9fd8ff"], n=14, speed=(30, 40), life=(0.12, 0.2), size=0.5, squash=-3, spread=40, direction="Front"),
        glow(["#dff2ff"], start=1.5, end=2.5, life=0.1, alpha=0.2, name="Flash")),
    "block": fx("Combat", "Blue-white sparks off a blocked hit.", ["block", "parry", "shield", "combat"],
        streaks(["#e0f4ff", "#3c9cff"], n=12, speed=(18, 26), spread=60, direction="Front"),
        glow(["#bfe4ff"], start=2, end=2.5, life=0.12, alpha=0.2, name="Flash")),
    "muzzle_flash": fx("Combat", "Short yellow flash and smoke wisp for guns and blasters.", ["gun", "muzzle", "shoot", "blaster", "murder mystery"],
        E("Flash", texture="fire", emit=3, color=["#fff6c0", ORANGE], life=(0.06, 0.08), speed=(4, 8), spread=10,
          direction="Front", size=((0, 1.2), (1, 0.4)), transp=((0, 0), (1, 1))),
        smoke(["#bdbab3"], n=3, start=0.4, end=1.5, life=(0.3, 0.5), speed=(2, 4), alpha=0.6),
        light=light("#ffd27a", 4, 10, 0.08)),
    "ground_slam": fx("Combat", "Dust wave, rocks and a ring when something hits the ground hard.", ["slam", "stomp", "ground", "impact", "boss"],
        ring(["#d8cbb4"], end=14, life=0.45, alpha=0.1), smoke(["#c8b9a0", "#8a7f6c"], n=12, start=2, end=5, speed=(12, 18), up=0, alpha=0.3),
        debris(["#8a7f6c"], n=10)),
    "shockwave": fx("Combat", "A clean expanding energy ring.", ["shockwave", "pulse", "wave", "ability"],
        ring(["#bfe6ff"], end=16, life=0.5, alpha=0), ring(["#ffffff"], end=10, life=0.35, alpha=0.3, name="InnerRing")),
    "stun_stars": fx("Combat", "Little yellow stars circling above a stunned head.", ["stun", "dizzy", "daze", "combat"],
        E("Stars", emit=6, color=["#fff3a0", GOLD], life=(1.2, 1.5), speed=(2, 3), spread=180, acc=(0, 0.5, 0),
          spin=True, size=((0, 0), (0.2, 0.5), (0.8, 0.5), (1, 0)), transp=((0, 0), (0.8, 0.1), (1, 1)))),
    "death": fx("Combat", "Soft grey poof when a character is eliminated.", ["death", "eliminate", "poof", "respawn", "murder mystery"],
        smoke(["#f2f0ea", "#9c9890"], n=14, start=1.5, end=4.5, life=(0.6, 1), speed=(6, 10), alpha=0.2),
        sparkles([WHITE], n=8, speed=(6, 10), size=0.4)),
    "charge_up": fx("Combat", "Energy sparks pulling into a point before a big move.", ["charge", "power", "ability", "cast"],
        E("Crackle", emit=24, color=["#c8f0ff", "#3c8cff"], life=(0.4, 0.7), speed=(3, 6), drag=4, spin=True,
          size=((0, 0.1), (0.6, 0.5), (1, 0)), transp=((0, 0.6), (0.8, 0), (1, 1))),
        glow(["#9fd0ff"], start=0.5, end=3, life=0.6, alpha=0.5), light=light("#6fb0ff", 3, 10, 0.6)),
    "explosion": fx("Combat", "Fireball, flying embers and lingering smoke. Visual only.", ["explosion", "bomb", "boom"],
        E("Fireball", texture="fire", emit=12, color=["#fffac8", "#ff8c1e", "#781e0a"], life=(0.35, 0.6), speed=(6, 14),
          drag=5, spin=True, size=((0, 2), (1, 5)), transp=((0, 0), (1, 1))),
        streaks(["#ffc850", "#ff5014"], n=20, speed=(25, 45), life=(0.6, 1.1), size=0.35, squash=-1, drag=3, name="Embers", acc=(0, -25, 0)),
        smoke(["#5a5550", "#282624"], n=10, start=3, end=8, life=(1.5, 2.5), speed=(3, 8), up=3, delay=0.08),
        glow(["#fff6d8"], start=4, end=8, life=0.15, alpha=0, brightness=5, z=3, name="Flash"),
        ring(["#ffd9a0"], end=14, life=0.4, alpha=0.3, name="Shockwave"),
        light=light("#ff9a3b", 6, 20, 0.6)),

    # Elements
    "fire_burst": fx("Elements", "A whoosh of flame bursting outward.", ["fire", "flame", "burn", "element"],
        E("Flames", texture="fire", emit=16, color=["#fff2a0", "#ff7a1a", "#a8200a"], life=(0.4, 0.7), speed=(8, 14),
          drag=4, acc=(0, 6, 0), spin=True, size=((0, 1.5), (1, 3)), transp=((0, 0), (1, 1))),
        sparkles(["#ffcc66", "#ff5a14"], n=10, speed=(10, 16), up=8, name="Embers"),
        glow(["#ffd27a"], start=2, end=4, life=0.2, alpha=0.2, name="Core"), light=light("#ff8a3b", 4, 14, 0.5)),
    "ice_shatter": fx("Elements", "Icy shards and frost mist.", ["ice", "freeze", "frost", "shatter", "element"],
        streaks(["#ffffff", "#8fdcff"], n=14, speed=(14, 22), life=(0.4, 0.6), size=0.5, squash=-1, drag=4, name="Shards", acc=(0, -20, 0)),
        smoke(["#e8f8ff", "#a6defa"], n=8, start=1.5, end=4, life=(0.8, 1.2), speed=(3, 6), up=0, alpha=0.4, name="Frost"),
        glow(["#e6f8ff"], start=2, end=3.5, life=0.12, alpha=0.1, name="Flash")),
    "lightning_strike": fx("Elements", "A bright flash with crackling blue sparks.", ["lightning", "electric", "zap", "thunder", "element"],
        streaks(["#ffffff", "#7ec8ff"], n=18, speed=(30, 45), life=(0.08, 0.18), size=0.4, squash=-3, drag=2),
        glow(["#d8f0ff"], start=4, end=6, life=0.1, alpha=0, name="Flash"), light=light("#9fd8ff", 8, 24, 0.2)),
    "splash": fx("Elements", "Water droplets and a splash ring.", ["water", "splash", "swim", "rain", "element"],
        E("Droplets", emit=20, color=["#e6f7ff", "#5ab4ff"], light=0.2, life=(0.5, 0.8), speed=(12, 18), spread=35,
          acc=(0, -45, 0), jitter=0.3, size=((0, 0.35), (1, 0.2)), transp=((0, 0), (0.7, 0.3), (1, 1))),
        ring(["#cfeeff"], end=6, life=0.4, alpha=0.3)),
    "poison_cloud": fx("Elements", "Sickly green bubbling cloud.", ["poison", "toxic", "acid", "debuff", "element"],
        smoke(["#9dff6a", "#3d8a1e"], n=12, start=2, end=5, life=(1, 1.6), speed=(2, 4), up=1, alpha=0.3),
        sparkles(["#d4ff9a"], n=10, speed=(2, 4), up=3, life=(0.8, 1.2), size=0.4, name="Bubbles")),
    "dark_burst": fx("Elements", "Purple-black void energy blasting out.", ["dark", "shadow", "void", "curse", "element"],
        smoke(["#5a2a8a", "#120a1e"], n=12, start=2, end=5, life=(0.6, 1), speed=(8, 14), up=0, alpha=0.2),
        streaks(["#e0b0ff", "#6a1aff"], n=12, speed=(18, 26), name="Wisps"),
        glow(["#a060ff"], start=2.5, end=4.5, life=0.2, alpha=0.2, name="Core")),
    "holy_light": fx("Elements", "Warm beams of light rising from the ground.", ["holy", "light", "divine", "bless", "element"],
        rise(["#fffbe6", "#ffd65a"], n=20, speed=(10, 16), spread=8, size=0.9),
        glow(["#fff2b0"], start=3, end=6, life=0.6, alpha=0.4), light=light("#fff0b0", 4, 16, 0.8)),
    "wind_gust": fx("Elements", "Pale streaks whipping past in one direction.", ["wind", "gust", "air", "dash", "element"],
        streaks(["#ffffff", "#d8f0f0"], n=12, speed=(30, 40), life=(0.25, 0.4), size=0.3, squash=-4, drag=2, spread=10, direction="Front")),

    # Movement
    "jump": fx("Movement", "Small dust puff at your feet when you jump.", ["jump", "dust", "movement"],
        smoke(["#e8e2d6"], n=6, start=0.8, end=2, life=(0.3, 0.5), speed=(4, 6), up=0, alpha=0.4, spread=80, direction="Bottom")),
    "land": fx("Movement", "Dust ring when you land.", ["land", "dust", "fall", "movement"],
        smoke(["#e8e2d6"], n=10, start=1, end=2.5, life=(0.4, 0.6), speed=(8, 12), up=0, alpha=0.4, spread=90, direction="Bottom"),
        ring(["#e8e2d6"], end=5, life=0.3, alpha=0.4)),
    "double_jump": fx("Movement", "A ring of air under your feet for a second jump.", ["double jump", "air", "movement", "obby"],
        ring(["#ffffff"], end=5, life=0.3, alpha=0.2), sparkles(["#ffffff", "#bfe6ff"], n=8, speed=(6, 10), size=0.4)),
    "dash": fx("Movement", "Speed streaks left behind on a dash.", ["dash", "speed", "boost", "movement"],
        streaks(["#ffffff", "#9fd0ff"], n=10, speed=(12, 18), life=(0.2, 0.35), size=0.35, squash=-4, spread=15, direction="Back")),
    "teleport": fx("Movement", "Blue column of light for teleports and portals.", ["teleport", "warp", "portal", "movement"],
        rise(["#e0f4ff", "#3c9cff"], n=30, speed=(10, 18), spread=5, life=(0.4, 0.7), size=0.8),
        ring(["#bfe6ff"], end=6, life=0.4), light=light("#7fc0ff", 4, 14, 0.5)),
    "checkpoint": fx("Movement", "Green rising sparkles and ring when you hit a checkpoint.", ["checkpoint", "stage", "save", "obby"],
        rise(["#d0ffd8", "#2fd06a"], n=20), ring(["#a6f5be"], end=7), glow(["#d0ffd8"], start=2, end=4, life=0.3)),

    # Farming
    "plant": fx("Farming", "Soil puff and green sparkle as a seed goes in.", ["plant", "seed", "farm", "grow a garden"],
        debris(["#7a5a3a"], n=6, speed=(4, 8), size=0.4, name="Soil"), sparkles(["#c8ffb0", "#4cc84a"], n=8, speed=(3, 6), up=4, size=0.4)),
    "harvest": fx("Farming", "Leafy pop when a crop is collected.", ["harvest", "crop", "farm", "collect", "grow a garden"],
        E("Leaves", emit=12, color=["#a8f07a", "#3a9a2a"], light=0, life=(0.6, 1), speed=(8, 14), spread=50,
          acc=(0, -25, 0), drag=2, spin=True, size=((0, 0.5), (1, 0.4)), transp=((0, 0), (0.8, 0), (1, 1))),
        sparkles(["#fff6c0"], n=8, speed=(6, 10), size=0.4)),
    "smoke_puff": fx("Farming", "Neutral grey puff for things appearing or disappearing.", ["smoke", "poof", "appear", "despawn", "build"],
        smoke(["#e6e3dc", "#a6a299"], n=10, start=1.2, end=3.5, life=(0.5, 0.8), speed=(5, 8), alpha=0.3)),

    # Auras and ambient (loops)
    "aura_fire": fx("Auras & ambient", "Flames licking up around a character. Loops.", ["aura", "fire", "buff", "anime", "loop"],
        E("Flames", texture="fire", rate=20, color=["#fff2a0", "#ff6a14", "#a8200a"], life=(0.5, 0.8), speed=(2, 4),
          acc=(0, 8, 0), spin=True, size=((0, 1.2), (1, 0.2)), transp=((0, 0.2), (1, 1)), locked=True),
        loop=True, surface=True, light=light("#ff8a3b", 2, 10)),
    "aura_electric": fx("Auras & ambient", "Blue sparks crackling around a character. Loops.", ["aura", "electric", "lightning", "anime", "loop"],
        E("Sparks", rate=45, color=["#ffffff", "#5ab4ff"], life=(0.12, 0.25), speed=(6, 10), drag=2,
          size=((0, 0.35), (1, 0)), transp=((0, 0), (0.7, 0), (1, 1)), squash=-2.5, streak=True, brightness=2, locked=True),
        loop=True, surface=True, light=light("#7fc0ff", 1.5, 8)),
    "aura_holy": fx("Auras & ambient", "Soft golden motes drifting up. Loops.", ["aura", "holy", "gold", "vip", "loop"],
        E("Motes", rate=12, color=["#fffbe0", GOLD], life=(1, 1.6), speed=(1, 2), acc=(0, 3, 0), spin=True,
          size=((0, 0), (0.3, 0.5), (1, 0)), transp=((0, 0.1), (1, 1)), locked=True),
        loop=True, surface=True, light=light("#ffe7a0", 1, 8)),
    "shield_bubble": fx("Auras & ambient", "Pulsing blue shield ring and glints. Loops.", ["shield", "bubble", "protect", "base lock", "loop"],
        E("Pulse", rate=2, color=["#bfe6ff"], life=(0.8, 0.8), speed=(0, 0), size=((0, 6), (1, 7)),
          transp=((0, 0.6), (0.5, 0.75), (1, 1)), locked=True),
        E("Glints", rate=6, color=["#e6f6ff", "#5ab4ff"], life=(0.4, 0.6), speed=(3, 4), drag=6,
          size=((0, 0.3), (1, 0)), transp=((0, 0), (1, 1)), locked=True),
        loop=True),
    "campfire": fx("Auras & ambient", "Campfire flames, embers and smoke. Loops.", ["campfire", "fire", "survival", "99 nights", "loop"],
        E("Flames", texture="fire", rate=18, color=["#fff2a0", "#ff6a14", "#a8200a"], life=(0.5, 0.9), speed=(1, 3), spread=15,
          acc=(0, 6, 0), spin=True, size=((0, 1.6), (1, 0.4)), transp=((0, 0.1), (1, 1))),
        E("Embers", rate=5, color=["#ffcc66", "#ff5a14"], life=(1.2, 2), speed=(3, 6), spread=20, acc=(0, 3, 0),
          size=((0, 0.2), (1, 0)), transp=((0, 0), (0.8, 0.3), (1, 1))),
        E("Smoke", texture="smoke", rate=3, color=["#8a8680", "#3a3834"], light=0, life=(2.5, 3.5), speed=(3, 5), spread=10,
          acc=(0, 1, 0), spin=True, jitter=0.3, size=((0, 1.5), (1, 5)), transp=((0, 1), (0.1, 0.6), (1, 1))),
        loop=True, light=light("#ff9a4a", 3, 18)),
    "fireflies": fx("Auras & ambient", "Slow glowing fireflies for night scenes. Loops.", ["fireflies", "night", "ambient", "forest", "loop"],
        E("Flies", rate=3, color=["#f6ff9a", "#b8ff4a"], life=(3, 5), speed=(0.5, 1.5), acc=(0, 0.3, 0),
          size=((0, 0), (0.2, 0.3), (0.8, 0.3), (1, 0)), transp=((0, 1), (0.15, 0), (0.5, 0.4), (0.85, 0), (1, 1))),
        loop=True),
    "portal": fx("Auras & ambient", "Swirling purple portal energy. Loops.", ["portal", "gate", "teleport", "world", "loop"],
        E("Swirl", rate=30, color=["#f0d0ff", "#7a2cff"], life=(0.6, 0.9), speed=(3, 5), drag=3, spin=True,
          size=((0, 0.6), (1, 0.1)), transp=((0, 0), (1, 1))),
        E("Core", rate=4, color=["#c890ff"], life=(0.6, 0.6), speed=(0, 0), spin=True, z=1, size=((0, 4), (1, 5)), transp=((0, 1), (0.2, 0.5), (1, 1))),
        loop=True, light=light("#a060ff", 2, 12)),
    "falling_leaves": fx("Auras & ambient", "Autumn leaves drifting down. Loops.", ["leaves", "autumn", "ambient", "tree", "loop"],
        E("Leaves", rate=3, color=["#ffb347", "#c8501e"], light=0, life=(3, 4), speed=(1, 2), spread=60, direction="Bottom",
          acc=(0, -1.5, 0), spin=True, size=((0, 0.5), (1, 0.5)), transp=((0, 0), (0.9, 0), (1, 1))),
        loop=True),
}


# ---- output -----------------------------------------------------------------

def lua_num(v):
    return f"{v:g}"


def lua_color(h):
    r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
    return f"Color3.fromRGB({r}, {g}, {b})"


def lua_seq(points, indent, jitter=0):
    if len(points) == 2 and points[0][1] == points[1][1] and not jitter:
        return f"NumberSequence.new({lua_num(points[0][1])})"
    pad = "\t" * (indent + 1)

    def key(t, v):
        env = round(v * jitter, 3)
        return f"NumberSequenceKeypoint.new({lua_num(t)}, {lua_num(v)}{', ' + lua_num(env) if env else ''})"
    keys = "".join(f"{pad}{key(t, v)},\n" for t, v in points)
    return "NumberSequence.new({\n" + keys + "\t" * indent + "})"


def lua_colors(colors, indent):
    if len(colors) == 1:
        return f"ColorSequence.new({lua_color(colors[0])})"
    if len(colors) == 2:
        return f"ColorSequence.new({lua_color(colors[0])}, {lua_color(colors[1])})"
    pad = "\t" * (indent + 1)
    step = 1 / (len(colors) - 1)
    keys = "".join(f"{pad}ColorSequenceKeypoint.new({lua_num(round(i * step, 3))}, {lua_color(c)}),\n" for i, c in enumerate(colors))
    return "ColorSequence.new({\n" + keys + "\t" * indent + "})"


def lua_emitter(e):
    i = 4
    p = "\t" * i
    lines = [
        f'Name = "{e["name"]}"',
        f'Texture = {e["texture"].upper()}',
        f'Color = {lua_colors(e["color"], i)}',
        f'LightEmission = {lua_num(e["light"])}',
        "LightInfluence = 0 -- looks the same in a dark cave and in daylight",
        f'Lifetime = NumberRange.new({lua_num(e["life"][0])}, {lua_num(e["life"][1])})',
        f'Speed = NumberRange.new({lua_num(e["speed"][0])}, {lua_num(e["speed"][1])})',
        f'SpreadAngle = Vector2.new({lua_num(e["spread"])}, {lua_num(e["spread"])})',
    ]
    if e["direction"] != "Top":
        lines.append(f'EmissionDirection = Enum.NormalId.{e["direction"]}')
    if any(e["acc"]):
        lines.append("Acceleration = Vector3.new({}, {}, {})".format(*map(lua_num, e["acc"])))
    if e["drag"]:
        lines.append(f'Drag = {lua_num(e["drag"])}')
    if e["brightness"] != 1:
        lines.append(f'Brightness = {lua_num(e["brightness"])}')
    if e["z"]:
        lines.append(f'ZOffset = {lua_num(e["z"])} -- drawn in front of the layers behind it')
    if e["spin"]:
        lines += ["Rotation = NumberRange.new(0, 360)", "RotSpeed = NumberRange.new(-180, 180)"]
    if e["squash"] is not None:
        lines.append(f'Squash = NumberSequence.new({lua_num(e["squash"])}) -- stretch along motion: streaks, not dots')
    if e["streak"]:
        lines.append("Orientation = Enum.ParticleOrientation.VelocityParallel -- points along its flight path")
    if e["ring"]:
        lines.append("Orientation = Enum.ParticleOrientation.VelocityPerpendicular -- lies flat: a ring on the ground")
    if e["locked"]:
        lines.append("LockedToPart = true -- follows the character")
    lines += [f'Size = {lua_seq(e["size"], i, e["jitter"])}', f'Transparency = {lua_seq(e["transp"], i)}']
    count = f'rate = {lua_num(e["rate"])},' if e["rate"] is not None else f'emit = {e["emit"]},'
    if e["delay"]:
        count += f'\n\t\t\tdelay = {lua_num(e["delay"])},'
    # the comma goes before any trailing comment, or Luau reads it as part of the comment
    body = "".join(f"{p}{code}, --{note}\n" if note else f"{p}{code},\n"
                   for code, _, note in (line.partition(" --") for line in lines))
    return f"\t\t{{\n\t\t\t{count}\n\t\t\tproperties = {{\n{body}\t\t\t}},\n\t\t}},\n"


def lua_effect(name, spec):
    used = sorted({e["texture"] for e in spec["emitters"]}, key=list(TEXTURES).index)
    header = f"-- {name}: {spec['description']}"
    if spec["loop"]:
        header += "\n-- Loops: start it with Juice.attach(\"" + name + "\", target), which returns a stop function."
    consts = "".join(f'local {t.upper()} = "{TEXTURES[t]}"\n' for t in used)
    out = f"{header}\n-- Generated by registry/tools/gen_vfx.py. Edit the spec there, or edit this file and own it.\n{consts}\nreturn {{\n"
    if spec["surface"]:
        out += "\tsurface = true, -- emit from the whole part, not just its centre\n"
    if spec["loop"]:
        out += "\tloop = true,\n"
        if spec["duration"]:
            out += f"\tduration = {lua_num(spec['duration'])},\n"
    if spec["light"]:
        l = spec["light"]
        out += (f"\tlight = {{ color = {lua_color(l['color'])}, brightness = {lua_num(l['brightness'])}, "
                f"range = {lua_num(l['range'])}, duration = {lua_num(l['duration'])} }},\n")
    out += "\temitters = {\n" + "".join(lua_emitter(e) for e in spec["emitters"]) + "\t},\n}\n"
    return out


def preview(spec):
    """What the website needs to animate the effect: the same numbers, flattened."""
    return dict(
        loop=spec["loop"], surface=spec["surface"],
        light=spec["light"]["color"] if spec["light"] else None,
        emitters=[dict(
            emit=e["emit"], rate=e["rate"], texture=e["texture"], color=e["color"], add=e["light"] >= 0.5,
            life=list(e["life"]), speed=list(e["speed"]), spread=e["spread"], direction=e["direction"],
            acc=e["acc"][1], drag=e["drag"], spin=e["spin"], streak=-e["squash"] if e["squash"] else 0,
            ring=e["ring"], size=[list(k) for k in e["size"]],
            alpha=[[t, round(1 - v, 3)] for t, v in e["transp"]],
            delay=e["delay"], z=e["z"],
        ) for e in spec["emitters"]],
    )


def validate(name, spec):
    """Catch settings Roblox would reject before they reach a game."""
    for e in spec["emitters"]:
        where = f"{name}.{e['name']}"
        for label, seq in (("size", e["size"]), ("transp", e["transp"])):
            assert seq[0][0] == 0 and seq[-1][0] == 1, f"{where}: {label} keypoints must run from 0 to 1"
            assert len(seq) <= 20, f"{where}: {label} has more than 20 keypoints"
            assert all(a[0] < b[0] for a, b in zip(seq, seq[1:])), f"{where}: {label} times must increase"
        assert all(0 <= v <= 1 for _, v in e["transp"]), f"{where}: transparency must be 0..1"
        assert e["transp"][-1][1] == 1, f"{where}: particles must fade out to fully transparent, not pop"
        assert 0 <= e["jitter"] < 1 and 0 <= e["delay"] < 1, f"{where}: jitter and delay must be 0..1"
        assert all(v >= 0 for _, v in e["size"]), f"{where}: size can't be negative"
        for label in ("life", "speed"):
            lo, hi = e[label]
            assert lo <= hi, f"{where}: {label} min > max"
        assert e["life"][0] > 0, f"{where}: lifetime must be positive"
        assert e["texture"] in TEXTURES, f"{where}: unknown texture"
        assert e["direction"] in ("Top", "Bottom", "Front", "Back", "Left", "Right"), where
        assert len(e["color"]) <= 20, f"{where}: too many colors"
    assert spec["loop"] == any(e["rate"] for e in spec["emitters"]), f"{name}: loop must match rate emitters"


def main():
    OUT.mkdir(exist_ok=True)
    for name, spec in EFFECTS.items():
        validate(name, spec)
    for old in OUT.glob("*.luau"):
        if old.stem not in EFFECTS:
            old.unlink()
    for name, spec in EFFECTS.items():
        (OUT / f"{name}.luau").write_text(lua_effect(name, spec))
    print(f"wrote {len(EFFECTS)} effects to vfx/")


if __name__ == "__main__":
    main()
