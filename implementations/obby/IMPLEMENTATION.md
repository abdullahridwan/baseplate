# Obby: IMPLEMENTATION.md

The generic 50% of an obby: stages, checkpoints that save, kill bricks, respawning at your last stage, and a stage HUD. When this file is done, the game is playable end to end. Everything that makes it a *specific* obby (theme, level design, obstacles, monetization) is the other 50%, listed at the end.

## Rules for the agent

1. Complete [`core/IMPLEMENTATION.md`](../core/IMPLEMENTATION.md) first. This file assumes all of it exists.
2. Do the steps in order. Check every **Done when** before moving on.
3. Use the exact paths, names and tags given. Other systems depend on them.
4. Do not build level geometry beyond the test stages in Step 6. Level design is the user's 50%.

## How it works

- Every checkpoint is a `BasePart` tagged `Checkpoint` with a number attribute `Stage` (1, 2, 3...). Stage 1 is the start.
- Touching the checkpoint for `stage + 1` advances you. Touching any other checkpoint does nothing, so players cannot skip ahead.
- Your stage is saved. When you respawn or rejoin, you appear on your checkpoint.
- Every part tagged `KillBrick` kills on touch.
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

## Step 4: Register the services

In `src/server/Main.server.luau`, change `SERVICES` to:

```lua
local SERVICES = {
	"DataService",
	"CheckpointService",
	"HazardService",
}
```

**Done when**
- Playing in Studio shows no errors in Output.

---

## Step 5: Stage HUD

Create `src/client/Controllers/StageHud.luau`:

```lua
local Players = game:GetService("Players")

local StageHud = {}

function StageHud.Start()
	local player = Players.LocalPlayer
	local stageValue = player:WaitForChild("leaderstats"):WaitForChild("Stage") :: IntValue

	local gui = Instance.new("ScreenGui")
	gui.Name = "StageHud"
	gui.ResetOnSpawn = false

	local label = Instance.new("TextLabel")
	label.AnchorPoint = Vector2.new(0.5, 0)
	label.Position = UDim2.new(0.5, 0, 0, 16)
	label.Size = UDim2.fromOffset(220, 48)
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
		label.Text = "Stage " .. stageValue.Value
	end
	render()
	stageValue.Changed:Connect(render)

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
- Playing in Studio shows "Stage 1" at the top of the screen.

---

## Step 6: Test stages

Build the smallest course that proves every system works. In Studio, in `Workspace`, create a Folder named `Stages`, then inside it:

| Part | Size | Position | Tag | Attribute |
|---|---|---|---|---|
| `Checkpoint1` | 8, 1, 8 | 0, 0, 0 | `Checkpoint` | `Stage` = 1 |
| `Checkpoint2` | 8, 1, 8 | 0, 0, -20 | `Checkpoint` | `Stage` = 2 |
| `Checkpoint3` | 8, 1, 8 | 0, 0, -40 | `Checkpoint` | `Stage` = 3 |
| `Lava` | 8, 1, 12 | 0, -6, -10 | `KillBrick` | none |

Anchor every part. Add plain anchored platforms between the checkpoints so they can be reached by walking.

**Done when** (the obby acceptance test, run all of it)
- [ ] You spawn on `Checkpoint1` and the HUD says "Stage 1".
- [ ] Touching `Checkpoint2` changes the HUD and the leaderboard to 2.
- [ ] Walking back to `Checkpoint1` does not change your stage.
- [ ] Touching `Checkpoint3` before `Checkpoint2` does nothing.
- [ ] Touching `Lava` kills you, and you respawn on your current checkpoint.
- [ ] Stop and play again: you start on the stage you reached.
- [ ] Output shows no errors or `[DataService]` warnings.

---

## The generic 50% is done

Stop here and tell the user the foundation is complete. Everything below is **their 50%**: build it only when they ask, and build it on top of these systems rather than replacing them.

**Extension points**
- **New stages:** any part tagged `Checkpoint` with the next `Stage` number. No code changes.
- **New hazards:** any part tagged `KillBrick`. For moving or timed hazards, add a new service and tag; keep `HazardService` as is.
- **New saved data** (coins, wins, times): add keys to `Config.DEFAULT_DATA`, read and write them through `DataService.Get(player)`.
- **New client UI:** a new module in `src/client/Controllers`, added to `CONTROLLERS`.
- **New remotes:** `Remotes.Create` on the server, `Remotes.Get` on the client, validated and rate limited on the server.

**Ideas the user might ask for**
- A theme (lava, space, candy) and real level design
- Moving platforms, spinners, disappearing bricks, conveyors
- A speed-run timer and a global leaderboard (`OrderedDataStore`)
- Skip-stage developer product, VIP gamepass, trails
- Sound, music, particles and checkpoint effects
- Difficulty sections, a lobby, or multiple worlds
