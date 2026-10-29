# Baseplate Desktop Extension for Claude Desktop

This is a Desktop Extension (DXT) source folder, not a finished .dxt file.

Build it, then install it in Claude Desktop Settings:

1. In this folder, run: `npx @anthropic-ai/dxt pack`
   That produces a `.dxt` file, which is a zip containing this manifest
   and the server code.
2. Open Claude Desktop, go to Settings > Extensions.
3. Drag the `.dxt` file into Settings, or use Advanced settings >
   Extension Developer > Install Extension, and select it.
4. Enable Baseplate, then check that its tools appear.

Why this route: a DXT is a one-click local install in Settings, with no
manual JSON editing and no npm publish needed, because the server code
is bundled in the extension itself. The server fetches the component
registry from Baseplate's published site, so it still needs internet.

Manual alternative, same server, no DXT:
Settings > Developer > Local MCP servers > Edit Config, add:

```json
{
  "mcpServers": {
    "baseplate": {
      "command": "npx",
      "args": ["-y", "baseplate-cli", "mcp"]
    }
  }
}
```

That manual route does need baseplate-cli published on npm, which it
is not yet. The DXT route does not.

Note: this manifest was built from the DXT spec examples and JSON
validated, but it has not yet been tested by dragging it into Claude
Desktop itself, because there is no Claude Desktop here to test with.
