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
    """One-pole lowpass; enough to take the fizz off noise."""
    a = np.exp(-2 * np.pi * cutoff / RATE)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


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

def coin_pickup():
    return seq(
        tone("square", note("B5"), 0.07, curve=1.5) * 0.5,
        tone("square", note("E6"), 0.28, curve=3) * 0.5,
        gap=-0.005,
    )


def hit():
    thump = tone("sine", np.linspace(180, 60, int(RATE * 0.12)), 0.12, attack=0.001, curve=3)
    crack = lowpass(noise(0.08), 3500) * env(int(RATE * 0.08), 0.001, True, 6)
    return mix(thump, crack * 1.4)


def level_up():
    notes = ["C5", "E5", "G5", "C6"]
    run = seq(*[tone("square", note(n), 0.09, curve=1.2) * 0.35 for n in notes[:-1]], gap=-0.01)
    final = mix(
        tone("square", note("C6"), 0.5, curve=2.5) * 0.35,
        tone("triangle", note("G6"), 0.5, curve=3) * 0.2,
    )
    return seq(run, final, gap=-0.01)


def ui_click():
    return mix(
        tone("sine", 1800, 0.03, attack=0.0005, curve=6) * 0.6,
        lowpass(noise(0.015), 6000) * env(int(RATE * 0.015), 0.0005, True, 4) * 0.4,
    )


def ui_hover():
    return tone("sine", 1200, 0.04, attack=0.004, curve=3) * 0.25


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


def error():
    return seq(
        tone("square", note("D#4"), 0.12, curve=1.5) * 0.35,
        tone("square", note("A3"), 0.22, curve=2.5) * 0.35,
        gap=0.02,
    )


def jump():
    sweep = np.linspace(note("C5"), note("C6"), int(RATE * 0.14))
    return tone("square", sweep, 0.14, curve=2) * 0.3


def checkpoint():
    return seq(
        tone("triangle", note("G5"), 0.1, curve=1.5) * 0.5,
        mix(
            tone("triangle", note("D6"), 0.45, curve=2.5) * 0.45,
            tone("sine", note("D7"), 0.45, curve=4) * 0.1,
        ),
        gap=-0.01,
    )


RECIPES = [coin_pickup, hit, level_up, ui_click, ui_hover, purchase, error, jump, checkpoint]


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
    for recipe in RECIPES:
        write(recipe.__name__, recipe())
        print(f"sfx/{recipe.__name__}.ogg")


if __name__ == "__main__":
    main()
