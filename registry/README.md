# Registry: VFX and sounds

Good effects and sounds for a v0 Roblox game, ready to use. Like shadcn/ui: nothing to depend on. Your agent copies the files into your game, and you own them.

## Use it

Browse and preview everything at https://baseplatehq.github.io/baseplate/components/. Then run, from your Rojo project root:

```
npx baseplate-cli add coin_pickup confetti
```

Or tell your agent:

```
Add coin_pickup and confetti from https://baseplatehq.github.io/baseplate/r/index.json
```

Then in your code:

```lua
local Juice = require(game.ReplicatedStorage.Shared.Juice)

Juice.play("coin_pickup", coinPart)        -- effect + sound together
Juice.vfx("explosion", Vector3.new(0, 5, 0))
Juice.sfx("ui_click")                       -- no target: plays flat (2D)
Juice.music("lobby")                        -- crossfades a looping track; Juice.music(nil) stops it
```

Effects work right away. Sounds need one step from you: **upload the `.ogg` to your own Roblox account** and give the agent the asset ID. Roblox only plays audio that's an uploaded asset, and owning it means nobody can delete it out from under your game.

## What's in it

53 effects and 50 sounds, chosen by what today's most-played Roblox games use: steal games (Steal An Egg, Steal a Brainrot), Murder Mystery 2, Adopt Me!, Grow a Garden, Blox Fruits, 99 Nights in the Forest and Brookhaven, plus the obby, tycoon and simulator basics. See [How we picked](#how-we-picked).

**Effects** (built-in Roblox textures, nothing to upload)

| Category | Effects |
|---|---|
| Rewards | `coin_pickup`, `gem_pickup`, `cash_burst`, `confetti`, `level_up`, `rebirth`, `purchase`, `chest_open`, `firework` |
| Pets & eggs | `egg_hatch`, `rarity_rare`, `rarity_epic`, `rarity_legendary`, `rarity_mythic`, `pet_aura`, `mutation_shimmer`, `steal_grab` |
| Combat | `hit`, `crit_hit`, `slash`, `block`, `muzzle_flash`, `ground_slam`, `shockwave`, `stun_stars`, `death`, `charge_up`, `explosion` |
| Elements | `fire_burst`, `ice_shatter`, `lightning_strike`, `splash`, `poison_cloud`, `dark_burst`, `holy_light`, `wind_gust` |
| Movement | `jump`, `land`, `double_jump`, `dash`, `teleport`, `checkpoint` |
| Farming | `plant`, `harvest`, `smoke_puff` |
| Auras & ambient | `aura_fire`, `aura_electric`, `aura_holy`, `shield_bubble`, `campfire`, `fireflies`, `portal`, `falling_leaves` |

Effects tagged `loop` (auras, campfire, portal) keep running: `local stop = Juice.attach("aura_fire", character)`, then `stop()`.

**Sounds** (original, synthesized from code, CC0)

| Category | Sounds |
|---|---|
| Rewards | `coin_pickup`, `level_up`, `purchase`, `gem_pickup`, `cash_burst`, `rebirth`, `chest_open`, `firework`, `spin_tick` |
| Combat | `hit`, `crit_hit`, `swing`, `slash`, `block`, `muzzle_flash`, `explosion`, `death`, `heal`, `charge_up`, `lightning_strike`, `ice_shatter` |
| UI | `ui_click`, `ui_hover`, `error`, `ui_open`, `ui_close`, `notification`, `success`, `countdown_tick`, `countdown_go`, `timer_warning`, `reward_claim` |
| Movement | `jump`, `land`, `double_jump`, `dash`, `teleport`, `splash` |
| Game flow | `checkpoint`, `round_start`, `victory`, `defeat`, `alarm`, `lock`, `plant`, `harvest` |
| Pets & eggs | `egg_crack`, `egg_hatch`, `rarity_legendary`, `steal_grab` |

Items that share a name (like `coin_pickup`, `slash`, `egg_hatch`) pair up: `Juice.play` fires both.

## How we picked

We ranked the games with the most players in October 2026 (live trackers disagree hour to hour, but the same handful lead every chart), looked at what each one leans on, and weighted those effects and sounds most:

| Game type | Leans on |
|---|---|
| Steal games (Steal An Egg, Steal a Brainrot) | cash income, steal grab, base lock and alarm, rarity reveals, egg hatching |
| Murder Mystery 2 | knife slash, blaster, round start and win/lose, death, crate spins |
| Adopt Me!, pet simulators | egg crack and hatch, rarity tiers, pet auras, rewards |
| Grow a Garden | plant, harvest, mutation shimmer, splash |
| Blox Fruits, anime fighters | hits, crits, slashes, blocks, elemental bursts, auras, charge-ups |
| 99 Nights in the Forest | campfire, fireflies, night ambience |
| Obby, tycoon, simulator | checkpoints, jumps, coins, purchases, rebirths, UI |

## For agents

1. Fetch `index.json`. Each item has `kind` (`runtime`, `vfx`, `sfx`), `files` and `after`.
2. Install everything in `requires` first (always `juice`). Skip any file that already exists.
3. Copy each file from `baseUrl` + `src` to `dest` in the user's project. `dest` follows the [core](../implementations/core/IMPLEMENTATION.md) layout: `src/shared` syncs to `ReplicatedStorage.Shared`.
4. Do every step in `after`, in order. For a sound, that means asking the user to upload it and adding the line to `Sounds.luau` with their asset ID.
5. Prefer calling Juice from client code. Effects are visual, and the client is where they look smooth.

**Done when**: `Juice.play("<name>", somePart)` in a LocalScript shows the effect and plays the sound with no `[Juice]` warnings in Output.

## Layout

```
index.json      every item: what it is, which files go where, what to do after
juice/          the runtime (init.luau + Sounds.luau)
vfx/            one file per effect: ParticleEmitter settings in plain Luau
sfx/            the sounds (.ogg)
tools/          gen_vfx.py (effect specs) and gen_sfx.py (sound recipes) are the catalog;
                build_index.py turns them into index.json; check_registry.py validates;
                build_registry.py publishes to docs/r/
```

## Adding to it

- **Effect:** add a spec to `EFFECTS` in `tools/gen_vfx.py` and run it. The same spec drives the Luau file and the website preview, and it's checked for settings Roblox would reject.
- **Sound:** add a recipe with `@sound(...)` to `tools/gen_sfx.py` and run it. Sounds from elsewhere must be CC0 or made by us, with the source noted.
- Then `python3 registry/tools/build_index.py`.
- Run `python3 registry/tools/check_registry.py`, then `python3 registry/tools/build_registry.py` to publish to `docs/r/`, which the website and CLI read from.

The bar is that it fits the set. A few good items beat many uneven ones. See [PLAN.md](../PLAN.md) for what's next (music, previews, packs per game type).

Licenses: code and effects MIT, sounds CC0-1.0.
