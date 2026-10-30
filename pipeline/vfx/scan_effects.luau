--!nocheck
-- Step 6: split a safe pack into usable effects and read each one's settings, so
-- find_vfx can return one effect instead of a whole pack. Pure Luau like scan.luau:
-- runs in Lune on .rbxm files or in Studio through game:GetObjects. Nothing is run.
--
-- An effect is the instance that holds a group of ParticleEmitters: usually an
-- Attachment, or a Part when several of its Attachments together make one effect.

local ScanEffects = {}

local MAX_EFFECTS = 80 -- per pack
local MAX_EMITTERS = 12 -- per effect

local function hex(c)
	return string.format("#%02X%02X%02X", math.floor(c.R * 255 + 0.5), math.floor(c.G * 255 + 0.5), math.floor(c.B * 255 + 0.5))
end

-- "Pack/Effects/Fire#2": names joined by "/", with "#k" on any name that has same-named
-- siblings (the k-th of them), so the path always leads to exactly one instance. A "/"
-- inside a name is written as "%2F".
local function segment(inst, siblings)
	local k, n = 0, 0
	for _, c in siblings do
		if c.Name == inst.Name then
			n += 1
			if c == inst then
				k = n
			end
		end
	end
	local name = string.gsub(inst.Name, "/", "%%2F")
	return if n > 1 then name .. "#" .. k else name
end

local function path(inst, roots, rootList)
	local parts = {}
	while inst and not roots[inst] do
		table.insert(parts, 1, segment(inst, inst.Parent:GetChildren()))
		inst = inst.Parent
	end
	if inst then
		table.insert(parts, 1, segment(inst, rootList))
	end
	return table.concat(parts, "/")
end

local function seq(s)
	local out = {}
	for _, k in s.Keypoints do
		table.insert(out, { math.floor(k.Time * 100 + 0.5) / 100, math.floor(k.Value * 100 + 0.5) / 100 })
	end
	return out
end

local function emitter(e)
	local info = { name = e.Name }
	pcall(function()
		local colors = {}
		for _, k in e.Color.Keypoints do
			table.insert(colors, hex(k.Value))
		end
		info.colors = colors
		info.texture = string.match(e.Texture, "%d+")
		info.rate = e.Rate
		info.enabled = e.Enabled
		info.life = { e.Lifetime.Min, e.Lifetime.Max }
		info.speed = { e.Speed.Min, e.Speed.Max }
		info.size = seq(e.Size)
		info.transp = seq(e.Transparency)
		info.le = e.LightEmission
		info.li = e.LightInfluence
		info.orient = e.Orientation.Name
		info.flip = e.FlipbookLayout.Name
		info.drag = e.Drag
		info.accel_y = e.Acceleration.Y
		info.locked = e.LockedToPart
		info.z = e.ZOffset
		info.emit = e:GetAttribute("EmitCount")
		info.delay = e:GetAttribute("EmitDelay")
		info.duration = e:GetAttribute("EmitDuration")
	end)
	return info
end

-- roots: the pack's top-level instances. Returns { effects = {...}, total = n }.
function ScanEffects.scan(roots)
	local rootSet = {}
	for _, r in roots do
		rootSet[r] = true
	end

	-- Group emitters by the instance that holds them.
	local holders, order = {}, {}
	local function add(holder, e)
		if not holders[holder] then
			holders[holder] = {}
			table.insert(order, holder)
		end
		table.insert(holders[holder], e)
	end
	for _, r in roots do
		local all = r:GetDescendants()
		table.insert(all, 1, r)
		for _, d in all do
			if d.ClassName == "ParticleEmitter" and d.Parent then
				local holder = d.Parent
				-- Several emitting Attachments on one Part are one effect: use the Part.
				if holder.ClassName == "Attachment" and holder.Parent and holder.Parent:IsA("BasePart") then
					local siblings = 0
					for _, a in holder.Parent:GetChildren() do
						if a.ClassName == "Attachment" and a:FindFirstChildOfClass("ParticleEmitter") then
							siblings += 1
						end
					end
					if siblings > 1 then
						holder = holder.Parent
					end
				end
				add(holder, d)
			end
		end
	end

	local effects = {}
	for _, holder in order do
		if #effects >= MAX_EFFECTS then
			break
		end
		local list = {}
		for i, e in holders[holder] do
			if i > MAX_EMITTERS then
				break
			end
			table.insert(list, emitter(e))
		end
		table.insert(effects, {
			path = path(holder, rootSet, roots),
			name = holder.Name,
			holder = holder.ClassName,
			parent = holder.Parent and holder.Parent.Name or "",
			count = #holders[holder],
			emitters = list,
		})
	end
	return { effects = effects, total = #order }
end

return ScanEffects
