#!/usr/bin/env node
// baseplate: copy VFX and sounds from the Baseplate registry into a Roblox (Rojo) project.
//   npx baseplate-cli list
//   npx baseplate-cli add coin_pickup confetti
// Run it from the project root (where default.project.json is).
// BASEPLATE_REGISTRY points at another registry: a URL or a local folder containing index.json.

import { existsSync } from "node:fs";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";

const REGISTRY = process.env.BASEPLATE_REGISTRY || "https://abdullahridwan.github.io/baseplate/r/";
const SOUNDS_FILE = "src/shared/Juice/Sounds.luau";
const isUrl = (s) => /^https?:\/\//.test(s);

const bold = (s) => `\x1b[1m${s}\x1b[0m`;
const dim = (s) => `\x1b[2m${s}\x1b[0m`;
const green = (s) => `\x1b[32m${s}\x1b[0m`;
const yellow = (s) => `\x1b[33m${s}\x1b[0m`;

async function fetchFile(rel, { binary = false } = {}) {
	if (!isUrl(REGISTRY)) {
		const path = resolve(REGISTRY, rel);
		return binary ? readFile(path) : readFile(path, "utf8");
	}
	const url = new URL(rel, REGISTRY.endsWith("/") ? REGISTRY : REGISTRY + "/");
	const res = await fetch(url);
	if (!res.ok) throw new Error(`could not fetch ${url} (${res.status})`);
	return binary ? Buffer.from(await res.arrayBuffer()) : res.text();
}

async function loadIndex() {
	return JSON.parse(await fetchFile("index.json"));
}

// Items can share a name across kinds (coin_pickup is a vfx and an sfx); `add coin_pickup` installs both.
function resolveItems(index, names) {
	const picked = [];
	const seen = new Set();
	const visit = (name) => {
		const matches = index.items.filter((i) => i.name === name);
		if (matches.length === 0) throw new Error(`no item named '${name}'. Run 'npx baseplate-cli list' to see them all.`);
		for (const item of matches) {
			const key = `${item.kind}:${item.name}`;
			if (seen.has(key)) continue;
			seen.add(key);
			item.requires.forEach(visit);
			picked.push(item);
		}
	};
	names.forEach(visit);
	return picked;
}

function soundLine(item) {
	const { volume, pitchVariance } = item.sound;
	const pitch = pitchVariance ? `, pitchVariance = ${pitchVariance}` : "";
	return `\t${item.name} = { id = "", volume = ${volume}${pitch} },`;
}

// Adds the sound to the Sounds table with an empty id. Juice skips it (with one warning) until the id is filled in.
async function registerSound(item) {
	const source = await readFile(SOUNDS_FILE, "utf8");
	if (new RegExp(`^\\s*${item.name}\\s*=`, "m").test(source)) return false;
	const marker = "local Sounds: { [string]: SoundDef } = {\n";
	if (!source.includes(marker)) throw new Error(`couldn't find the Sounds table in ${SOUNDS_FILE}; add ${item.name} by hand`);
	await writeFile(SOUNDS_FILE, source.replace(marker, marker + soundLine(item) + "\n"));
	return true;
}

async function add(names) {
	if (names.length === 0) throw new Error("name at least one item, e.g. 'baseplate add coin_pickup'");
	if (!existsSync("default.project.json")) {
		console.log(yellow("! no default.project.json here. Run this from your Rojo project root.\n"));
	}
	const items = resolveItems(await loadIndex(), names);
	const uploads = [];

	for (const item of items) {
		for (const file of item.files) {
			if (existsSync(file.dest)) {
				console.log(dim(`  skip  ${file.dest} (exists)`));
				continue;
			}
			await mkdir(dirname(file.dest), { recursive: true });
			await writeFile(file.dest, await fetchFile(file.src, { binary: item.kind === "sfx" }));
			console.log(green("  add   ") + file.dest);
		}
		if (item.kind === "sfx") {
			if (await registerSound(item)) console.log(green("  edit  ") + `${SOUNDS_FILE} (${item.name})`);
			uploads.push(item);
		}
	}

	console.log("\n" + bold("Done.") + " Use it:");
	console.log(dim('  local Juice = require(game.ReplicatedStorage.Shared.Juice)'));
	for (const name of new Set(names)) {
		const kinds = items.filter((i) => i.name === name);
		const loop = kinds.find((i) => i.kind === "vfx" && i.preview?.loop);
		const hint = loop ? loop.usage : kinds.length > 1 ? `Juice.play("${name}", part)` : kinds[0].usage;
		console.log(dim(`  ${hint}`));
	}

	if (uploads.length > 0) {
		console.log("\n" + bold("One step left for sounds:") + " Roblox only plays uploaded audio.");
		console.log("  1. Upload these at https://create.roblox.com/dashboard/creations (Upload asset > Audio):");
		for (const item of uploads) console.log(`       ${item.files[0].dest}`);
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

const [command, ...args] = process.argv.slice(2);
const commands = { add: () => add(args), list };

if (!commands[command]) {
	console.log(`${bold("baseplate")}: VFX and sounds for Roblox games\n
  npx baseplate-cli list           show every effect and sound
  npx baseplate-cli add <name...>  copy items into this project\n`);
	process.exit(command && command !== "help" ? 1 : 0);
}

commands[command]().catch((err) => {
	console.error(yellow("error: ") + err.message);
	process.exit(1);
});
