# Registry: VFX and sounds

Good effects and sounds for a v0 Roblox game, ready to use. Like shadcn/ui: nothing to depend on. Your agent copies the files into your game, and you own them.

## Use it

Browse and preview everything at https://abdullahridwan.github.io/baseplate/components/. Then run, from your Rojo project root:

```
npx baseplate-cli add coin_pickup confetti
```

Or tell your agent:

```
Add coin_pickup and confetti from https://abdullahridwan.github.io/baseplate/r/index.json
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

**Effects** (built-in Roblox textures, nothing to upload)

| Name | What it looks like |
|---|---|
| `coin_pickup` | Gold sparkle burst with a soft glow |
| `hit` | White-orange impact sparks with a flash |
| `level_up` | Rising blue sparkles with an expanding ring |
| `confetti` | Colourful confetti that pops and flutters down |
| `heal` | Soft green motes drifting upward |
| `explosion` | Fireball, embers and smoke (visual only) |

**Sounds** (original, CC0)

`coin_pickup`, `hit`, `level_up`, `ui_click`, `ui_hover`, `purchase`, `error`, `jump`, `checkpoint`

Items that share a name (`coin_pickup`, `hit`, `level_up`) pair up: `Juice.play` fires both.

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
tools/          gen_sfx.py makes the sounds, check_registry.py validates index.json
```

## Adding to it

- **Effect:** add `vfx/<name>.luau` (copy one as a template) and its entry in `index.json`.
- **Sound:** add a recipe to `tools/gen_sfx.py`, run it, then add the entry. Sounds from elsewhere must be CC0 or made by us, with the source noted.
- Run `python3 registry/tools/check_registry.py`, then `python3 registry/tools/build_registry.py` to publish to `docs/r/`, which the website and CLI read from.

The bar is that it fits the set. A few good items beat many uneven ones. See [PLAN.md](../PLAN.md) for what's next (music, previews, packs per game type).

Licenses: code and effects MIT, sounds CC0-1.0.
