// Shared by the CLI and the MCP server: read the Baseplate registry and install items into a project.
// BASEPLATE_REGISTRY points at another registry: a URL or a local folder containing index.json.
// BASEPLATE_SITE points at another site root : a URL or a local folder.

import { existsSync } from "node:fs";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";

export const REGISTRY = process.env.BASEPLATE_REGISTRY || "https://baseplatehq.github.io/baseplate/r/";
export const SITE = process.env.BASEPLATE_SITE || "https://baseplatehq.github.io/baseplate/";
export const SOUNDS_FILE = "src/shared/Juice/Sounds.luau";
export const SAFE_VFX_FILE = "vfx.json";

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

export async function loadSafeIndex() {
  return JSON.parse(await fetchFile("safe-vfx.json"));
}

let effectsCache;
export async function loadEffects() {
  effectsCache ??= JSON.parse(await fetchFile("vfx-effects.json"));
  return effectsCache;
}

// Common words agents use, mapped to the words effect names are built from.
const SYNONYMS = {
  boom: "explosion", blast: "explosion", explode: "explosion", impact: "hit", damage: "hit", punch: "hit", slash: "hit",
  coin: "pickup", collect: "pickup", reward: "pickup", win: "celebrate", victory: "celebrate", finish: "celebrate",
  party: "celebrate", lightning: "electric", thunder: "electric", shock: "electric", frost: "ice", freeze: "ice",
  flame: "fire", burn: "fire", shadow: "dark", void: "dark", lava: "hazard", poison: "hazard", heal: "heal",
  powerup: "aura", charge: "aura", teleport: "spawn", die: "death", kill: "death", fog: "smoke", mist: "smoke",
  loop: "loop", looping: "loop", bigger: "big", large: "big", tiny: "small",
};

const words = (s) => String(s || "").toLowerCase().split(/[^a-z0-9]+/).filter(Boolean)
  .map((w) => (w.length > 3 && w.endsWith("s") ? w.slice(0, -1) : w));

// Whole-word search over agent names first, then descriptions. Best-loved pack wins ties.
export function searchEffects(index, query, limit = 5) {
  const q = words(query).flatMap((w) => (SYNONYMS[w] && SYNONYMS[w] !== w ? [w, SYNONYMS[w]] : [w]));
  if (q.length === 0) return [];
  const exact = index.effects.find((e) => e.name === String(query).trim().toLowerCase());
  if (exact) return [exact];
  return index.effects
    .map((e) => {
      const nameWords = new Set(words(e.name));
      const other = new Set([...words(e.description), ...e.layers, ...e.colors, e.kind, e.size, ...words(e.pack)]);
      let score = 0;
      for (const w of new Set(q)) score += nameWords.has(w) ? 3 : other.has(w) ? 1 : 0;
      return { e, score };
    })
    .filter((x) => x.score > 0)
    .sort((a, b) => b.score - a.score || a.e.name.length - b.e.name.length || b.e.votes - a.e.votes)
    .slice(0, limit)
    .map((x) => x.e);
}

// The store's last-updated time for an asset, or null if the store can't be reached.
export async function storeUpdated(assetId) {
  try {
    const res = await fetch(`https://apis.roblox.com/toolbox-service/v1/items/details?assetIds=${assetId}`);
    if (!res.ok) return null;
    const body = await res.json();
    return body?.data?.[0]?.asset?.updatedUtc ?? null;
  } catch {
    return null;
  }
}

// Same instant, written the way either side writes it.
export const sameTime = (a, b) => a && b && Date.parse(a) === Date.parse(b);

// One Luau snippet for the Studio MCP's execute_luau: reads each pinned pack without running it,
// keeps only the chosen effect, removes any scripts, and stores it in ReplicatedStorage.BaseplateVFX
// under its agent name, ready for Juice.play(name, target).
export function insertSnippet(effects) {
  const items = effects.map((e) => {
    const fire = e.fire.filter((f, i, all) => all.findIndex((g) => g.emitter === f.emitter) === i).map((f) => `{ emitter = ${JSON.stringify(f.emitter)}, emit = ${f.emit}, delay = ${f.delay} }`).join(", ");
    return `\t{ name = ${JSON.stringify(e.name)}, id = ${e.asset_id}, path = ${JSON.stringify(e.path)}, loop = ${e.loops}, fire = { ${fire} } },`;
  });
  return `local items = {
${items.join("\n")}
}
local store = game:GetService("ReplicatedStorage"):FindFirstChild("BaseplateVFX") or Instance.new("Folder")
store.Name = "BaseplateVFX"
store.Parent = game:GetService("ReplicatedStorage")
-- Follows "Pack/Effects/Fire#2": "#k" is the k-th child with that name, "%2F" a "/" in a name.
local function find(roots, path)
	local node
	for i, seg in string.split(path, "/") do
		local name, k = string.match(seg, "^(.-)#(%d+)$")
		name, k = string.gsub(name or seg, "%%2F", "/"), tonumber(k) or 1
		local n, found = 0, nil
		for _, c in (if i == 1 then roots else node:GetChildren()) do
			if c.Name == name then
				n += 1
				if n == k then found = c break end
			end
		end
		node = found
		if not node then return nil end
	end
	return node
end
local done = {}
for _, it in items do
	local roots = game:GetObjects("rbxassetid://" .. it.id)
	local node = find(roots, it.path)
	if node then
		local fx = node:Clone()
		for _, d in fx:GetDescendants() do
			if d:IsA("LuaSourceContainer") then d:Destroy() end
		end
		if fx:IsA("BasePart") then
			fx.Anchored, fx.CanCollide, fx.CanQuery, fx.CanTouch, fx.Transparency = true, false, false, false, 1
		end
		for _, f in it.fire do
			for _, e in fx:GetDescendants() do
				if e:IsA("ParticleEmitter") and e.Name == f.emitter then
					e.Enabled = false
					e:SetAttribute("EmitCount", f.emit)
					e:SetAttribute("EmitDelay", f.delay)
				end
			end
		end
		fx:SetAttribute("Loop", it.loop)
		fx:SetAttribute("BaseplateAsset", it.id)
		local old = store:FindFirstChild(it.name)
		if old then old:Destroy() end
		fx.Name = it.name
		fx.Parent = store
		table.insert(done, it.name)
	else
		table.insert(done, it.name .. " (NOT FOUND)")
	end
	for _, r in roots do r:Destroy() end
end
return table.concat(done, ", ")`;
}

export async function writeVfxLock(root, effects) {
  const path = resolve(root, SAFE_VFX_FILE);
  let existing = { version: 2, effects: [] };
  if (existsSync(path)) {
    try { existing = JSON.parse(await readFile(path, "utf8")); } catch { existing = { version: 2, effects: [] }; }
  }
  if (!Array.isArray(existing.effects)) existing.effects = [];
  const added = [];
  const already = [];
  for (const e of effects) {
    if (existing.effects.some((x) => x.name === e.name)) { already.push(e.name); continue; }
    existing.effects.push({
      name: e.name,
      asset_id: e.asset_id,
      path: e.path,
      pinned_version: e.pinned_version,
      pack: e.pack,
      source: "baseplate vfx-effects",
    });
    added.push(e.name);
  }
  existing.effects.sort((a, b) => a.name.localeCompare(b.name));
  existing.version = 2;
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, JSON.stringify(existing, null, 2) + "\n");
  return { added, already, path: SAFE_VFX_FILE };
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
