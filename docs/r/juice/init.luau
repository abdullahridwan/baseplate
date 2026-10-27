--!strict
-- Juice: play Baseplate effects and sounds.
--   Juice.play("coin_pickup", part)   -- effect + sound with the same name, whichever exist
--   Juice.vfx("hit", Vector3.new(0, 5, 0))
--   Juice.sfx("ui_click")             -- no target: plays flat (2D)
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

function Juice.vfx(name: string, target: Target)
	local module = Effects and Effects:FindFirstChild(name)
	if not module or not module:IsA("ModuleScript") then
		warnOnce("vfx:" .. name, "no effect named '" .. name .. "'")
		return
	end
	local host, temporary = resolveHost(target)
	if not host then
		warnOnce("target:" .. name, "Juice.vfx('" .. name .. "') needs a Vector3, BasePart or Model")
		return
	end

	local definition = require(module) :: any
	local attachment = Instance.new("Attachment")
	attachment.Name = "Juice_" .. name
	attachment.Parent = host

	local longest = 0
	for _, emitterDef in definition.emitters do
		local emitter = Instance.new("ParticleEmitter")
		emitter.Enabled = false
		for property, value in emitterDef.properties do
			(emitter :: any)[property] = value
		end
		emitter.Parent = attachment
		emitter:Emit(emitterDef.emit)
		longest = math.max(longest, emitter.Lifetime.Max)
	end

	Debris:AddItem(if temporary then host else attachment, longest + 0.5)
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
