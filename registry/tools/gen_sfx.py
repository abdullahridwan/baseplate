"""Generate Baseplate's sound effects from code.

Every sound in registry/sfx/ is synthesized here, so they are fully original
and released CC0. Re-run after tweaking a recipe:

    python3 registry/tools/gen_sfx.py

Needs numpy and ffmpeg (with libvorbis) on PATH.
"""

import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

RATE = 44100
OUT = Path(__file__).resolve().parent.parent / "sfx"
rng = np.random.default_rng(7)  # fixed seed: regenerating gives identical files


def t(duration):
    return np.arange(int(RATE * duration)) / RATE


def note(name):
    """'A4' -> Hz."""
    names = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}
    semis = names[name[0]] + (1 if "#" in name else 0)
    octave = int(name[-1])
    return 440.0 * 2 ** ((semis + 12 * (octave - 4)) / 12)


def env(n, attack, release, curve=4.0):
    """Fast attack, exponential-ish decay over n samples."""
    a = max(1, int(RATE * attack))
    e = np.ones(n)
    e[:a] = np.linspace(0, 1, a)
    tail = np.linspace(0, 1, n - a)
    e[a:] = (1 - tail) ** curve if release else 1
    return e


def osc(shape, freq, duration):
    x = t(duration)
    phase = 2 * np.pi * np.cumsum(np.broadcast_to(freq, x.shape)) / RATE
    if shape == "sine":
        return np.sin(phase)
    if shape == "triangle":
        return 2 / np.pi * np.arcsin(np.sin(phase))
    if shape == "square":
        # softened square: fewer harsh harmonics than a pure one
        return np.tanh(4 * np.sin(phase))
    raise ValueError(shape)


def tone(shape, freq, duration, attack=0.003, curve=4.0):
    s = osc(shape, freq, duration)
    return s * env(len(s), attack, True, curve)


def noise(duration):
    return rng.uniform(-1, 1, int(RATE * duration))


def lowpass(x, cutoff):
    """One-pole lowpass; enough to take the fizz off noise. `cutoff` may be an array to sweep it."""
    a = np.exp(-2 * np.pi * np.broadcast_to(cutoff, x.shape) / RATE)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a[i]) * v + a[i] * acc
        y[i] = acc
    return y


def bandpass(x, low, high):
    """Crude band: lowpass at `high` minus lowpass at `low`. Both may be arrays."""
    return lowpass(x, high) - lowpass(x, low)


def ramp(a, b, duration, curve=1.0):
    """Values from a to b over `duration` seconds; curve > 1 eases in."""
    return a + (b - a) * np.linspace(0, 1, int(RATE * duration)) ** curve


def shaped(x, attack=0.003, curve=4.0):
    return x * env(len(x), attack, True, curve)


def seq(*parts, gap=0.0):
    """Play parts one after another, overlapping by `gap` seconds if negative."""
    out = np.zeros(0)
    for p in parts:
        offset = max(0, len(out) + int(RATE * gap)) if len(out) else 0
        need = offset + len(p)
        if need > len(out):
            out = np.pad(out, (0, need - len(out)))
        out[offset:offset + len(p)] += p
    return out


def mix(*parts):
    n = max(len(p) for p in parts)
    return sum(np.pad(p, (0, n - len(p))) for p in parts)


# --- recipes -----------------------------------------------------------------
# Each recipe registers itself with the metadata build_index.py puts in index.json.
# Ordered and chosen by how common the sound is across today's top Roblox games.

SOUNDS = {}


def sound(category, description, tags, volume=0.5, pitch=0.0):
    def register(fn):
        SOUNDS[fn.__name__] = dict(fn=fn, category=category, description=description, tags=tags,
                                   volume=volume, pitchVariance=pitch)
        return fn
    return register


@sound("Rewards", "Two-note bright coin blip.", ["coin", "pickup", "collect"], 0.5, 0.05)
def coin_pickup():
    return seq(
        tone("square", note("B5"), 0.07, curve=1.5) * 0.5,
        tone("square", note("E6"), 0.28, curve=3) * 0.5,
        gap=-0.005,
    )


@sound("Combat", "Punchy thump with a noise crack.", ["hit", "impact", "damage", "punch"], 0.6, 0.08)
def hit():
    thump = tone("sine", np.linspace(180, 60, int(RATE * 0.12)), 0.12, attack=0.001, curve=3)
    crack = lowpass(noise(0.08), 3500) * env(int(RATE * 0.08), 0.001, True, 6)
    return mix(thump, crack * 1.4)


@sound("Rewards", "Rising arpeggio ending on a held chord.", ["level", "upgrade", "rank", "xp"])
def level_up():
    notes = ["C5", "E5", "G5", "C6"]
    run = seq(*[tone("square", note(n), 0.09, curve=1.2) * 0.35 for n in notes[:-1]], gap=-0.01)
    final = mix(
        tone("square", note("C6"), 0.5, curve=2.5) * 0.35,
        tone("triangle", note("G6"), 0.5, curve=3) * 0.2,
    )
    return seq(run, final, gap=-0.01)


@sound("UI", "Short, crisp button click.", ["ui", "click", "button", "tap"], 0.4, 0.04)
def ui_click():
    return mix(
        tone("sine", 1800, 0.03, attack=0.0005, curve=6) * 0.6,
        lowpass(noise(0.015), 6000) * env(int(RATE * 0.015), 0.0005, True, 4) * 0.4,
    )


@sound("UI", "Very soft hover tick.", ["ui", "hover"], 0.25, 0.03)
def ui_hover():
    return tone("sine", 1200, 0.04, attack=0.004, curve=3) * 0.25


@sound("Rewards", "Three-note cha-ching for buying things.", ["purchase", "buy", "shop", "cash"])
def purchase():
    return seq(
        tone("triangle", note("E5"), 0.08, curve=1.5) * 0.5,
        tone("triangle", note("A5"), 0.08, curve=1.5) * 0.5,
        mix(
            tone("square", note("C#6"), 0.35, curve=3) * 0.3,
            tone("triangle", note("E6"), 0.35, curve=3) * 0.3,
        ),
        gap=-0.005,
    )


@sound("UI", "Two descending low notes for denied actions.", ["ui", "error", "denied", "fail"], 0.45)
def error():
    return seq(
        tone("square", note("D#4"), 0.12, curve=1.5) * 0.35,
        tone("square", note("A3"), 0.22, curve=2.5) * 0.35,
        gap=0.02,
    )


@sound("Movement", "Quick upward chirp.", ["jump", "movement", "obby"], 0.35, 0.06)
def jump():
    sweep = np.linspace(note("C5"), note("C6"), int(RATE * 0.14))
    return tone("square", sweep, 0.14, curve=2) * 0.3


@sound("Game flow", "Two-note chime for reaching a checkpoint.", ["checkpoint", "save", "stage", "obby"])
def checkpoint():
    return seq(
        tone("triangle", note("G5"), 0.1, curve=1.5) * 0.5,
        mix(
            tone("triangle", note("D6"), 0.45, curve=2.5) * 0.45,
            tone("sine", note("D7"), 0.45, curve=4) * 0.1,
        ),
        gap=-0.01,
    )


# UI

@sound("UI", "Soft rising pop when a menu opens.", ["ui", "open", "menu", "panel"], 0.4)
def ui_open():
    return shaped(osc("sine", ramp(500, 900, 0.09, 0.6), 0.09), 0.002, 2) * 0.6


@sound("UI", "Soft falling pop when a menu closes.", ["ui", "close", "menu", "back"], 0.4)
def ui_close():
    return shaped(osc("sine", ramp(850, 450, 0.09, 0.6), 0.09), 0.002, 2) * 0.6


@sound("UI", "Two-tone ping for a new notification or message.", ["ui", "notification", "alert", "message"])
def notification():
    return seq(tone("sine", note("E6"), 0.12, curve=2) * 0.5, tone("sine", note("B6"), 0.3, curve=3) * 0.5, gap=-0.02)


@sound("UI", "Bright major chime for a task done right.", ["ui", "success", "complete", "quest"])
def success():
    return seq(tone("triangle", note("C6"), 0.08, curve=1.5) * 0.5, tone("triangle", note("E6"), 0.08, curve=1.5) * 0.5,
               mix(tone("triangle", note("G6"), 0.4, curve=3) * 0.4, tone("sine", note("C7"), 0.4, curve=4) * 0.15), gap=-0.005)


@sound("UI", "Woodblock tick for each second of a countdown.", ["countdown", "tick", "timer", "round"], 0.45)
def countdown_tick():
    return mix(tone("sine", 1400, 0.05, attack=0.0005, curve=8) * 0.6, tone("triangle", 700, 0.05, attack=0.0005, curve=8) * 0.3)


@sound("UI", "Higher, longer beep for GO at the end of a countdown.", ["countdown", "go", "start", "race"], 0.5)
def countdown_go():
    return mix(tone("square", note("A5"), 0.45, curve=2.5) * 0.3, tone("triangle", note("A6"), 0.45, curve=3) * 0.2)


@sound("UI", "Urgent double beep for time running out.", ["timer", "warning", "hurry", "low time"], 0.45)
def timer_warning():
    beep = tone("square", note("F#5"), 0.08, curve=1) * 0.3
    return seq(beep, beep, gap=0.06)


@sound("UI", "Sparkly ascending run for claiming a reward.", ["reward", "claim", "daily", "gift", "quest"])
def reward_claim():
    notes = ["G5", "B5", "D6", "G6", "B6"]
    return seq(*[tone("triangle", note(n), 0.07 if i < 4 else 0.45, curve=1.5 if i < 4 else 3) * 0.4
                 for i, n in enumerate(notes)], gap=-0.015)


# Rewards

@sound("Rewards", "Glassy high glint for gems and diamonds.", ["gem", "diamond", "pickup", "currency"], 0.45, 0.05)
def gem_pickup():
    return mix(tone("sine", note("E7"), 0.35, curve=4) * 0.4, tone("sine", note("B7"), 0.3, curve=5) * 0.25,
               seq(np.zeros(int(RATE * 0.04)), tone("sine", note("G#7"), 0.3, curve=5) * 0.25))


@sound("Rewards", "Quick coin cascade for collecting cash or income.", ["cash", "money", "collect", "tycoon", "steal"], 0.5, 0.04)
def cash_burst():
    coins = [tone("square", note(n), 0.06, curve=2) * 0.25 for n in ["E6", "G6", "B6", "E7"]]
    return seq(*coins, tone("square", note("E7"), 0.25, curve=3) * 0.25, gap=-0.02)


@sound("Rewards", "Big whoosh-up and chord for rebirth or prestige.", ["rebirth", "prestige", "simulator"])
def rebirth():
    riser = bandpass(noise(0.6), ramp(300, 3000, 0.6, 2), ramp(800, 6000, 0.6, 2)) * env(int(RATE * 0.6), 0.5, False)
    chord = mix(*[tone("triangle", note(n), 0.9, curve=2.5) * 0.25 for n in ["C5", "E5", "G5", "C6"]])
    return seq(riser * 0.8, chord, gap=-0.02)


@sound("Rewards", "Creak and sparkle of a chest opening.", ["chest", "loot", "crate", "open"])
def chest_open():
    creak = shaped(osc("square", ramp(110, 160, 0.25) + 8 * np.sin(np.linspace(0, 60, int(RATE * 0.25))), 0.25), 0.01, 1) * 0.15
    sparkle = seq(*[tone("sine", note(n), 0.1, curve=3) * 0.3 for n in ["C7", "E7", "G7", "C8"]], gap=-0.06)
    return seq(lowpass(creak, 1200), sparkle, gap=-0.05)


@sound("Rewards", "Launch whistle and pop of a firework.", ["firework", "win", "celebrate", "event"], 0.5, 0.06)
def firework():
    whistle = shaped(osc("sine", ramp(900, 2200, 0.5, 0.7), 0.5), 0.05, 0.5) * 0.25
    pop = lowpass(noise(0.6), 2500) * env(int(RATE * 0.6), 0.001, True, 5)
    crackle = (rng.uniform(0, 1, int(RATE * 0.6)) > 0.996) * rng.uniform(-1, 1, int(RATE * 0.6)) * np.linspace(1, 0, int(RATE * 0.6))
    return seq(whistle, mix(pop * 1.2, crackle * 0.6), gap=0)


@sound("Rewards", "Fast clicky tick for spinning wheels and crate rolls.", ["spin", "wheel", "crate", "unbox", "roll"], 0.35, 0.03)
def spin_tick():
    return tone("triangle", 2000, 0.025, attack=0.0005, curve=8) * 0.6


# Pets and eggs

@sound("Pets & eggs", "Shell crack for an egg starting to hatch.", ["egg", "crack", "hatch", "pet"], 0.5, 0.06)
def egg_crack():
    crack = lambda d: bandpass(noise(d), 1500, 7000) * env(int(RATE * d), 0.0005, True, 8)
    return seq(crack(0.05), crack(0.04), crack(0.07), gap=0.04)


@sound("Pets & eggs", "Magical shimmer and pop as the pet appears.", ["egg", "hatch", "pet", "reveal", "steal an egg"])
def egg_hatch():
    pop = shaped(osc("sine", ramp(300, 900, 0.08), 0.08), 0.001, 2) * 0.5
    shimmer = seq(*[tone("sine", note(n), 0.12, curve=3) * 0.25 for n in ["G6", "B6", "D7", "G7", "B7"]], gap=-0.08)
    return seq(pop, shimmer, gap=-0.02)


@sound("Pets & eggs", "Triumphant fanfare stab for a legendary pull.", ["rarity", "legendary", "reveal", "unbox"], 0.55)
def rarity_legendary():
    hit = mix(*[tone("square", note(n), 0.14, curve=1.5) * 0.18 for n in ["G4", "D5", "G5"]])
    hold = mix(*[tone("square", note(n), 1.0, curve=2) * 0.18 for n in ["C5", "E5", "G5", "C6"]],
               tone("sine", note("C7"), 1.0, curve=3) * 0.1)
    return seq(hit, hit, hold, gap=0.02)


@sound("Pets & eggs", "Sneaky swoosh-and-snag for grabbing someone's item.", ["steal", "grab", "steal a brainrot", "steal an egg"], 0.5, 0.05)
def steal_grab():
    swoosh = bandpass(noise(0.18), ramp(400, 2500, 0.18), ramp(1200, 6000, 0.18)) * env(int(RATE * 0.18), 0.1, True, 2)
    snag = tone("triangle", note("A5"), 0.12, curve=2) * 0.35
    return seq(swoosh * 1.4, snag, gap=-0.04)


# Combat

@sound("Combat", "Bigger impact with a high ring for critical hits.", ["critical", "crit", "hit", "damage"], 0.6, 0.06)
def crit_hit():
    return mix(hit() * 1.2, seq(np.zeros(int(RATE * 0.01)), tone("square", note("A6"), 0.25, curve=3) * 0.2))


@sound("Combat", "Airy whoosh of a swing or punch.", ["swing", "whoosh", "melee", "punch", "attack"], 0.45, 0.1)
def swing():
    n = int(RATE * 0.22)
    return bandpass(noise(0.22), ramp(500, 1500, 0.22), ramp(1500, 4500, 0.22)) * np.sin(np.linspace(0, np.pi, n)) ** 2 * 1.6


@sound("Combat", "Sharp metallic slash for swords and knives.", ["slash", "sword", "knife", "blade", "murder mystery"], 0.5, 0.08)
def slash():
    ring = mix(tone("sine", 3200, 0.2, curve=6) * 0.2, tone("sine", 4700, 0.15, curve=7) * 0.12)
    return mix(swing() * 0.9, seq(np.zeros(int(RATE * 0.08)), ring))


@sound("Combat", "Dull clang of a blocked attack.", ["block", "parry", "shield", "clang"], 0.5, 0.06)
def block():
    return mix(tone("square", 520, 0.18, attack=0.0005, curve=6) * 0.2, tone("sine", 1310, 0.25, attack=0.0005, curve=5) * 0.25,
               lowpass(noise(0.04), 4000) * env(int(RATE * 0.04), 0.0005, True, 4) * 0.5)


@sound("Combat", "Punchy pew for guns and blasters. Not a realistic gunshot.", ["gun", "blaster", "shoot", "pew", "murder mystery"], 0.45, 0.06)
def muzzle_flash():
    zap = shaped(osc("square", ramp(1800, 200, 0.16, 0.5), 0.16), 0.0005, 2) * 0.3
    puff = lowpass(noise(0.08), 3000) * env(int(RATE * 0.08), 0.0005, True, 5) * 0.6
    return mix(zap, puff)


@sound("Combat", "Deep boom with a rumbling tail.", ["explosion", "bomb", "boom"], 0.6, 0.05)
def explosion():
    n = int(RATE * 1.2)
    body = lowpass(noise(1.2), ramp(2500, 120, 1.2, 0.4)) * env(n, 0.002, True, 2.5)
    sub = tone("sine", ramp(90, 35, 1.2), 1.2, attack=0.002, curve=3)
    return mix(body * 3.5, sub * 0.8)


@sound("Combat", "Soft descending blip when a character is eliminated.", ["death", "eliminate", "lose life", "respawn"], 0.45)
def death():
    return seq(tone("triangle", note("E5"), 0.1, curve=1.5) * 0.4, tone("triangle", note("C5"), 0.1, curve=1.5) * 0.4,
               shaped(osc("triangle", ramp(note("A4"), note("A3"), 0.35), 0.35), 0.003, 2) * 0.4, gap=0.01)


@sound("Combat", "Gentle rising shimmer for healing.", ["heal", "health", "regen", "potion"], 0.45)
def heal():
    return mix(shaped(osc("sine", ramp(note("C6"), note("C7"), 0.6, 0.7), 0.6), 0.05, 2) * 0.3,
               seq(*[tone("sine", note(n), 0.15, curve=3) * 0.15 for n in ["E6", "G6", "C7", "E7"]], gap=-0.05))


@sound("Combat", "Rising hum that builds before a big move.", ["charge", "power", "ability", "cast"], 0.35)
def charge_up():
    n = int(RATE * 0.8)
    hum = osc("square", ramp(110, 440, 0.8, 1.5), 0.8) * np.linspace(0.1, 1, n)
    return lowpass(hum, ramp(400, 4000, 0.8, 1.5)) * 0.4


@sound("Combat", "Crackling electric zap.", ["lightning", "electric", "zap", "shock"], 0.5, 0.06)
def lightning_strike():
    n = int(RATE * 0.35)
    buzz = osc("square", 60 + 40 * rng.uniform(-1, 1, n), 0.35) * (rng.uniform(0, 1, n) > 0.5)
    crack = bandpass(noise(0.35), 1500, 9000) * env(n, 0.0005, True, 3)
    return mix(buzz * env(n, 0.001, True, 2) * 0.3, crack * 1.2)


@sound("Combat", "Glassy shatter for ice and freeze effects.", ["ice", "freeze", "shatter", "glass"], 0.5, 0.05)
def ice_shatter():
    n = int(RATE * 0.5)
    tinkles = mix(*[seq(np.zeros(int(RATE * rng.uniform(0, 0.15))), tone("sine", rng.uniform(3000, 7000), 0.2, curve=6) * 0.12)
                    for _ in range(10)])
    crash = bandpass(noise(0.5), 2500, 10000) * env(n, 0.0005, True, 5)
    return mix(crash * 1.4, tinkles)


# Movement

@sound("Movement", "Soft thud when you land.", ["land", "fall", "thud", "movement"], 0.4, 0.08)
def land():
    return mix(tone("sine", ramp(140, 60, 0.12), 0.12, attack=0.001, curve=3) * 0.7,
               lowpass(noise(0.06), 1500) * env(int(RATE * 0.06), 0.0005, True, 4) * 0.5)


@sound("Movement", "Airy bounce for a second jump.", ["double jump", "air", "movement", "obby"], 0.35, 0.05)
def double_jump():
    return mix(jump() * 0.8, bandpass(noise(0.12), 2000, 6000) * env(int(RATE * 0.12), 0.01, True, 3) * 0.6)


@sound("Movement", "Fast whoosh for a dash or speed boost.", ["dash", "speed", "boost", "movement"], 0.45, 0.08)
def dash():
    n = int(RATE * 0.25)
    return bandpass(noise(0.25), ramp(800, 3000, 0.25), ramp(2500, 8000, 0.25)) * np.sin(np.linspace(0, np.pi, n)) ** 3 * 1.8


@sound("Movement", "Warbling warp for teleports and portals.", ["teleport", "warp", "portal", "movement"], 0.45)
def teleport():
    n = int(RATE * 0.5)
    wobble = ramp(400, 1600, 0.5, 1.5) * (1 + 0.08 * np.sin(np.linspace(0, 2 * np.pi * 18, n)))
    return shaped(osc("sine", wobble, 0.5), 0.02, 1.5) * 0.4 + shaped(osc("triangle", wobble * 1.5, 0.5), 0.02, 2) * 0.15


@sound("Movement", "Water splash.", ["water", "splash", "swim", "pool"], 0.5, 0.08)
def splash():
    n = int(RATE * 0.5)
    body = lowpass(noise(0.5), ramp(4000, 800, 0.5)) * env(n, 0.002, True, 3)
    bloop = tone("sine", ramp(300, 700, 0.1), 0.1, curve=2) * 0.3
    return mix(body * 1.5, bloop)


# Game flow

@sound("Game flow", "Three rising tones to start a round.", ["round", "start", "match", "murder mystery"], 0.5)
def round_start():
    return seq(*[tone("square", note(n), 0.14 if n != "C6" else 0.4, curve=1.5 if n != "C6" else 3) * 0.3
                 for n in ["C5", "G5", "C6"]], gap=0.04)


@sound("Game flow", "Short victory fanfare.", ["win", "victory", "round end", "finish"], 0.55)
def victory():
    lead = [("C5", 0.12), ("E5", 0.12), ("G5", 0.12), ("C6", 0.25), ("G5", 0.1), ("C6", 0.6)]
    melody = seq(*[tone("square", note(n), d, curve=1.5) * 0.28 for n, d in lead], gap=0.01)
    bass = seq(np.zeros(int(RATE * 0.5)), tone("triangle", note("C4"), 0.9, curve=2) * 0.4)
    return mix(melody, bass)


@sound("Game flow", "Sad descending trombone-ish phrase.", ["lose", "defeat", "game over", "fail"], 0.4)
def defeat():
    notes = [("G4", 0.25), ("F#4", 0.25), ("F4", 0.25)]
    parts = [tone("square", note(n), d, curve=1.2) * 0.25 for n, d in notes]
    fall = osc("square", ramp(note("E4"), note("C4"), 0.8) * (1 + 0.015 * np.sin(np.linspace(0, 2 * np.pi * 6, int(RATE * 0.8)))), 0.8)
    return lowpass(seq(*parts, shaped(fall, 0.01, 1.5) * 0.25, gap=0.03), 2500)


@sound("Game flow", "Two-tone alarm loop for intruders and stolen items.", ["alarm", "alert", "steal", "base", "siren"], 0.3)
def alarm():
    hi, lo = tone("square", 960, 0.25, curve=0.3) * 0.25, tone("square", 720, 0.25, curve=0.3) * 0.25
    return lowpass(seq(hi, lo, hi, lo, gap=0), 3500)


@sound("Game flow", "Heavy click of a lock or base door closing.", ["lock", "door", "base", "close", "steal"], 0.5, 0.04)
def lock():
    click = lambda f: mix(tone("square", f, 0.03, attack=0.0003, curve=8) * 0.3,
                          lowpass(noise(0.03), 5000) * env(int(RATE * 0.03), 0.0003, True, 6) * 0.6)
    return seq(click(1800), click(1100), gap=0.05)


@sound("Game flow", "Soft soil pat for planting a seed.", ["plant", "seed", "farm", "grow a garden"], 0.45, 0.08)
def plant():
    pat = lambda: lowpass(noise(0.07), 900) * env(int(RATE * 0.07), 0.001, True, 4)
    return seq(pat() * 1.5, pat() * 1.2, tone("sine", note("G6"), 0.15, curve=4) * 0.15, gap=0.03)


@sound("Game flow", "Leafy rustle and pop for harvesting a crop.", ["harvest", "crop", "farm", "collect", "grow a garden"], 0.5, 0.06)
def harvest():
    rustle = bandpass(noise(0.15), 2000, 7000) * env(int(RATE * 0.15), 0.02, True, 2)
    pop = shaped(osc("sine", ramp(400, 1000, 0.07), 0.07), 0.001, 2) * 0.5
    return seq(rustle * 0.8, pop, gap=-0.03)


RECIPES = [entry["fn"] for entry in SOUNDS.values()]


def write(name, samples):
    peak = np.max(np.abs(samples))
    samples = samples / peak * 0.89  # about -1 dBFS peak, consistent loudness across the set
    fade = min(len(samples), int(RATE * 0.005))
    samples[-fade:] *= np.linspace(1, 0, fade)  # no click at the end
    pcm = (samples * 32767).astype(np.int16)

    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        with wave.open(tmp.name, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(pcm.tobytes())
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", tmp.name,
             "-c:a", "libvorbis", "-q:a", "6", "-map_metadata", "-1", "-fflags", "+bitexact",
             str(OUT / f"{name}.ogg")],
            check=True,
        )


def main():
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.ogg"):
        if old.stem not in SOUNDS:
            old.unlink()
    for recipe in RECIPES:
        write(recipe.__name__, recipe())
        print(f"sfx/{recipe.__name__}.ogg")


if __name__ == "__main__":
    main()
