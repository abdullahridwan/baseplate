# Obby: IMPLEMENTATION.md

The generic 50% of an obby: a real, playable starter course with nine stages, checkpoints that save, kill bricks and a lava sea, respawning at your last stage, and a stage HUD. When this file is done, a player can run the whole course from start to finish. Everything that makes it a *specific* obby (theme, custom obstacles, more stages, monetization) is the other 50%, listed at the end.

## Rules for the agent

1. Complete [`core.md`](core.md) first. This file assumes all of it exists.
2. Do the steps in order. Check every **Done when** before moving on.
3. Use the exact paths, names and tags given. Other systems depend on them.
4. Do not build the course by hand in Studio. `CourseBuilder` builds it from code every time the server starts, so it is always the same and always playable.

## How it works

- `CourseBuilder` builds the course when the server starts: a checkpoint pad, then an obstacle section, then the next pad, and so on, ending at a gold FINISH pad. A lava sea sits under everything.
- Every checkpoint is a `BasePart` tagged `Checkpoint` with a number attribute `Stage` (1, 2, 3...). Stage 1 is the start and is also the spawn.
- Touching the checkpoint for `stage + 1` advances you. Touching any other checkpoint does nothing, so players cannot skip ahead.
- Your stage is saved. When you respawn or rejoin, you appear on your checkpoint.
- Every part tagged `KillBrick` kills on touch, including the lava sea.
- All of this runs on the server. The client only shows the HUD.

---

## Step 1: Config

In `src/shared/Config.luau`, add these lines above `return Config`, and replace `Config.DEFAULT_DATA = {}` with the version below.

```lua
Config.DEFAULT_DATA = {
	stage = 1,
}

Config.CHECKPOINT_TAG = "Checkpoint"
Config.HAZARD_TAG = "KillBrick"
Config.SPAWN_HEIGHT = 4 -- studs above the checkpoint

-- The starter course, in order. Each name is one obstacle section between two checkpoints.
Config.COURSE = { "jumps", "stairs", "beam", "zigzag", "lava", "vanish", "climb", "truss" }
Config.COURSE_HEIGHT = 20 -- height of the first checkpoint, in studs
Config.COURSE_GAP = 5 -- gap before each checkpoint pad
```

**Done when**
- `require(game.ReplicatedStorage.Shared.Config).DEFAULT_DATA.stage` returns `1` in the command bar.

---

## Step 2: CheckpointService

Create `src/server/Services/CheckpointService.luau`:

```lua
local CollectionService = game:GetService("CollectionService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage.Shared.Config)
local DataService = require(script.Parent.DataService)

local CheckpointService = {}

local function findCheckpoint(stage: number): BasePart?
	for _, part in CollectionService:GetTagged(Config.CHECKPOINT_TAG) do
		if part:IsA("BasePart") and part:GetAttribute("Stage") == stage then
			return part
		end
	end
	return nil
end

local function spawnAtCheckpoint(player: Player, character: Model)
	local data = DataService.Get(player)
	if not data then
		return
	end
	local checkpoint = findCheckpoint(data.stage) or findCheckpoint(1)
	if not checkpoint then
		warn("[CheckpointService] no checkpoint with Stage = 1 exists")
		return
	end
	character:WaitForChild("HumanoidRootPart")
	task.wait() -- let the default spawn finish first
	character:PivotTo(checkpoint.CFrame + Vector3.new(0, Config.SPAWN_HEIGHT, 0))
end

local function setupLeaderstats(player: Player, data)
	local leaderstats = Instance.new("Folder")
	leaderstats.Name = "leaderstats"

	local stage = Instance.new("IntValue")
	stage.Name = "Stage"
	stage.Value = data.stage
	stage.Parent = leaderstats

	leaderstats.Parent = player
end

local function onCheckpointTouched(checkpoint: BasePart, hit: BasePart)
	local character = hit.Parent
	local player = character and Players:GetPlayerFromCharacter(character)
	if not player then
		return
	end
	local humanoid = character:FindFirstChildOfClass("Humanoid")
	if not humanoid or humanoid.Health <= 0 then
		return
	end
	local data = DataService.Get(player)
	if not data then
		return
	end

	local stage = checkpoint:GetAttribute("Stage")
	if stage ~= data.stage + 1 then
		return -- only the next stage counts
	end

	data.stage = stage
	player.leaderstats.Stage.Value = stage
end

local function bindCheckpoint(part: Instance)
	if not part:IsA("BasePart") then
		return
	end
	part.Touched:Connect(function(hit)
		onCheckpointTouched(part, hit)
	end)
end

function CheckpointService.Start()
	for _, part in CollectionService:GetTagged(Config.CHECKPOINT_TAG) do
		bindCheckpoint(part)
	end
	CollectionService:GetInstanceAddedSignal(Config.CHECKPOINT_TAG):Connect(bindCheckpoint)

	DataService.OnLoaded(function(player, data)
		setupLeaderstats(player, data)
		player.CharacterAdded:Connect(function(character)
			spawnAtCheckpoint(player, character)
		end)
		if player.Character then
			task.spawn(spawnAtCheckpoint, player, player.Character)
		end
	end)
end

return CheckpointService
```

**Done when**
- The file requires without errors.

---

## Step 3: HazardService

Create `src/server/Services/HazardService.luau`:

```lua
local CollectionService = game:GetService("CollectionService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage.Shared.Config)

local HazardService = {}

local function bindHazard(part: Instance)
	if not part:IsA("BasePart") then
		return
	end
	part.Touched:Connect(function(hit)
		local humanoid = hit.Parent and hit.Parent:FindFirstChildOfClass("Humanoid")
		if humanoid and humanoid.Health > 0 then
			humanoid.Health = 0
		end
	end)
end

function HazardService.Start()
	for _, part in CollectionService:GetTagged(Config.HAZARD_TAG) do
		bindHazard(part)
	end
	CollectionService:GetInstanceAddedSignal(Config.HAZARD_TAG):Connect(bindHazard)
end

return HazardService
```

**Done when**
- The file requires without errors.

---

## Step 4: CourseBuilder

This builds the whole starter course from code. Every gap and height below is tuned for the default Roblox character (walk speed 16, jump power 50), so every section is beatable.

Create `src/server/Services/CourseBuilder.luau`:

```lua
local CollectionService = game:GetService("CollectionService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage.Shared.Config)

local CourseBuilder = {}

local PALETTE = {
	Color3.fromRGB(31, 75, 255),
	Color3.fromRGB(255, 170, 0),
	Color3.fromRGB(150, 90, 255),
	Color3.fromRGB(0, 185, 135),
	Color3.fromRGB(255, 85, 150),
}
local PAD_COLOR = Color3.fromRGB(240, 240, 240)
local FINISH_COLOR = Color3.fromRGB(255, 200, 40)
local HAZARD_COLOR = Color3.fromRGB(255, 70, 20)

local vanishing: { BasePart } = {}

local function block(parent: Instance, size: Vector3, position: Vector3, color: Color3, material: Enum.Material?): Part
	local part = Instance.new("Part")
	part.Anchored = true
	part.Size = size
	part.Position = position
	part.Color = color
	part.Material = material or Enum.Material.SmoothPlastic
	part.TopSurface = Enum.SurfaceType.Smooth
	part.BottomSurface = Enum.SurfaceType.Smooth
	part.Parent = parent
	return part
end

local function hazard(parent: Instance, size: Vector3, position: Vector3, material: Enum.Material?): Part
	local part = block(parent, size, position, HAZARD_COLOR, material or Enum.Material.Neon)
	part.Name = "KillBrick"
	CollectionService:AddTag(part, Config.HAZARD_TAG)
	return part
end

-- A platform whose top surface is at height y, running from z forward (toward -Z) for `length` studs.
local function platform(parent: Instance, width: number, length: number, x: number, y: number, z: number, color: Color3): Part
	return block(parent, Vector3.new(width, 1, length), Vector3.new(x, y - 0.5, z - length / 2), color)
end

local function label(part: BasePart, text: string)
	local gui = Instance.new("BillboardGui")
	gui.Size = UDim2.fromOffset(180, 48)
	gui.StudsOffset = Vector3.new(0, 6, 0)
	gui.MaxDistance = 140
	local textLabel = Instance.new("TextLabel")
	textLabel.Size = UDim2.fromScale(1, 1)
	textLabel.BackgroundTransparency = 1
	textLabel.Text = text
	textLabel.Font = Enum.Font.GothamBlack
	textLabel.TextScaled = true
	textLabel.TextColor3 = Color3.new(1, 1, 1)
	textLabel.TextStrokeTransparency = 0.3
	textLabel.Parent = gui
	gui.Parent = part
end

local function checkpoint(parent: Instance, stage: number, z: number, y: number, isFirst: boolean, isLast: boolean): number
	local pad: BasePart
	if isFirst then
		local spawn = Instance.new("SpawnLocation")
		spawn.Neutral = true
		spawn.Duration = 0 -- no force field
		pad = spawn
	else
		pad = Instance.new("Part")
	end
	pad.Name = "Checkpoint" .. stage
	pad.Anchored = true
	pad.Size = Vector3.new(10, 1, 10)
	pad.Position = Vector3.new(0, y - 0.5, z - 5)
	pad.Color = if isLast then FINISH_COLOR else PAD_COLOR
	pad.Material = Enum.Material.SmoothPlastic
	pad.TopSurface = Enum.SurfaceType.Smooth
	pad.BottomSurface = Enum.SurfaceType.Smooth
	pad:SetAttribute("Stage", stage)
	CollectionService:AddTag(pad, Config.CHECKPOINT_TAG)
	pad.Parent = parent
	label(pad, if isLast then "FINISH" else "Stage " .. stage)
	return z - 10
end

-- Each builder starts at (z, y), the far edge of the previous pad, and returns the new (z, y).
local BUILDERS = {}

function BUILDERS.jumps(f: Instance, z: number, y: number, color: Color3)
	for _ = 1, 4 do
		z -= 5
		platform(f, 5, 5, 0, y, z, color)
		z -= 5
	end
	return z, y
end

function BUILDERS.stairs(f: Instance, z: number, y: number, color: Color3)
	for _ = 1, 5 do
		z -= 4
		y += 3
		platform(f, 6, 5, 0, y, z, color)
		z -= 5
	end
	return z, y
end

function BUILDERS.beam(f: Instance, z: number, y: number, color: Color3)
	z -= 4
	platform(f, 1.6, 30, 0, y, z, color)
	return z - 30, y
end

function BUILDERS.zigzag(f: Instance, z: number, y: number, color: Color3)
	for i = 1, 6 do
		z -= 3
		platform(f, 5, 5, if i % 2 == 0 then 4 else -4, y, z, color)
		z -= 5
	end
	return z, y
end

function BUILDERS.lava(f: Instance, z: number, y: number, color: Color3)
	z -= 4
	platform(f, 8, 44, 0, y, z, color)
	for i = 1, 4 do
		hazard(f, Vector3.new(8, 1, 2.5), Vector3.new(0, y + 0.5, z - i * 9))
	end
	return z - 44, y
end

function BUILDERS.vanish(f: Instance, z: number, y: number, color: Color3)
	for _ = 1, 5 do
		z -= 4
		table.insert(vanishing, platform(f, 5, 5, 0, y, z, color))
		z -= 5
	end
	return z, y
end

function BUILDERS.climb(f: Instance, z: number, y: number, color: Color3)
	for i = 1, 5 do
		z -= 4
		y += 2
		platform(f, 4, 4, if i % 2 == 0 then 2 else -2, y, z, color)
		z -= 4
	end
	return z, y
end

function BUILDERS.truss(f: Instance, z: number, y: number, color: Color3)
	z -= 4
	platform(f, 8, 6, 0, y, z, color)
	z -= 6
	local truss = Instance.new("TrussPart")
	truss.Anchored = true
	truss.Size = Vector3.new(2, 16, 2)
	truss.Position = Vector3.new(0, y + 8, z - 1)
	truss.Color = color
	truss.Parent = f
	y += 16
	platform(f, 8, 8, 0, y, z - 2, color)
	return z - 10, y
end

local function startVanishing()
	for i, part in vanishing do
		task.spawn(function()
			task.wait((i - 1) * 0.6)
			while part.Parent do
				part.Transparency = 0
				part.CanCollide = true
				task.wait(2.2)
				part.Transparency = 0.6
				task.wait(0.6)
				part.Transparency = 1
				part.CanCollide = false
				task.wait(1.4)
			end
		end)
	end
end

function CourseBuilder.Start()
	-- The default template's baseplate and spawn would sit in the way of the course.
	local oldBaseplate = workspace:FindFirstChild("Baseplate")
	if oldBaseplate then
		oldBaseplate:Destroy()
	end
	for _, child in workspace:GetChildren() do
		if child:IsA("SpawnLocation") then
			child:Destroy()
		end
	end

	local course = Instance.new("Folder")
	course.Name = "Course"

	local z, y = 0, Config.COURSE_HEIGHT
	for i, kind in Config.COURSE do
		z = checkpoint(course, i, z, y, i == 1, false)
		local section = Instance.new("Folder")
		section.Name = string.format("Section%d_%s", i, kind)
		section.Parent = course
		local builder = BUILDERS[kind]
		assert(builder, "[CourseBuilder] unknown section: " .. tostring(kind))
		z, y = builder(section, z, y, PALETTE[(i - 1) % #PALETTE + 1])
		z -= Config.COURSE_GAP
	end
	local stageCount = #Config.COURSE + 1
	z = checkpoint(course, stageCount, z, y, false, true)

	-- A lava sea under the whole course: falling off means respawning at your checkpoint.
	local length = -z + 80
	hazard(course, Vector3.new(200, 1, length), Vector3.new(0, Config.COURSE_HEIGHT - 14, z / 2), Enum.Material.CrackedLava)

	course:SetAttribute("StageCount", stageCount)
	course.Parent = workspace
	startVanishing()
end

return CourseBuilder
```

**Done when**
- The file requires without errors.

---

## Step 5: Register the services

In `src/server/Main.server.luau`, change `SERVICES` to (the order matters: the course must exist before checkpoints are bound and players spawn):

```lua
local SERVICES = {
	"DataService",
	"CourseBuilder",
	"CheckpointService",
	"HazardService",
}
```

**Done when**
- Playing in Studio shows no errors in Output.
- `Workspace.Course` exists while playing, with `Checkpoint1` to `Checkpoint9`, eight `Section` folders and a `KillBrick` lava sea.

---

## Step 6: Stage HUD

Create `src/client/Controllers/StageHud.luau`:

```lua
local Players = game:GetService("Players")

local StageHud = {}

function StageHud.Start()
	local player = Players.LocalPlayer
	local stageValue = player:WaitForChild("leaderstats"):WaitForChild("Stage") :: IntValue
	local course = workspace:WaitForChild("Course")

	local gui = Instance.new("ScreenGui")
	gui.Name = "StageHud"
	gui.ResetOnSpawn = false

	local label = Instance.new("TextLabel")
	label.AnchorPoint = Vector2.new(0.5, 0)
	label.Position = UDim2.new(0.5, 0, 0, 16)
	label.Size = UDim2.fromOffset(240, 48)
	label.BackgroundColor3 = Color3.fromRGB(17, 17, 17)
	label.BackgroundTransparency = 0.2
	label.TextColor3 = Color3.fromRGB(255, 255, 255)
	label.Font = Enum.Font.GothamBold
	label.TextSize = 24
	label.Parent = gui

	local corner = Instance.new("UICorner")
	corner.CornerRadius = UDim.new(0, 12)
	corner.Parent = label

	local function render()
		local total = course:GetAttribute("StageCount") or 0
		if total > 0 and stageValue.Value >= total then
			label.Text = "Finished!"
		else
			label.Text = string.format("Stage %d / %d", stageValue.Value, total)
		end
	end
	render()
	stageValue.Changed:Connect(render)
	course:GetAttributeChangedSignal("StageCount"):Connect(render)

	gui.Parent = player:WaitForChild("PlayerGui")
end

return StageHud
```

In `src/client/Main.client.luau`, change `CONTROLLERS` to:

```lua
local CONTROLLERS = {
	"StageHud",
}
```

**Done when**
- Playing in Studio shows "Stage 1 / 9" at the top of the screen.

---

## Step 7: Play the course

Nothing to build by hand. Press Play and run the acceptance test.

**Done when** (the obby acceptance test, run all of it)
- [ ] You spawn on the Stage 1 pad, high above a lava sea, and the HUD says "Stage 1 / 9".
- [ ] The course has eight different sections: jumps, stairs, a narrow beam, zigzags, a lava run, disappearing platforms, a climb and a truss tower.
- [ ] Reaching each pad changes the HUD and the leaderboard to that stage.
- [ ] Falling into the lava, or touching a red strip, respawns you on your current checkpoint.
- [ ] Walking back to an earlier pad does not change your stage.
- [ ] The gold FINISH pad shows "Finished!".
- [ ] Stop and play again: you start on the stage you reached.
- [ ] Output shows no errors or `[DataService]` warnings.

---

## The generic 50% is done

Stop here and tell the user the obby works and is playable start to finish. Everything below is **their 50%**: build it only when they ask, and build it on top of these systems rather than replacing them.

**Extension points**
- **Reorder or add sections:** edit `Config.COURSE`. Any name from `BUILDERS` can repeat.
- **New obstacle types:** add a function to `BUILDERS` in `CourseBuilder` that takes `(folder, z, y, color)` and returns the new `(z, y)`, then use its name in `Config.COURSE`.
- **New hazards:** any part tagged `KillBrick`. For moving or timed hazards, add a new service and tag; keep `HazardService` as is.
- **New saved data** (coins, wins, times): add keys to `Config.DEFAULT_DATA`, read and write them through `DataService.Get(player)`.
- **New client UI:** a new module in `src/client/Controllers`, added to `CONTROLLERS`.
- **New remotes:** `Remotes.Create` on the server, `Remotes.Get` on the client, validated and rate limited on the server.

**Ideas the user might ask for**
- A theme (lava, space, candy): colors, materials, lighting, skybox and music
- Moving platforms, spinners, conveyors, wind zones
- A speed-run timer and a global leaderboard (`OrderedDataStore`)
- Skip-stage developer product, VIP gamepass, trails
- Sound, particles and checkpoint effects
- More stages, difficulty tiers, a lobby, or multiple worlds
