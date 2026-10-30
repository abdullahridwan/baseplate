# Baseplate for Claude Code

Install as a plugin, instead of adding the MCP server by hand:

```
/plugin marketplace add baseplatehq/baseplate
/plugin install baseplate@baseplate
```

Then restart Claude Code and run `/mcp` to check that `baseplate` is listed.

This plugin registers the Baseplate MCP server, which is started with
`npx -y baseplate-cli mcp`. That requires `baseplate-cli` 0.3.0 or later
to be published on npm. Until it is published, the plugin install will
succeed but the server will not start.

Manual alternative, same server:

```
claude mcp add baseplate -- npx -y baseplate-cli mcp
```

Agents are first class citizens here: the agent searches components by
description in text, not thumbnails, then adds them. See DIRECTION.md.

## Skills

- `roblox-vfx`: how to build and tune particle effects that look as good as the most
  popular Creator Store packs. Built from measuring 755 emitters in the 40 most-voted
  free VFX packs. Claude Code loads it automatically when you work on effects.
