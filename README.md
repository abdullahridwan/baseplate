<p align="center"><img src="brand/baseplate-mark-ink.svg" width="96" alt="Baseplate"></p>

<h1 align="center">baseplate</h1>
<p align="center"><b>Build better Roblox games.</b> The agent-native layer for Roblox.</p>
<p align="center"><a href="https://abdullahridwan.github.io/baseplate/">Website</a></p>

---

Every Roblox game is half generic: saves, checkpoints, cash, remotes, leaderboards. Baseplate is a set of implementation specs that any AI agent can build from, so a fast, cheap model lays the foundation and you only spend frontier-model tokens on what makes your game yours.

## Specs

| Spec | What the generic 50% includes |
|---|---|
| [core](implementations/core/IMPLEMENTATION.md) | Rojo layout, DataStore saves with retries, rate-limited remotes, service and controller loaders |
| [obby](implementations/obby/IMPLEMENTATION.md) | Saved stages, anti-skip checkpoints, kill bricks, respawn on your stage, stage HUD |
| [tycoon](implementations/tycoon/IMPLEMENTATION.md) | Claimable plots, cash, purchase buttons, droppers, collector, saved progress |
| [simulator](implementations/simulator/IMPLEMENTATION.md) | Click to collect, backpack capacity, sell zones, upgrades, rebirths |

## Use it

Point your agent (Claude Code, Cursor, Codex) at a spec:

```
Build the obby from https://github.com/abdullahridwan/baseplate/blob/main/implementations/obby/IMPLEMENTATION.md
```

Each spec runs in strict order, with a **Done when** check after every step and an acceptance test at the end. It stops at the generic 50% and lists the extension points where your part begins.

**Requirements:** Roblox Studio with API Services enabled, and [Rojo](https://rojo.space) 7+.

## Repo

```
implementations/   the specs, one folder per game type
brand/             logo files and brand guidelines
docs/              the website (GitHub Pages)
```

## Roadmap

- MCP server so agents pull specs and steps directly
- More game types: tower defense, horror, fighting
- One-command publishing (a fastlane for Roblox): build, upload, set metadata and go live, callable by agents
- Store assets: generated game icons, thumbnails and descriptions
- Cost and reliability benchmarks: frontier model from scratch vs. Baseplate

## License

MIT. Copy it, fork it, ship with it.

Not affiliated with Roblox Corporation.
