#!/usr/bin/env node
// baseplate: safe Creator Store VFX for Roblox, with agent names.
//   npx baseplate-cli mcp                 (run as an MCP server for Claude Code and other agents)
//   npx baseplate-cli find fire explosion (search the effects yourself)
// BASEPLATE_REGISTRY points at another registry: a URL or a local folder.

import { loadEffects, searchEffects } from "../lib/registry.js";

const bold = (s) => `\x1b[1m${s}\x1b[0m`;
const dim = (s) => `\x1b[2m${s}\x1b[0m`;
const yellow = (s) => `\x1b[33m${s}\x1b[0m`;

async function find(words) {
	if (words.length === 0) throw new Error("say what you want, e.g. 'baseplate-cli find fire explosion'");
	const index = await loadEffects();
	const found = searchEffects(index, words.join(" "));
	if (found.length === 0) return console.log(`Nothing matches. Try a category: ${index.categories.join(", ")}`);
	for (const e of found) console.log(`${bold(e.name)}  ${e.description} ${dim(`(from "${e.pack}")`)}`);
	console.log(dim("\nAsk your AI: use baseplate to add <name>"));
}

async function mcp() {
	const { serve } = await import("../lib/mcp.js");
	serve();
}

const [command, ...args] = process.argv.slice(2);
const commands = { find: () => find(args), mcp };

if (!commands[command]) {
	console.log(`${bold("baseplate")}: safe Creator Store VFX for Roblox\n
  npx baseplate-cli mcp            run as an MCP server for your AI agent
  npx baseplate-cli find <words>   search the 600 effects yourself\n`);
	process.exit(command && command !== "help" ? 1 : 0);
}

commands[command]().catch((err) => {
	console.error(yellow("error: ") + err.message);
	process.exit(1);
});
