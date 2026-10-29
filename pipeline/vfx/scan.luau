--!nocheck
-- Step 3: scan one VFX asset's instance tree. Pure Luau with no services, so the
-- same file runs in Lune (weekly job, reading downloaded .rbxm files) and in
-- Roblox Studio (through the Studio MCP, using game:GetObjects).
-- Every rule here is defined in RULES.md. Change both together.

local Scan = {}

-- Classes a VFX asset is made of. Anything else is noted as "other".
local EFFECTS = { ParticleEmitter = true, Beam = true, Trail = true, Fire = true, Smoke = true, Sparkles = true }
local LIGHTS = { PointLight = true, SpotLight = true, SurfaceLight = true }
local SCRIPTS = { Script = true, LocalScript = true, ModuleScript = true }
local REMOTES = { RemoteEvent = true, RemoteFunction = true, UnreliableRemoteEvent = true, BindableEvent = true, BindableFunction = true }
local GUIS = { ScreenGui = true, SurfaceGui = true, BillboardGui = true }
-- Scripts never belong inside these. Hiding one there is a disguise (rule M3).
local LEAVES = {
	ParticleEmitter = true, Beam = true, Trail = true, Attachment = true, Decal = true, Texture = true,
	PointLight = true, SpotLight = true, SurfaceLight = true, Sound = true, SpecialMesh = true,
	Fire = true, Smoke = true, Sparkles = true,
}

-- M1 and M2: code patterns. Each is { rule, label, lua pattern }.
local CODE_RULES = {
	{ "M1", "require() by asset ID", "require%s*%(%s*[%d%(]" },
	{ "M1", "require() of a computed value", "require%s*%(%s*tonumber" },
	{ "M1", "loadstring", "loadstring" },
	{ "M1", "getfenv/setfenv", "[gs]etfenv" },
	{ "M1", "string.reverse obfuscation", "string%.reverse" },
	{ "M1", "byte-escaped strings", "\\%d%d?%d?\\%d%d?%d?\\%d%d?%d?\\%d%d?%d?" },
	{ "M2", "InsertService", "InsertService" },
	{ "M2", "LoadAsset", "LoadAsset" },
	{ "M2", "GetObjects", "GetObjects" },
	{ "M2", "HttpService", "HttpService" },
	{ "M2", "HttpGet/PostAsync/RequestAsync", "Http[GP]" },
	{ "M2", "RequestAsync", "RequestAsync" },
	{ "M2", "MarketplaceService prompt", "Prompt%w*Purchase" },
	{ "M2", "TeleportService", "TeleportService" },
	{ "M2", "touches CoreGui", "CoreGui" },
}

-- M4: words a fake "developer tool" window uses to get you to paste a command.
local BAIT = { "troubleshoot", "command", "paste", "console", "verify", "copy", "fix", "execute", "plugin", "license" }

local function hex(c)
	return string.format("#%02X%02X%02X", math.floor(c.R * 255 + 0.5), math.floor(c.G * 255 + 0.5), math.floor(c.B * 255 + 0.5))
end

local function path(inst, root)
	local parts = {}
	while inst and inst ~= root do
		table.insert(parts, 1, inst.Name)
		inst = inst.Parent
	end
	return table.concat(parts, ".")
end

local function longestLine(src)
	local n = 0
	for line in string.gmatch(src, "[^\n]+") do
		if #line > n then n = #line end
	end
	return n
end

local function emitterInfo(e)
	local info = { name = e.Name, class = e.ClassName }
	local ok = pcall(function()
		if e.ClassName == "ParticleEmitter" then
			info.texture = e.Texture
			info.color = hex(e.Color.Keypoints[1].Value)
			info.rate = e.Rate
			info.lifetime = { e.Lifetime.Min, e.Lifetime.Max }
			info.enabled = e.Enabled
		elseif e.ClassName == "Beam" or e.ClassName == "Trail" then
			info.texture = e.Texture
			info.color = hex(e.Color.Keypoints[1].Value)
		end
	end)
	if not ok then info.unreadable = true end
	return info
end

-- root: the asset's top-level instance(s) as an array. storeDescription: the listing text.
function Scan.scan(roots, storeDescription)
	local report = {
		counts = { effects = 0, emitters = 0, parts = 0, lights = 0, sounds = 0, scripts = 0, remotes = 0, guis = 0, total = 0 },
		effects = {},
		scripts = {},
		findings = {},
	}
	local function find(rule, label, where)
		table.insert(report.findings, { rule = rule, what = label, where = where })
	end

	local all = {}
	for _, r in ipairs(roots) do
		table.insert(all, r)
		for _, d in ipairs(r:GetDescendants()) do
			table.insert(all, d)
		end
	end

	for _, inst in ipairs(all) do
		local class = inst.ClassName
		local c = report.counts
		c.total += 1
		local where = path(inst, nil)

		if EFFECTS[class] then
			c.effects += 1
			if class == "ParticleEmitter" then c.emitters += 1 end
			if #report.effects < 40 then table.insert(report.effects, emitterInfo(inst)) end
		elseif LIGHTS[class] then
			c.lights += 1
		elseif class == "Sound" then
			c.sounds += 1
		elseif inst:IsA("BasePart") then
			c.parts += 1
		elseif REMOTES[class] then
			c.remotes += 1
		elseif GUIS[class] then
			c.guis += 1
		end

		if SCRIPTS[class] then
			c.scripts += 1
			local ok, src = pcall(function() return inst.Source end)
			src = ok and src or ""
			table.insert(report.scripts, { path = where, class = class, bytes = #src })
			if inst.Parent and LEAVES[inst.Parent.ClassName] then
				find("M3", class .. " hidden inside a " .. inst.Parent.ClassName, where)
			end
			for _, rule in ipairs(CODE_RULES) do
				if string.find(src, rule[3]) then find(rule[1], rule[2], where) end
			end
			if longestLine(src) > 1500 then find("M1", "a single line over 1500 characters", where) end
			if string.find(src, "[%w+/=]" .. string.rep("[%w+/=]", 400)) then find("M1", "large encoded blob", where) end
		end

		if class == "TextBox" or class == "TextButton" or class == "TextLabel" then
			local ok, text = pcall(function() return string.lower(inst.Text .. " " .. inst.Name) end)
			if ok then
				for _, word in ipairs(BAIT) do
					if string.find(text, word, 1, true) then
						find("M4", "fake tool window text: '" .. word .. "'", where)
						break
					end
				end
			end
		end
	end

	local c = report.counts
	if c.remotes > 0 and c.scripts > 0 then find("M6", "scripts plus remotes in a VFX asset", "") end
	if c.scripts > 0 and storeDescription and string.find(string.lower(storeDescription), "no script", 1, true) then
		find("M5", "listing says 'no scripts' but it has " .. c.scripts, "")
	end
	return report
end

return Scan
