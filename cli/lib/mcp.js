// Baseplate as an MCP server (stdio). Zero dependencies so `npx` starts fast.
//   claude mcp add baseplate -- npx -y baseplate-cli mcp
// Speaks newline-delimited JSON-RPC 2.0 on stdin/stdout. Never write anything else to stdout.

import { createInterface } from "node:readline";
import { SOUNDS_FILE, SAFE_VFX_FILE, install, loadIndex, fetchFile, loadEffects, searchEffects, storeUpdated, sameTime, insertSnippet, writeVfxLock } from "./registry.js";
import { readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

const SERVER = { name: "baseplate", version: "0.3.1" };
const SUPPORTED = ["2025-06-18", "2025-03-26", "2024-11-05"];

const INSTRUCTIONS = `Baseplate is a component library for Roblox: effects and sounds your agent can find and add safely.
- To add juice: search_components, then add_component. Sounds must be uploaded to the user's Roblox account; tell them which files to upload and where the IDs go.
- For Creator Store VFX: find_vfx, then add_vfx. Effects have agent names like explosion/fire, hit/electric, aura/dark, celebrate/confetti: category/element-modifiers. Categories: hit, explosion, aura, projectile, trail, pickup, celebrate, ambient, hazard, magic, heal, dash, spawn, death, weather, fire, smoke. If you can guess the name, call add_vfx directly. Every effect comes from a scanned, safe pack. add_vfx returns one Luau snippet: run it with the Roblox Studio MCP's execute_luau, then play the effect with Juice.play(name, target).`;

const TOOLS = [
	{
		name: "list_components",
		description: "List Baseplate components: visual effects (vfx) and sounds (sfx) for Roblox games.",
		inputSchema: {
			type: "object",
			properties: { kind: { type: "string", enum: ["vfx", "sfx"], description: "Only this kind" } },
		},
	},
	{
		name: "search_components",
		description: "Find components by what they're for, e.g. 'coin', 'button click', 'win', 'damage'.",
		inputSchema: {
			type: "object",
			properties: { query: { type: "string" } },
			required: ["query"],
		},
	},
	{
		name: "get_component",
		description: "Details for one component: description, files, usage, and for effects the full Luau source.",
		inputSchema: {
			type: "object",
			properties: { name: { type: "string" } },
			required: ["name"],
		},
	},
	{
		name: "add_component",
		description: "Copy components (and what they need, like the Juice runtime) into the user's Rojo project. Existing files are never overwritten. Sounds are registered in Sounds.luau with an empty id until the user uploads them.",
		inputSchema: {
			type: "object",
			properties: {
				names: { type: "array", items: { type: "string" }, minItems: 1, description: "Component names, e.g. [\"coin_pickup\", \"ui_click\"]" },
				project_dir: { type: "string", description: "Rojo project root (where default.project.json is). Defaults to the current directory." },
			},
			required: ["names"],
		},
	},
	{
		name: "find_vfx",
		description: "Find Creator Store VFX by what they are for, e.g. 'fire explosion' or 'electric aura'. Returns up to 5 single effects from safe, scanned packs, each with its agent name (category/element-modifiers) and a one-line description.",
		inputSchema: {
			type: "object",
			properties: { query: { type: "string" } },
			required: ["query"],
		},
	},
	{
		name: "add_vfx",
		description: "Add effects by agent name, e.g. ['explosion/fire', 'hit/electric']. Checks each pack is unchanged since its scan, adds the Juice runtime if missing, records the effects in vfx.json, and returns one Luau snippet to run with the Roblox Studio MCP's execute_luau. Refuses unknown or changed effects.",
		inputSchema: {
			type: "object",
			properties: {
				names: { type: "array", items: { type: "string" }, minItems: 1, description: "Agent names from find_vfx" },
				project_dir: { type: "string", description: "Rojo project root. Defaults to the current directory." },
			},
			required: ["names"],
		},
	},
];

const summary = (i) => `${i.name} (${i.kind}): ${i.description}`;

const HANDLERS = {
	async list_components({ kind } = {}) {
		const index = await loadIndex();
		const items = index.items.filter((i) => (kind ? i.kind === kind : i.kind !== "runtime"));
		return items.map(summary).join("\n");
	},

	async search_components({ query }) {
		const index = await loadIndex();
		const words = String(query).toLowerCase().split(/[\s,_-]+/).filter(Boolean);
		const scored = index.items
			.filter((i) => i.kind !== "runtime")
			.map((i) => {
				const hay = [i.name, i.description, ...(i.tags || [])].join(" ").toLowerCase();
				return { i, score: words.filter((w) => hay.includes(w)).length };
			})
			.filter((x) => x.score > 0)
			.sort((a, b) => b.score - a.score);
		if (scored.length === 0) return `Nothing matches "${query}". Call list_components to see everything.`;
		return scored.map((x) => summary(x.i)).join("\n");
	},

	async get_component({ name }) {
		const index = await loadIndex();
		const matches = index.items.filter((i) => i.name === name);
		if (matches.length === 0) throw new Error(`no component named '${name}'. Call list_components to see them all.`);
		const parts = [];
		for (const item of matches) {
			const lines = [
				`## ${item.name} (${item.kind})`,
				item.description,
				`Usage: ${item.usage || "see the runtime"}`,
				`Requires: ${item.requires.join(", ") || "nothing"}`,
				`Files: ${item.files.map((f) => f.dest).join(", ")}`,
				`License: ${item.license}`,
			];
			if (item.kind === "vfx") {
				lines.push("", "```lua", (await fetchFile(item.files[0].src)).trimEnd(), "```");
			}
			parts.push(lines.join("\n"));
		}
		return parts.join("\n\n");
	},

	async add_component({ names, project_dir }) {
		const r = await install(names, project_dir || process.cwd());
		const out = [];
		if (r.warnings.length) out.push(...r.warnings.map((w) => `Warning: ${w}`), "");
		if (r.added.length) out.push("Added:", ...r.added.map((f) => `  ${f}`));
		if (r.skipped.length) out.push("Already there (left unchanged):", ...r.skipped.map((f) => `  ${f}`));
		if (r.edited.length) out.push("Edited:", ...r.edited.map((f) => `  ${f}`));
		out.push("", "Use it:", 'local Juice = require(game.ReplicatedStorage.Shared.Juice)', ...names.map((n) => `Juice.play("${n}", part)`));
		if (r.uploads.length) {
			out.push(
				"",
				"Tell the user: Roblox only plays uploaded audio. Upload these as Audio at https://create.roblox.com/dashboard/creations, then put each asset ID into its id = \"\" in " + SOUNDS_FILE + ":",
				...r.uploads.map((f) => `  ${f}`),
			);
		}
			return out.join("\n");
	},

	async find_vfx({ query }) {
		const index = await loadEffects();
		const found = searchEffects(index, query);
		if (found.length === 0) return `Nothing matches "${query}". Try a category (${index.categories.join(", ")}) plus an element, e.g. 'explosion fire'.`;
		return found.map((e) => `${e.name}: ${e.description} (from "${e.pack}")`).join("\n") + "\n\nAdd with add_vfx(names).";
	},

	async add_vfx({ names, project_dir }) {
		const root = project_dir || process.cwd();
		const index = await loadEffects();
		const picked = [];
		const refused = [];
		for (const n of names) {
			const e = index.effects.find((x) => x.name === n);
			if (!e) { refused.push(`${n} (no such effect; call find_vfx)`); continue; }
			const now = await storeUpdated(e.asset_id);
			if (now && !sameTime(now, e.pinned_version)) { refused.push(`${n} (its pack changed after the scan)`); continue; }
			picked.push(e);
		}
		if (picked.length === 0) throw new Error(`nothing added: ${refused.join("; ")}`);
		const juice = await install(["juice"], root);
		const lock = await writeVfxLock(root, picked);
		const out = [];
		if (refused.length) out.push(`Not added: ${refused.join("; ")}`);
		if (juice.added.length) out.push(`Added the Juice runtime: ${juice.added.join(", ")}`);
		const init = resolve(root, "src/shared/Juice/init.luau");
		if (existsSync(init) && !(await readFile(init, "utf8")).includes("BaseplateVFX")) {
			out.push("Your Juice runtime predates store effects. Replace src/shared/Juice/init.luau with the latest (add_component never overwrites it).");
		}
		out.push(`Locked in ${lock.path}: ${[...lock.added, ...lock.already].join(", ")}`);
		out.push("", "Run this once with the Roblox Studio MCP's execute_luau (Edit mode):", "```lua", insertSnippet(picked), "```", "", "Then play them:");
		for (const e of picked) out.push(`  Juice.${e.loops ? "attach" : "play"}("${e.name}", part)${e.loops ? "  -- loops; returns stop()" : ""}`);
		return out.join("\n");
	},
};

function send(message) {
	process.stdout.write(JSON.stringify(message) + "\n");
}

async function handle(msg) {
	const { id, method, params } = msg;
	const isRequest = id !== undefined && id !== null;
	try {
		let result;
		switch (method) {
			case "initialize": {
				const asked = params?.protocolVersion;
				result = {
					protocolVersion: SUPPORTED.includes(asked) ? asked : SUPPORTED[0],
					capabilities: { tools: {} },
					serverInfo: SERVER,
					instructions: INSTRUCTIONS,
				};
				break;
			}
			case "ping":
				result = {};
				break;
			case "tools/list":
				result = { tools: TOOLS };
				break;
			case "tools/call": {
				const handler = HANDLERS[params?.name];
				if (!handler) throw Object.assign(new Error(`unknown tool: ${params?.name}`), { code: -32602 });
				try {
					const text = await handler(params.arguments || {});
					result = { content: [{ type: "text", text }] };
				} catch (err) {
					// Tool failures go back to the model as a result it can read, not a protocol error.
					result = { content: [{ type: "text", text: `Error: ${err.message}` }], isError: true };
				}
				break;
			}
			default:
				if (!isRequest) return; // notifications like notifications/initialized need no reply
				throw Object.assign(new Error(`method not found: ${method}`), { code: -32601 });
		}
		if (isRequest) send({ jsonrpc: "2.0", id, result });
	} catch (err) {
		if (isRequest) send({ jsonrpc: "2.0", id, error: { code: err.code || -32603, message: err.message } });
	}
}

export function serve() {
	const rl = createInterface({ input: process.stdin });
	const pending = new Set();
	rl.on("line", (line) => {
		if (!line.trim()) return;
		let msg;
		try {
			msg = JSON.parse(line);
		} catch {
			send({ jsonrpc: "2.0", id: null, error: { code: -32700, message: "parse error" } });
			return;
		}
		const job = handle(msg).finally(() => pending.delete(job));
		pending.add(job);
	});
	// Finish any in-flight replies before exiting when the client closes stdin.
	rl.on("close", () => Promise.allSettled([...pending]).then(() => process.exit(0)));
}
