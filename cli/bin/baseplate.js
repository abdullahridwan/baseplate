#!/usr/bin/env node
// baseplate: copy VFX and sounds from the Baseplate registry into a Roblox (Rojo) project.
//   npx baseplate-cli list
//   npx baseplate-cli add coin_pickup confetti
//   npx baseplate-cli mcp            (run as an MCP server for Claude Code and other agents)
// Run it from the project root (where default.project.json is).
// BASEPLATE_REGISTRY points at another registry: a URL or a local folder containing index.json.

import { SOUNDS_FILE, install, loadIndex, resolveItems } from "../lib/registry.js";

const bold = (s) => `\x1b[1m${s}\x1b[0m`;
const dim = (s) => `\x1b[2m${s}\x1b[0m`;
const green = (s) => `\x1b[32m${s}\x1b[0m`;
const yellow = (s) => `\x1b[33m${s}\x1b[0m`;

async function add(names) {
	if (names.length === 0) throw new Error("name at least one item, e.g. 'baseplate add coin_pickup'");
	const r = await install(names);
	for (const w of r.warnings) console.log(yellow(`! ${w}\n`));
	for (const f of r.skipped) console.log(dim(`  skip  ${f} (exists)`));
	for (const f of r.added) console.log(green("  add   ") + f);
	for (const f of r.edited) console.log(green("  edit  ") + f);

	console.log("\n" + bold("Done.") + " Use it:");
	console.log(dim('  local Juice = require(game.ReplicatedStorage.Shared.Juice)'));
	const items = resolveItems(await loadIndex(), names);
	for (const name of new Set(names)) {
		const kinds = items.filter((i) => i.name === name);
		const loop = kinds.find((i) => i.kind === "vfx" && i.preview?.loop);
		const hint = loop ? loop.usage : kinds.length > 1 ? `Juice.play("${name}", part)` : kinds[0].usage;
		console.log(dim(`  ${hint}`));
	}

	if (r.uploads.length > 0) {
		console.log("\n" + bold("One step left for sounds:") + " Roblox only plays uploaded audio.");
		console.log("  1. Upload these at https://create.roblox.com/dashboard/creations (Upload asset > Audio):");
		for (const f of r.uploads) console.log(`       ${f}`);
		console.log(`  2. Paste each asset ID into its id = "" in ${SOUNDS_FILE}`);
	}
}

async function list() {
	const index = await loadIndex();
	for (const kind of ["vfx", "sfx"]) {
		console.log(bold(kind === "vfx" ? "Effects" : "Sounds"));
		const items = index.items.filter((i) => i.kind === kind);
		for (const category of new Set(items.map((i) => i.category))) {
			console.log(`  ${dim(category)}`);
			for (const item of items.filter((i) => i.category === category)) {
				console.log(`    ${item.name.padEnd(18)} ${dim(item.description)}`);
			}
		}
		console.log();
	}
	console.log(dim("Add one: npx baseplate-cli add <name>"));
}

async function mcp() {
	const { serve } = await import("../lib/mcp.js");
	serve();
}

const [command, ...args] = process.argv.slice(2);
const commands = { add: () => add(args), list, mcp };

if (!commands[command]) {
	console.log(`${bold("baseplate")}: VFX and sounds for Roblox games\n
  npx baseplate-cli list           show every effect and sound
  npx baseplate-cli add <name...>  copy items into this project
  npx baseplate-cli mcp            run as an MCP server for your AI agent\n`);
	process.exit(command && command !== "help" ? 1 : 0);
}

commands[command]().catch((err) => {
	console.error(yellow("error: ") + err.message);
	process.exit(1);
});
