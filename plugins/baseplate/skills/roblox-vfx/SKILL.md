---
name: roblox-vfx
description: Make Roblox particle effects look as good as the most popular Creator Store packs. Use when building, tuning, or reviewing ParticleEmitters, Beams, or Trails for hits, explosions, auras, projectiles, magic, fire, or any game-feel effect in a Roblox game.
---

# Roblox VFX that look good

These rules come from measuring the 40 most-voted free, script-free VFX packs on the
Creator Store (755 particle emitters and 123 beams, read on 2026-10-29). The numbers in
brackets are how often popular packs do it.

**Before you build anything:** call `find_vfx` from the Baseplate MCP. It returns single
effects from safe, scanned Creator Store packs by agent name (`explosion/fire`,
`hit/slash`, `aura/electric`). If one fits, add it with `add_vfx` and play it with
`Juice.play(name, part)`. Build from scratch only when nothing fits, using the rules below.

## 1. One effect is a stack of layers, not one emitter

Good effects put 3 to 8 emitters on one Attachment [75% of emitters sit in an
Attachment, not directly in a Part], and each one does one job:

| Layer | What it is | Key settings |
|---|---|---|
| **Flash / core** | One big, short, bright pop | `Emit(1)`, Lifetime 0.2 to 0.5, Speed 0, Brightness 5 to 25, LightEmission 0.5 to 1, highest ZOffset (3 to 4) |
| **Glow / bloom** | Soft halo that sells the light | Soft round texture, LightEmission 1, Size larger than the core, fades fast |
| **Shockwave / ring** | Flat ring that expands | `Orientation = VelocityPerpendicular`, Speed ~0, Size grows over life (e.g. 0 → 30), Lifetime ~0.75 |
| **Sparks / streaks** | Fast lines flying out | `Orientation = VelocityParallel`, Speed 10 to 25, Drag 1 to 3, Lifetime 0.3 to 1, Size shrinks to 0 |
| **Smoke / dust** | The slow aftermath | LightEmission 0, Lifetime 1 to 2, random Speed, high Drag (5 to 10), Size grows, often a 4x4 or 8x8 flipbook |
| **Debris / specks** | Small bits for texture | Many particles (20 to 60), small Size, random spin, Drag so they settle |

A one-emitter effect almost always looks flat. Add the layer that's missing before
tweaking numbers.

## 2. Bursts use Emit, not Rate

Impacts, explosions, and hits fire once. Popular packs leave the emitter's settings in
place and store the burst on the emitter as attributes [27% of emitters, almost all
burst effects]:

- `EmitCount`: how many particles to emit (common values: 1, 2, 5, 30 to 40)
- `EmitDelay`: seconds to wait before emitting (usually 0, sometimes 0.1 to 0.2 to stagger layers)
- `EmitDuration`: for short continuous bursts, how long to leave `Enabled` on

Keep `Enabled = false` on burst emitters and fire them with this:

```lua
-- Fires every burst emitter under root, using its EmitCount, EmitDelay, and EmitDuration attributes.
local function playBurst(root: Instance)
	for _, emitter in root:GetDescendants() do
		if not emitter:IsA("ParticleEmitter") then
			continue
		end
		local delay = emitter:GetAttribute("EmitDelay") or 0
		local count = emitter:GetAttribute("EmitCount") or 0
		local duration = emitter:GetAttribute("EmitDuration")
		task.delay(delay, function()
			if count > 0 then
				emitter:Emit(count)
			end
			if duration then
				emitter.Enabled = true
				task.delay(duration, function()
					emitter.Enabled = false
				end)
			end
		end)
	end
end
```

Clone the effect's Attachment into the target part, call `playBurst`, and destroy the
Attachment after the longest Lifetime plus delay.

## 3. Curves, not constants

- **Transparency fades out to 1** [84%]. A particle that pops out of existence looks cheap.
- **Fade in too** [61% start transparent]. Go from 1 to 0 in the first 5 to 10% of life, then back to 1.
- **Size changes over life** [about 60%]. Rings and smoke grow. Sparks and cores shrink. Use 3 or more keypoints for anything that matters [34%].
- **Use the envelope** [29% have random size]. A little randomness per particle hides repetition.

## 4. Randomize everything a little

- Random start Rotation of 0 to 360 [64%]. The fastest way to stop a burst looking stamped.
- Random spin with RotSpeed [33%], for example -200 to 200.
- A random Lifetime range [37%] and Speed range [21%], instead of a single value.

## 5. Light settings

- **LightInfluence = 0** [84%]. Effects should look the same in a dark cave and in daylight.
- **LightEmission high (0.8 to 1) for anything that glows** [57% at 0.5 or more]. It blends additively, so overlapping particles brighten instead of muddying.
- **LightEmission 0 for smoke, dust, blood, and debris.** Additive smoke turns into a grey glow.
- **Brightness 1 to 10**, up to 25 for a one-frame flash [38% above 1].
- **ZOffset sorts the layers** [44% use it]. Put the flash and core in front (2 to 4) so smoke never covers them.

## 6. Movement

- Most layers barely move: the median Speed is near 0, with movement coming from Size and the flipbook. Only sparks and debris travel.
- Use **Drag** instead of short lifetimes to stop fast particles [31%]. Things decelerate, they don't vanish mid-flight.
- **Gravity is rare** [8% fall, 7% rise]. Use Acceleration only for debris, embers, and blood.
- **LockedToPart = true for auras, projectiles, and anything attached to a moving character** [56%]. Leave it off for smoke trails that should hang in the air.

## 7. Flipbooks for fire, smoke, and explosions

A third of popular emitters use a flipbook texture [34%]:

- `FlipbookLayout = Grid4x4` or `Grid8x8`
- `FlipbookMode = OneShot` for explosions and impacts (plays once over the particle's life)
- `Loop` for fire and steady smoke

Animated textures are what make fire look like fire instead of orange dots.

## 8. Beams for energy

Beams appear in energy, lightning, and magic packs:

- `LightEmission = 1`
- `Segments` around 50
- `TextureSpeed` around 1 to 3 (negative to reverse) so the energy flows
- `FaceCamera = true` for lasers and lightning

## Quick defaults

When you have no reference, start here and adjust:

| Setting | Glow layer | Smoke layer | Spark layer |
|---|---|---|---|
| Lifetime | 0.3 to 0.6 | 1 to 2 | 0.3 to 1 |
| Speed | 0 | 0.5 to 10 | 10 to 25 |
| Drag | 0 | 5 to 10 | 1 to 3 |
| LightEmission | 1 | 0 | 0.6 |
| LightInfluence | 0 | 0 | 0 |
| Orientation | FacingCamera | FacingCamera | VelocityParallel |
| Size | grows a little | grows | shrinks to 0 |
| Transparency | 1 → 0 → 1 | 0.5 → 0 → 1 | 0 → 1 |
| Rotation | 0 to 360 | 0 to 360 | 0 |
| ZOffset | 2 to 4 | 0 to 0.5 | 1 |

## Checklist before you call an effect done

1. At least three layers, each with one job.
2. Bursts fire with `Emit` from `EmitCount`, not by toggling Rate.
3. Every emitter fades out to fully transparent.
4. Start rotation is randomized.
5. LightInfluence is 0, glow layers are additive, and smoke isn't.
6. The core sits in front through ZOffset.
7. The effect cleans itself up after its longest lifetime.
