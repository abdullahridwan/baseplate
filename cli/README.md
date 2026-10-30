# baseplate-cli

Safe VFX and sounds for Roblox, as an MCP server your AI agent can search and add from.

```bash
claude mcp add baseplate -- npx -y baseplate-cli mcp
```

Then ask your agent for an effect, for example "add a coin pickup effect" or "find a safe fire explosion pack".

- `search_components` and `add_component`: 53 effects and 50 sounds, copied into your project. The files are yours.
- `find_vfx` and `add_vfx`: 600 single effects from free Creator Store packs that passed a safety scan, each with an agent name like `explosion/fire` or `celebrate/confetti`. One `add_vfx` call checks the pack is unchanged, records it in a `vfx.json` lockfile, and returns one snippet for the Roblox Studio MCP. Then `Juice.play("explosion/fire", part)`.

Site: https://baseplatehq.github.io/baseplate/

MIT license. Not affiliated with Roblox Corporation.
