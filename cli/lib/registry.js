// Shared by the CLI and the MCP server: read the Baseplate registry and install items into a project.
// BASEPLATE_REGISTRY points at another registry: a URL or a local folder containing index.json.
// BASEPLATE_SITE points at another site root (for recipes): a URL or a local folder.

import { existsSync } from "node:fs";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";

export const REGISTRY = process.env.BASEPLATE_REGISTRY || "https://abdullahridwan.github.io/baseplate/r/";
export const SITE = process.env.BASEPLATE_SITE || "https://abdullahridwan.github.io/baseplate/";
export const SOUNDS_FILE = "src/shared/Juice/Sounds.luau";
export const RECIPES = ["core", "obby", "tycoon", "simulator"];

const isUrl = (s) => /^https?:\/\//.test(s);
const withSlash = (s) => (s.endsWith("/") ? s : s + "/");

async function fetchFrom(root, rel, { binary = false } = {}) {
	if (!isUrl(root)) {
		const path = resolve(root, rel);
		return binary ? readFile(path) : readFile(path, "utf8");
	}
	const url = new URL(rel, withSlash(root));
	const res = await fetch(url);
	if (!res.ok) throw new Error(`could not fetch ${url} (${res.status})`);
	return binary ? Buffer.from(await res.arrayBuffer()) : res.text();
}

export const fetchFile = (rel, opts) => fetchFrom(REGISTRY, rel, opts);

export async function loadIndex() {
	return JSON.parse(await fetchFile("index.json"));
}

export async function loadRecipe(name) {
	if (!RECIPES.includes(name)) throw new Error(`no recipe named '${name}'. Recipes: ${RECIPES.join(", ")}`);
	return fetchFrom(SITE, `recipes/${name}.md`);
}

// Items can share a name across kinds (coin_pickup is a vfx and an sfx); adding coin_pickup installs both.
export function resolveItems(index, names) {
	const picked = [];
	const seen = new Set();
	const visit = (name) => {
		const matches = index.items.filter((i) => i.name === name);
		if (matches.length === 0) throw new Error(`no item named '${name}'`);
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
async function registerSound(root, item) {
	const path = resolve(root, SOUNDS_FILE);
	const source = await readFile(path, "utf8");
	if (new RegExp(`^\\s*${item.name}\\s*=`, "m").test(source)) return false;
	const marker = "local Sounds: { [string]: SoundDef } = {\n";
	if (!source.includes(marker)) throw new Error(`couldn't find the Sounds table in ${SOUNDS_FILE}; add ${item.name} by hand`);
	await writeFile(path, source.replace(marker, marker + soundLine(item) + "\n"));
	return true;
}

// Installs items (and what they require) into the project at `root`.
// Returns what happened, so callers can report it however they like.
export async function install(names, root = process.cwd()) {
	if (names.length === 0) throw new Error("name at least one item, e.g. coin_pickup");
	const result = { added: [], skipped: [], edited: [], uploads: [], warnings: [] };
	if (!existsSync(resolve(root, "default.project.json"))) {
		result.warnings.push(`no default.project.json in ${root}; is this the Rojo project root?`);
	}
	const items = resolveItems(await loadIndex(), names);

	for (const item of items) {
		for (const file of item.files) {
			const dest = resolve(root, file.dest);
			if (existsSync(dest)) {
				result.skipped.push(file.dest);
				continue;
			}
			await mkdir(dirname(dest), { recursive: true });
			await writeFile(dest, await fetchFile(file.src, { binary: item.kind === "sfx" }));
			result.added.push(file.dest);
		}
		if (item.kind === "sfx") {
			if (await registerSound(root, item)) result.edited.push(`${SOUNDS_FILE} (${item.name})`);
			result.uploads.push(item.files[0].dest);
		}
	}
	return result;
}
