<p align="center"><img src="brand/baseplate-mark-ink.svg" width="96" alt="Baseplate"></p>

<h1 align="center">baseplate</h1>
<p align="center"><b>Your AI builds better Roblox games, faster and cheaper.</b></p>
<p align="center"><a href="https://baseplatehq.github.io/baseplate/">Website</a> · <a href="https://www.npmjs.com/package/baseplate-cli">npm</a></p>

---

Baseplate is a component library for Roblox that AI agents use through MCP. Your agent searches in plain words and gets back short, agent-readable names, instead of hunting through Creator Store thumbnails.

- **600 Creator Store effects.** Free packs that passed a safety scan, split into single effects with agent names like `explosion/fire`, `celebrate/confetti` and `hazard/lava`. `add_vfx` checks the pack hasn't changed, pins it in `vfx.json`, and returns one snippet for the Roblox Studio MCP.
- **Our own effects and sounds.** Copied into your project as files you own, like shadcn/ui. Browse them at [baseplate/components](https://baseplatehq.github.io/baseplate/components/).
- **One runtime.** `Juice.play("explosion/fire", part)` plays either kind by name.

## Connect your AI (MCP)

```
claude mcp add baseplate -- npx -y baseplate-cli mcp
```

Then ask for what you need, for example "add an explosion when the rocket hits".

Tools: `list_components`, `search_components`, `get_component`, `add_component`, `find_vfx`, `add_vfx`.

Or use the CLI from your Rojo project root:

```
npx baseplate-cli add coin_pickup confetti
```

## Repo

```
registry/   effects, sounds, the Juice runtime and the store effect index (published to docs/r/)
pipeline/   the Creator Store scan and effect naming
cli/        npx baseplate-cli and the MCP server
docs/       the website (GitHub Pages)
brand/      logo files
```

## License

MIT. Copy it, fork it, ship with it.

Not affiliated with Roblox Corporation.
