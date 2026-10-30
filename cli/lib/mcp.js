// Baseplate as an MCP server (stdio). Zero dependencies so `npx` starts fast.
//   claude mcp add baseplate -- npx -y baseplate-cli mcp
// Speaks newline-delimited JSON-RPC 2.0 on stdin/stdout. Never write anything else to stdout.

import { createInterface } from "node:readline";
import { RECIPES, SOUNDS_FILE, SAFE_VFX_FILE, install, loadIndex, loadRecipe, fetchFile, loadSafeIndex, searchSafeVfx, writeVfxLock } from "./registry.js";

const SERVER = { name: "baseplate", version: "0.3.0" };
const SUPPORTED = ["2025-06-18", "2025-03-26", "2024-11-05"];

const INSTRUCTIONS = `Baseplate is the agent-native layer for Roblox: recipes that build the generic half of a game, and components (effects and sounds) to drop in.
- To build a game: call get_recipe for "core", then for the game type (obby, tycoon, simulator), and follow every step in order, checking each "Done when".
- To add juice: search_components, then add_component. Sounds must be uploaded to the user's Roblox account; tell them which files to upload and where the IDs go.
- To add scanned VFX: find_vfx, then add_vfx. find_vfx returns only safe packs. Never offer or add a flagged pack. add_vfx writes vfx.json with the pinned asset ID and version. After add_vfx, insert the pack with the Roblox Studio MCP at exactly that pinned version and strip any scripts in the pack before use.`;

const TOOLS = [
	{
		name: "list_recipes",
		description: "List the Baseplate game recipes. A recipe is a step-by-step spec that builds the generic half of a Roblox game. Always build 'core' first.",
		inputSchema: { type: "object", properties: {} },
	},
	{
		name: "get_recipe",
		description: "Get a recipe's full Markdown. Follow its steps in order and check every 'Done when' before moving on.",
		inputSchema: {
			type: "object",
			properties: { name: { type: "string", enum: RECIPES, description: "Recipe name" } },
			required: ["name"],
		},
	},
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
		description: "Find safe, scanned Roblox VFX packs by what they are for, e.g. 'fire explosion'. Returns only safe packs, with a description, pinned asset ID and version, and scan date. Search is by description, tags, and use cases, not just title, so the agent does not need to review thumbnails.",
		inputSchema: {
			type: "object",
			properties: { query: { type: "string" } },
			required: ["query"],
		},
	},
	{
		name: "add_vfx",
		description: "Lock safe VFX packs into vfx.json. Writes the pinned asset ID and version for each pack, and tells the agent to insert that exact version with the Roblox Studio MCP and strip any scripts. Refuses flagged or unknown packs; it never adds them.",
		inputSchema: {
			type: "object",
			properties: {
				names: { type: "array", items: { type: "string" }, minItems: 1, description: "Safe pack names or asset IDs from find_vfx" },
				project_dir: { type: "string", description: "Rojo project root. Defaults to the current directory." },
			},
			required: ["names"],
		},
	},
];

const summary = (i) => `${i.name} (${i.kind}): ${i.description}`;

const HANDLERS = {
	async list_recipes() {
		return [
			"core: project layout, saving player data, safe client/server messaging. Build this first.",
			"obby: a playable starter course with checkpoints that save, hazards and a stage HUD.",
			"tycoon (beta, needs a hand-built map): claimable plots, cash, purchase buttons, droppers and a collector.",
			"simulator (beta, needs a hand-built map): click to collect, backpack capacity, selling, upgrades and rebirths.",
		].join("\n");
	},

	async get_recipe({ name }) {
		return loadRecipe(name);
	},

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
		const safe = await loadSafeIndex();
		const packs = searchSafeVfx(safe, query);
		if (!safe.packs || safe.packs.length === 0) {
			return "The safe VFX index is empty. No scan data has landed in safe-vfx.json yet, so no packs can be recommended. Do not invent an asset ID. See DIRECTION.md for the safe VFX data model and scan job.";
		}
		if (packs.length === 0) return `Nothing safe matches "${query}". Try a broader description, or call find_vfx with a use case like 'explosion', 'win', or 'damage'.`;
		return packs.map((p) => [
			`${p.name}: ${p.description}`,
			`  Asset ID: ${p.asset_id} (pinned version: ${p.pinned_version})`,
			`  Scan date: ${p.scan_date || "unknown"} | Tags: ${(p.tags || []).join(", ")} | Use cases: ${(p.use_cases || []).join(", ")}`,
			`  Insert: check the store page's last-updated time still equals the pinned version (if it changed, don't use it), then insert the asset ID with the Roblox Studio MCP and strip any scripts.`,
		].join("\n")).join("\n\n");
	},

	async add_vfx({ names, project_dir }) {
		const safe = await loadSafeIndex();
		const safePacks = (safe.packs || []).filter((p) => p.status === "safe");
		const picked = [];
		const rejected = [];
		for (const n of names) {
			const match = safePacks.find((p) => p.name === n || String(p.asset_id) === String(n));
			if (match) picked.push(match);
			else rejected.push(n);
		}
		if (picked.length === 0) throw new Error(`no safe packs found for: ${names.join(", ")}. Call find_vfx first. Flagged or unknown packs are never added.`);
		const r = await writeVfxLock(project_dir || process.cwd(), picked);
		const out = [];
		if (rejected.length) out.push(`Not added (not safe or not found): ${rejected.join(", ")}`, "");
		if (r.added.length) out.push(`Locked in ${SAFE_VFX_FILE}:`, ...r.added.map((x) => `  ${x}`));
		if (r.already.length) out.push(`Already locked: ${r.already.join(", ")}`);
		out.push("", "Next steps for the agent:");
		for (const p of picked) {
			out.push(`  - Check pack '${p.name}' still shows last-updated ${p.pinned_version} on its store page, then insert asset ${p.asset_id} with the Roblox Studio MCP.`);
		}
		out.push("  - Strip any scripts in the pack before use.");
		out.push("  - If the last-updated time changed, the pack was edited after the scan: don't use it until it is re-scanned.");
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
