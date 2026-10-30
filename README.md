<p align="center"><img src="brand/baseplate-mark-ink.svg" width="96" alt="Baseplate"></p>

<h1 align="center">baseplate</h1>
<p align="center"><b>Your AI builds better Roblox games, faster and cheaper.</b></p>
<p align="center"><a href="https://baseplatehq.github.io/baseplate/">Website</a> · <a href="https://www.npmjs.com/package/baseplate-cli">npm</a></p>

---

Baseplate scans free Creator Store effect packs for hidden scripts, splits the safe ones into single effects, and gives each effect an agent name and description. Your AI searches in plain words and gets back names like `explosion/fire`, `celebrate/confetti` and `hazard/lava`, instead of hunting through thumbnails.

- **600 effects from 148 safe packs.** Browse them with their metadata at [baseplate/components](https://baseplatehq.github.io/baseplate/components/).
- **Pinned and checked.** `add_vfx` refuses an effect if its pack changed since the scan, and records what you added in `vfx.json`.
- **One line to play.** `Juice.play("explosion/fire", part)`, or `Juice.attach("hazard/lava", part)` for loops.

## Connect your AI (MCP)

```
claude mcp add baseplate -- npx -y baseplate-cli mcp
```

Then ask, for example "use baseplate to add an explosion when the rocket hits". You also need the Roblox Studio MCP.

Tools: `find_vfx`, `add_vfx`.

## Repo

```
registry/   the store effect index, pack thumbnails and the Juice runtime (published to docs/r/)
pipeline/   the Creator Store scan, effect naming and thumbnails
cli/        npx baseplate-cli and the MCP server
docs/       the website (GitHub Pages)
brand/      logo files
```

## License

MIT. Copy it, fork it, ship with it.

Not affiliated with Roblox Corporation.
