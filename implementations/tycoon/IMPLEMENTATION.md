# Tycoon: IMPLEMENTATION.md

The generic 50% of a tycoon: claimable plots, cash, purchase buttons that unlock items, droppers, a collector, and progress that saves. When this file is done, a player can claim a plot, earn, buy, leave, rejoin and find their tycoon rebuilt. The theme, the item list, the economy curve and everything else that makes it *their* tycoon is the other 50%.

## Rules for the agent

1. Complete [`core/IMPLEMENTATION.md`](../core/IMPLEMENTATION.md) first.
2. Do the steps in order. Check every **Done when** before moving on.
3. Use the exact paths, names and attributes given.
4. All cash changes happen on the server, inside `CashService`. Nothing else touches `data.cash`.

## How a plot is built

Every plot is a Model inside `Workspace.Tycoons`, with a unique name (`Plot1`, `Plot2`...), containing:

| Child | Type | Purpose |
|---|---|---|
| `ClaimPad` | Part | Touch to claim the plot |
| `Collector` | Part | Drops that touch it pay the owner |
| `Buttons` | Folder | Purchase buttons (Parts) |
| `Items` | Folder | Everything a button can unlock (Models) |

Each **button** is a Part with attributes:
- `Price` (number): cost in cash
- `Unlocks` (string): name of a Model in `Items`
- `Requires` (string, optional): name of an item that must be owned first

Each **dropper** is an item Model that contains a Part named `Drop`, with attributes:
- `DropValue` (number): cash per drop
- `DropInterval` (number): seconds between drops

---

## Step 1: Config

In `src/shared/Config.luau`, replace `Config.DEFAULT_DATA = {}` and add the rest above `return Config`:

```lua
Config.DEFAULT_DATA = {
	cash = 0,
	purchased = {}, -- [itemName] = true
}

Config.TYCOONS_FOLDER = "Tycoons"
Config.DROP_LIFETIME = 20 -- seconds before an uncollected drop is removed
```

**Done when**
- The config requires without errors.

---

## Step 2: CashService

Create `src/server/Services/CashService.luau`:

```lua
local DataService = require(script.Parent.DataService)

local CashService = {}

local function display(player: Player, amount: number)
	local stats = player:FindFirstChild("leaderstats")
	if stats then
		stats.Cash.Value = amount
	end
end

function CashService.Get(player: Player): number
	local data = DataService.Get(player)
	return data and data.cash or 0
end

function CashService.Add(player: Player, amount: number)
	local data = DataService.Get(player)
	if not data or amount <= 0 then
		return
	end
	data.cash += amount
	display(player, data.cash)
end

-- Returns true and deducts if the player can afford it.
function CashService.TrySpend(player: Player, amount: number): boolean
	local data = DataService.Get(player)
	if not data or amount < 0 or data.cash < amount then
		return false
	end
	data.cash -= amount
	display(player, data.cash)
	return true
end

function CashService.Start()
	DataService.OnLoaded(function(player, data)
		local leaderstats = Instance.new("Folder")
		leaderstats.Name = "leaderstats"
		local cash = Instance.new("IntValue")
		cash.Name = "Cash"
		cash.Value = data.cash
		cash.Parent = leaderstats
		leaderstats.Parent = player
	end)
end

return CashService
```

**Done when**
- The file requires without errors.

---

## Step 3: TycoonService

Create `src/server/Services/TycoonService.luau`:

```lua
local Debris = game:GetService("Debris")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage.Shared.Config)
local DataService = require(script.Parent.DataService)
local CashService = require(script.Parent.CashService)

local TycoonService = {}

local items: { [Model]: { [string]: Instance } } = {} -- every unlockable, by plot
local buttons: { [Model]: { BasePart } } = {} -- every button, by plot
local owners: { [Model]: Player } = {}
local plotOf: { [Player]: Model } = {}
local activeDroppers: { [Instance]: {} } = {}

local function isOwned(player: Player, itemName: string): boolean
	local data = DataService.Get(player)
	return data ~= nil and data.purchased[itemName] == true
end

local function refreshButtons(plot: Model)
	local owner = owners[plot]
	for _, button in buttons[plot] do
		local visible = false
		if owner then
			local unlocks = button:GetAttribute("Unlocks")
			local requires = button:GetAttribute("Requires")
			visible = not isOwned(owner, unlocks) and (requires == nil or isOwned(owner, requires))
		end
		button.Parent = if visible then plot.Buttons else nil
	end
end

local function startDropper(plot: Model, item: Instance)
	local drop = item:FindFirstChild("Drop", true)
	if not drop or not drop:IsA("BasePart") then
		return
	end
	local token = {}
	activeDroppers[item] = token
	task.spawn(function()
		while activeDroppers[item] == token do
			local ore = Instance.new("Part")
			ore.Size = Vector3.new(1, 1, 1)
			ore.CFrame = drop.CFrame * CFrame.new(0, -(drop.Size.Y / 2 + 1), 0)
			ore:SetAttribute("DropValue", drop:GetAttribute("DropValue") or 1)
			ore:SetAttribute("Plot", plot.Name)
			ore.Parent = workspace
			Debris:AddItem(ore, Config.DROP_LIFETIME)
			task.wait(drop:GetAttribute("DropInterval") or 2)
		end
	end)
end

local function unlock(plot: Model, itemName: string)
	local item = items[plot][itemName]
	if not item then
		warn("[TycoonService] no item named " .. tostring(itemName) .. " in " .. plot.Name)
		return
	end
	item.Parent = plot.Items
	startDropper(plot, item)
end

local function lockAll(plot: Model)
	for _, item in items[plot] do
		activeDroppers[item] = nil
		item.Parent = nil
	end
	refreshButtons(plot)
end

local function playerFromHit(hit: BasePart): Player?
	local character = hit.Parent
	local player = character and Players:GetPlayerFromCharacter(character)
	local humanoid = character and character:FindFirstChildOfClass("Humanoid")
	if player and humanoid and humanoid.Health > 0 then
		return player
	end
	return nil
end

local function claim(plot: Model, player: Player)
	local data = DataService.Get(player)
	if owners[plot] or plotOf[player] or not data then
		return
	end
	owners[plot] = player
	plotOf[player] = plot
	plot:SetAttribute("OwnerId", player.UserId)
	for itemName in data.purchased do
		unlock(plot, itemName)
	end
	refreshButtons(plot)
end

local function release(player: Player)
	local plot = plotOf[player]
	if not plot then
		return
	end
	owners[plot] = nil
	plotOf[player] = nil
	plot:SetAttribute("OwnerId", nil)
	lockAll(plot)
end

local function setupButton(plot: Model, button: BasePart)
	local busy = false
	button.Touched:Connect(function(hit)
		local player = playerFromHit(hit)
		if busy or not player or owners[plot] ~= player then
			return
		end
		local itemName = button:GetAttribute("Unlocks")
		if isOwned(player, itemName) then
			return
		end
		busy = true
		if CashService.TrySpend(player, button:GetAttribute("Price") or 0) then
			DataService.Get(player).purchased[itemName] = true
			unlock(plot, itemName)
			refreshButtons(plot)
		end
		task.wait(0.5)
		busy = false
	end)
end

local function setupPlot(plot: Model)
	items[plot] = {}
	for _, item in plot.Items:GetChildren() do
		items[plot][item.Name] = item
		item.Parent = nil
	end

	buttons[plot] = {}
	for _, button in plot.Buttons:GetChildren() do
		if button:IsA("BasePart") then
			table.insert(buttons[plot], button)
			setupButton(plot, button)
		end
	end

	plot.ClaimPad.Touched:Connect(function(hit)
		local player = playerFromHit(hit)
		if player then
			claim(plot, player)
		end
	end)

	plot.Collector.Touched:Connect(function(hit)
		local value = hit:GetAttribute("DropValue")
		if not value or hit:GetAttribute("Plot") ~= plot.Name then
			return
		end
		hit:Destroy()
		local owner = owners[plot]
		if owner then
			CashService.Add(owner, value)
		end
	end)

	refreshButtons(plot)
end

function TycoonService.Start()
	local folder = workspace:WaitForChild(Config.TYCOONS_FOLDER)
	for _, plot in folder:GetChildren() do
		if plot:IsA("Model") then
			setupPlot(plot)
		end
	end
	Players.PlayerRemoving:Connect(release)
end

return TycoonService
```

**Done when**
- The file requires without errors.

---

## Step 4: Register the services

In `src/server/Main.server.luau`, change `SERVICES` to:

```lua
local SERVICES = {
	"DataService",
	"CashService",
	"TycoonService",
}
```

**Done when**
- Playing in Studio shows no errors in Output.

---

## Step 5: Test plot

In `Workspace`, create a Folder `Tycoons`, and inside it a Model `Plot1` containing (all parts anchored):

- `ClaimPad`: Part, 6 x 1 x 6, green.
- `Collector`: Part, 6 x 1 x 6, placed 10 studs from the claim pad.
- `Items` Folder containing:
  - `Dropper1`: Model with a Part `Drop` (2 x 2 x 2) placed 6 studs directly above `Collector`. Attributes on `Drop`: `DropValue` = 5, `DropInterval` = 2.
  - `Wall1`: Model with any Part.
- `Buttons` Folder containing:
  - `BuyDropper1`: Part, attributes `Price` = 0, `Unlocks` = `Dropper1`.
  - `BuyWall1`: Part, attributes `Price` = 25, `Unlocks` = `Wall1`, `Requires` = `Dropper1`.

Duplicate `Plot1` as `Plot2` and move it aside, to test two players.

**Done when** (the tycoon acceptance test)
- [ ] Before claiming, no buttons and no items are visible.
- [ ] Touching `ClaimPad` shows `BuyDropper1` only.
- [ ] Buying it shows `Dropper1`, drops start falling, and `Cash` rises by 5 per drop.
- [ ] `BuyWall1` appears only after `Dropper1` is owned, and buying it costs 25.
- [ ] A second player (Test > Clients and Servers, 2 players) cannot claim or buy on your plot.
- [ ] Stop and play again: claiming restores both items and your cash.
- [ ] Output shows no errors or `[DataService]` warnings.

---

## The generic 50% is done

Stop here and tell the user the foundation is complete. Everything below is **their 50%**.

**Extension points**
- **New items:** a Model in `Items` plus a button with `Price`, `Unlocks` and optional `Requires`. No code changes.
- **New droppers:** any item with a `Drop` part and the two drop attributes.
- **Conveyors:** an anchored Part with `AssemblyLinearVelocity` set, carrying drops to the `Collector`.
- **Upgraders, multipliers, rebirths:** read and change `DropValue` on drops in a new service. Cash changes still go through `CashService`.
- **New saved data:** keys in `Config.DEFAULT_DATA`, accessed through `DataService.Get`.

**Ideas the user might ask for**
- A theme (pizza shop, mining, space station) and the full item tree
- Upgraders, conveyors, a rebirth system, offline earnings
- Cash UI, purchase effects, owner name signs on plots
- Gamepasses: 2x cash, auto-collect, VIP area
