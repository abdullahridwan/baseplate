# baseplate-cli

Safe Creator Store VFX for Roblox, as an MCP server your AI agent can search and add from.

```bash
claude mcp add baseplate -- npx -y baseplate-cli mcp
```

Then ask your agent, for example "use baseplate to add an explosion when the rocket hits". It also needs the Roblox Studio MCP.

- `find_vfx`: 600 single effects from free Creator Store packs that passed a safety scan, each with an agent name like `explosion/fire` or `celebrate/confetti` and a one-line description. Returns up to 5.
- `add_vfx`: checks each pack is unchanged since the scan, records it in a `vfx.json` lockfile, and returns one snippet for the Roblox Studio MCP. Then `Juice.play("explosion/fire", part)`.

Browse every effect: https://baseplatehq.github.io/baseplate/components/

MIT license. Not affiliated with Roblox Corporation.
