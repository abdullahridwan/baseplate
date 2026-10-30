// Baseplate as an MCP server (stdio). Zero dependencies so `npx` starts fast.
//   claude mcp add baseplate -- npx -y baseplate-cli mcp
// Speaks newline-delimited JSON-RPC 2.0 on stdin/stdout. Never write anything else to stdout.

import { createInterface } from "node:readline";
import { install, loadEffects, searchEffects, storeUpdated, sameTime, insertSnippet, writeVfxLock } from "./registry.js";
import { readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

const SERVER = { name: "baseplate", version: "0.4.0" };
const SUPPORTED = ["2025-06-18", "2025-03-26", "2024-11-05"];

const INSTRUCTIONS = `Baseplate gives you safe Creator Store VFX for Roblox, split into single effects with agent names.
- find_vfx(query), then add_vfx(names). Names are category/element-modifiers, e.g. explosion/fire, hit/electric, aura/dark, celebrate/confetti. Categories: hit, explosion, aura, projectile, trail, pickup, celebrate, ambient, hazard, magic, heal, dash, spawn, death, weather, fire, smoke. If you can guess the name, call add_vfx directly.
- Every effect comes from a scanned, safe pack. add_vfx returns one Luau snippet: run it with the Roblox Studio MCP's execute_luau in Edit mode, then play the effect with Juice.play(name, target), or Juice.attach(name, target) for loops.`;

const TOOLS = [
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

const HANDLERS = {
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
			out.push("Your Juice runtime predates store effects. Replace src/shared/Juice/init.luau with the latest (add_vfx never overwrites it).");
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
