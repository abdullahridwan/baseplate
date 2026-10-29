-- Step 3 (weekly job): scan every downloaded .rbxm with scan.luau, outside Studio.
--   lune run pipeline/vfx/scan_files.luau
-- Writes pipeline/vfx/out/scans.json. Model files are only read, never run.

local fs = require("@lune/fs")
local roblox = require("@lune/roblox")
local serde = require("@lune/serde")
local Scan = require("./scan")

local DIR = "pipeline/vfx/out/rbxm"
local results = {}

for _, file in fs.readDir(DIR) do
	local id = tonumber(string.match(file, "^(%d+)_"))
	if id then
		local ok, roots = pcall(function()
			return roblox.deserializeModel(fs.readFile(DIR .. "/" .. file))
		end)
		if ok then
			local report = Scan.scan(roots, nil)
			report.id = id
			table.insert(results, report)
		else
			table.insert(results, { id = id, error = tostring(roots) })
		end
	end
end

fs.writeFile("pipeline/vfx/out/scans.json", serde.encode("json", results))
print(`scanned {#results} assets`)
