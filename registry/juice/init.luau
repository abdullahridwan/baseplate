--!strict
-- Juice: play Baseplate effects and sounds.
--   Juice.play("coin_pickup", part)   -- effect + sound with the same name, whichever exist
--   Juice.vfx("hit", Vector3.new(0, 5, 0))
--   Juice.sfx("ui_click")             -- no target: plays flat (2D)
--   local stop = Juice.attach("aura_fire", character)  -- looping effects; call stop() to end
--   Juice.music("lobby")              -- crossfades to a looping track; Juice.music(nil) stops
-- Call from the client for best results. Effects live in Effects/, sound IDs in Sounds.luau.

local Debris = game:GetService("Debris")
local SoundService = game:GetService("SoundService")
local TweenService = game:GetService("TweenService")

local Sounds = require(script.Sounds)
local Effects = script:FindFirstChild("Effects") -- created by the first effect you add

export type Target = Vector3 | BasePart | Model

local Juice = {}

local warned: { [string]: boolean } = {}
local function warnOnce(key: string, message: string)
	if not warned[key] then
		warned[key] = true
		warn("[Juice] " .. message)
	end
end

-- Returns a part to host the effect, and whether we created it (and must clean it up).
local function resolveHost(target: Target): (BasePart?, boolean)
	if typeof(target) == "Vector3" then
		local part = Instance.new("Part")
		part.Anchored = true
		part.CanCollide = false
		part.CanQuery = false
		part.CanTouch = false
		part.Transparency = 1
		part.Size = Vector3.new(0.2, 0.2, 0.2)
		part.Position = target
		part.Parent = workspace
		return part, true
	elseif typeof(target) == "Instance" then
		if target:IsA("BasePart") then
			return target, false
		elseif target:IsA("Model") then
			return target.PrimaryPart or target:FindFirstChildWhichIsA("BasePart", true), false
		end
	end
	return nil, false
end

local function loadEffect(name: string): any
	local module = Effects and Effects:FindFirstChild(name)
	if not module or not module:IsA("ModuleScript") then
		warnOnce("vfx:" .. name, "no effect named '" .. name .. "'")
		return nil
	end
	return require(module)
end

-- Builds the effect on the target. Burst emitters fire once; `rate` emitters keep running until stop() is called.
local function spawnEffect(name: string, target: Target): (() -> ())?
	local definition = loadEffect(name)
	if not definition then
		return nil
	end
	local host, temporary = resolveHost(target)
	if not host then
		warnOnce("target:" .. name, "effect '" .. name .. "' needs a Vector3, BasePart or Model")
		return nil
	end

	local attachment = Instance.new("Attachment")
	attachment.Name = "Juice_" .. name
	attachment.Parent = host

	-- `surface` effects (auras) sit on the part itself so particles come from its whole volume
	local emitterParent: Instance = if definition.surface then host else attachment
	local emitters: { ParticleEmitter } = {}
	local longest = 0
	for _, emitterDef in definition.emitters do
		local emitter = Instance.new("ParticleEmitter")
		emitter.Enabled = false
		for property, value in emitterDef.properties do
			(emitter :: any)[property] = value
		end
		emitter.Name = "Juice_" .. name .. "_" .. emitter.Name
		emitter.Parent = emitterParent
		if emitterDef.rate then
			emitter.Rate = emitterDef.rate
			emitter.Enabled = true
		else
			emitter:Emit(emitterDef.emit)
		end
		table.insert(emitters, emitter)
		longest = math.max(longest, emitter.Lifetime.Max)
	end

	local lightDef = definition.light
	if lightDef then
		local light = Instance.new("PointLight")
		light.Color = lightDef.color
		light.Range = lightDef.range
		light.Brightness = lightDef.brightness
		light.Parent = attachment
		if not definition.loop then
			TweenService:Create(light, TweenInfo.new(lightDef.duration), { Brightness = 0 }):Play()
		end
	end

	local stopped = false
	return function()
		if stopped then
			return
		end
		stopped = true
		for _, emitter in emitters do
			emitter.Enabled = false
		end
		-- let the last particles finish, then clean up
		Debris:AddItem(if temporary then host else attachment, longest + 0.5)
		if definition.surface and not temporary then
			for _, emitter in emitters do
				Debris:AddItem(emitter, longest + 0.5)
			end
		end
	end
end

-- One-shot effect. Looping effects (auras, campfires) play for `duration` seconds; use Juice.attach to keep them on.
function Juice.vfx(name: string, target: Target)
	local stop = spawnEffect(name, target)
	if not stop then
		return
	end
	local definition = loadEffect(name)
	if definition.loop then
		task.delay(definition.duration or 2, stop)
	else
		stop()
	end
end

-- Looping effect that stays on until you call the returned function.
--   local stop = Juice.attach("aura_fire", character)
--   stop()
function Juice.attach(name: string, target: Target): () -> ()
	return spawnEffect(name, target) or function() end
end

function Juice.sfx(name: string, target: Target?)
	local definition = Sounds[name]
	if not definition then
		return
	end
	if definition.id == "" then
		warnOnce("sfx:" .. name, "sound '" .. name .. "' has no asset ID yet; upload it and set it in Sounds.luau")
		return
	end

	local sound = Instance.new("Sound")
	sound.Name = "Juice_" .. name
	sound.SoundId = "rbxassetid://" .. definition.id
	sound.Volume = definition.volume
	local variance = definition.pitchVariance or 0
	sound.PlaybackSpeed = 1 + (math.random() * 2 - 1) * variance

	local host, temporary = nil, false
	if target then
		host, temporary = resolveHost(target)
	end
	sound.Parent = host or SoundService
	sound:Play()

	local cleanup: Instance = if temporary and host then host else sound
	sound.Ended:Once(function()
		cleanup:Destroy()
	end)
	Debris:AddItem(cleanup, 10) -- backup in case Ended never fires (asset failed to load)
end

function Juice.play(name: string, target: Target?)
	if target and Effects and Effects:FindFirstChild(name) then
		Juice.vfx(name, target)
	end
	Juice.sfx(name, target)
end

local MUSIC_FADE = TweenInfo.new(1)
local currentMusic: Sound? = nil

function Juice.music(name: string?)
	local previous = currentMusic
	currentMusic = nil
	if previous then
		local fade = TweenService:Create(previous, MUSIC_FADE, { Volume = 0 })
		fade.Completed:Once(function()
			previous:Destroy()
		end)
		fade:Play()
	end
	if not name then
		return
	end

	local definition = Sounds[name]
	if not definition or definition.id == "" then
		warnOnce("music:" .. name, "music '" .. name .. "' has no asset ID yet; upload it and set it in Sounds.luau")
		return
	end
	local sound = Instance.new("Sound")
	sound.Name = "Juice_Music_" .. name
	sound.SoundId = "rbxassetid://" .. definition.id
	sound.Looped = true
	sound.Volume = 0
	sound.Parent = SoundService
	sound:Play()
	TweenService:Create(sound, MUSIC_FADE, { Volume = definition.volume }):Play()
	currentMusic = sound
end

return Juice
