# Simulator: IMPLEMENTATION.md

The generic 50% of a clicking simulator: click to collect, a backpack with a capacity, a sell zone, backpack upgrades, rebirths with a multiplier, and a HUD. When this file is done, the full loop (collect, sell, upgrade, rebirth) works and saves. What you collect, the world, pets, eggs and zones are the other 50%.

## Rules for the agent

1. Complete [`core.md`](core.md) first.
2. Do the steps in order. Check every **Done when** before moving on.
3. The client never decides an amount. It only says "I clicked", "upgrade" or "rebirth". The server does all the math.

## The loop

1. Click: gain `points` equal to your multiplier, up to your backpack capacity.
2. Stand in a part tagged `SellZone`: all points become `coins`.
3. Spend coins to upgrade the backpack (more capacity per trip).
4. Rebirth: reset coins and backpack for a permanent multiplier.

---

## Step 1: Config

In `src/shared/Config.luau`, replace `Config.DEFAULT_DATA = {}` and add the rest above `return Config`:

```lua
Config.DEFAULT_DATA = {
	points = 0,
	coins = 0,
	backpackLevel = 1,
	rebirths = 0,
}

Config.SELL_ZONE_TAG = "SellZone"
Config.CLICKS_PER_SECOND = 10

function Config.capacityFor(level: number): number
	return 10 * level * level
end

function Config.upgradeCostFor(level: number): number
	return 25 * level * level
end

function Config.rebirthCostFor(rebirths: number): number
	return 1000 * (rebirths + 1)
end

function Config.multiplierFor(rebirths: number): number
	return 1 + rebirths
end
```

**Done when**
- `require(game.ReplicatedStorage.Shared.Config).capacityFor(2)` returns `40`.

---

## Step 2: SimulatorService

Create `src/server/Services/SimulatorService.luau`:

```lua
local CollectionService = game:GetService("CollectionService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage.Shared.Config)
local Remotes = require(ReplicatedStorage.Shared.Remotes)
local DataService = require(script.Parent.DataService)

local SimulatorService = {}

-- Mirrors data onto the player so the client HUD can read it.
local function sync(player: Player, data)
	player:SetAttribute("Points", data.points)
	player:SetAttribute("Capacity", Config.capacityFor(data.backpackLevel))
	player:SetAttribute("UpgradeCost", Config.upgradeCostFor(data.backpackLevel))
	player:SetAttribute("RebirthCost", Config.rebirthCostFor(data.rebirths))
	player:SetAttribute("Multiplier", Config.multiplierFor(data.rebirths))
	local stats = player:FindFirstChild("leaderstats")
	if stats then
		stats.Coins.Value = data.coins
		stats.Rebirths.Value = data.rebirths
	end
end

local function setupLeaderstats(player: Player)
	local leaderstats = Instance.new("Folder")
	leaderstats.Name = "leaderstats"
	for _, name in { "Coins", "Rebirths" } do
		local value = Instance.new("IntValue")
		value.Name = name
		value.Parent = leaderstats
	end
	leaderstats.Parent = player
end

local function sell(player: Player)
	local data = DataService.Get(player)
	if not data or data.points <= 0 then
		return
	end
	data.coins += data.points
	data.points = 0
	sync(player, data)
end

function SimulatorService.Start()
	local clickRemote = Remotes.Create("Click")
	local upgradeRemote = Remotes.Create("UpgradeBackpack")
	local rebirthRemote = Remotes.Create("Rebirth")

	local canClick = Remotes.RateLimiter(Config.CLICKS_PER_SECOND)
	local canAct = Remotes.RateLimiter(2)

	clickRemote.OnServerEvent:Connect(function(player)
		local data = DataService.Get(player)
		if not data or not canClick(player) then
			return
		end
		local capacity = Config.capacityFor(data.backpackLevel)
		data.points = math.min(data.points + Config.multiplierFor(data.rebirths), capacity)
		sync(player, data)
	end)

	upgradeRemote.OnServerEvent:Connect(function(player)
		local data = DataService.Get(player)
		if not data or not canAct(player) then
			return
		end
		local cost = Config.upgradeCostFor(data.backpackLevel)
		if data.coins < cost then
			return
		end
		data.coins -= cost
		data.backpackLevel += 1
		sync(player, data)
	end)

	rebirthRemote.OnServerEvent:Connect(function(player)
		local data = DataService.Get(player)
		if not data or not canAct(player) then
			return
		end
		if data.coins < Config.rebirthCostFor(data.rebirths) then
			return
		end
		data.rebirths += 1
		data.coins = 0
		data.points = 0
		data.backpackLevel = 1
		sync(player, data)
	end)

	local function bindSellZone(part: Instance)
		if not part:IsA("BasePart") then
			return
		end
		part.Touched:Connect(function(hit)
			local player = hit.Parent and Players:GetPlayerFromCharacter(hit.Parent)
			if player then
				sell(player)
			end
		end)
	end
	for _, part in CollectionService:GetTagged(Config.SELL_ZONE_TAG) do
		bindSellZone(part)
	end
	CollectionService:GetInstanceAddedSignal(Config.SELL_ZONE_TAG):Connect(bindSellZone)

	DataService.OnLoaded(function(player, data)
		setupLeaderstats(player)
		sync(player, data)
	end)
end

return SimulatorService
```

In `src/server/Main.server.luau`, change `SERVICES` to:

```lua
local SERVICES = {
	"DataService",
	"SimulatorService",
}
```

**Done when**
- Playing in Studio shows no errors, and `Coins` and `Rebirths` appear on the leaderboard.

---

## Step 3: Simulator HUD

Create `src/client/Controllers/SimulatorHud.luau`:

```lua
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Remotes = require(ReplicatedStorage.Shared.Remotes)

local SimulatorHud = {}

local function makeButton(parent: Instance, text: string, order: number): TextButton
	local button = Instance.new("TextButton")
	button.LayoutOrder = order
	button.Size = UDim2.fromOffset(220, 56)
	button.BackgroundColor3 = Color3.fromRGB(31, 75, 255)
	button.TextColor3 = Color3.fromRGB(255, 255, 255)
	button.Font = Enum.Font.GothamBold
	button.TextSize = 20
	button.Text = text
	button.Parent = parent
	local corner = Instance.new("UICorner")
	corner.CornerRadius = UDim.new(0, 12)
	corner.Parent = button
	return button
end

function SimulatorHud.Start()
	local player = Players.LocalPlayer
	local clickRemote = Remotes.Get("Click")
	local upgradeRemote = Remotes.Get("UpgradeBackpack")
	local rebirthRemote = Remotes.Get("Rebirth")

	local gui = Instance.new("ScreenGui")
	gui.Name = "SimulatorHud"
	gui.ResetOnSpawn = false

	local column = Instance.new("Frame")
	column.AnchorPoint = Vector2.new(0, 1)
	column.Position = UDim2.new(0, 16, 1, -16)
	column.Size = UDim2.fromOffset(220, 260)
	column.BackgroundTransparency = 1
	column.Parent = gui

	local layout = Instance.new("UIListLayout")
	layout.Padding = UDim.new(0, 8)
	layout.SortOrder = Enum.SortOrder.LayoutOrder
	layout.VerticalAlignment = Enum.VerticalAlignment.Bottom
	layout.Parent = column

	local backpack = Instance.new("TextLabel")
	backpack.LayoutOrder = 1
	backpack.Size = UDim2.fromOffset(220, 40)
	backpack.BackgroundColor3 = Color3.fromRGB(17, 17, 17)
	backpack.BackgroundTransparency = 0.2
	backpack.TextColor3 = Color3.fromRGB(255, 255, 255)
	backpack.Font = Enum.Font.GothamBold
	backpack.TextSize = 18
	backpack.Parent = column

	local clickButton = makeButton(column, "Click", 2)
	local upgradeButton = makeButton(column, "", 3)
	local rebirthButton = makeButton(column, "", 4)

	local function render()
		local points = player:GetAttribute("Points") or 0
		local capacity = player:GetAttribute("Capacity") or 0
		backpack.Text = string.format("Backpack %d / %d", points, capacity)
		upgradeButton.Text = "Upgrade: " .. (player:GetAttribute("UpgradeCost") or 0) .. " coins"
		rebirthButton.Text = "Rebirth: " .. (player:GetAttribute("RebirthCost") or 0) .. " coins"
	end
	render()
	for _, name in { "Points", "Capacity", "UpgradeCost", "RebirthCost" } do
		player:GetAttributeChangedSignal(name):Connect(render)
	end

	clickButton.Activated:Connect(function()
		clickRemote:FireServer()
	end)
	upgradeButton.Activated:Connect(function()
		upgradeRemote:FireServer()
	end)
	rebirthButton.Activated:Connect(function()
		rebirthRemote:FireServer()
	end)

	gui.Parent = player:WaitForChild("PlayerGui")
end

return SimulatorHud
```

In `src/client/Main.client.luau`, change `CONTROLLERS` to:

```lua
local CONTROLLERS = {
	"SimulatorHud",
}
```

**Done when**
- The HUD shows "Backpack 0 / 10" and three buttons.

---

## Step 4: Test world

In `Workspace`, create an anchored Part `SellPad` (10 x 1 x 10), tag it `SellZone`, and place it 20 studs from the spawn.

**Done when** (the simulator acceptance test)
- [ ] Clicking raises the backpack by 1 per click and stops at 10.
- [ ] Clicking faster than 10 times per second does not earn more.
- [ ] Standing on `SellPad` empties the backpack and adds the points to `Coins`.
- [ ] With 25 coins, Upgrade raises capacity to 40 and costs 25.
- [ ] With 1000 coins, Rebirth resets coins and backpack, and clicks now give 2.
- [ ] Stop and play again: coins, backpack level and rebirths are kept.
- [ ] Output shows no errors or `[DataService]` warnings.

---

## The generic 50% is done

Stop here and tell the user the foundation is complete. Everything below is **their 50%**.

**Extension points**
- **Economy tuning:** the four functions in `Config`. Change curves there, nowhere else.
- **New multipliers** (pets, gamepasses, boosts): multiply inside the click handler in `SimulatorService`, reading from saved data.
- **New actions:** `Remotes.Create` on the server, `Remotes.Get` on the client, rate limited, server-side checks only.
- **New zones:** tag parts and bind them like `SellZone`.

**Ideas the user might ask for**
- What you collect (strength, snow, candy) and a tool that does the clicking
- Pets and eggs with rarity, equipping and multipliers
- Zones and worlds gated by rebirths
- Quests, daily rewards, codes, and boosts
- Gamepasses: auto-click, 2x coins, bigger backpack
