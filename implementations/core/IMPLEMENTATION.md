# Core: IMPLEMENTATION.md

The foundation every Baseplate game type builds on: project layout, player data, and safe client/server communication. Every game spec (obby, tycoon, simulator) starts by completing this file.

## Rules for the agent

1. Do the steps in order. Do not skip ahead.
2. Create files exactly at the paths given, with the code given. Do not rename anything.
3. After each step, check every **Done when** item. If one fails, fix it before moving on.
4. Do not add features that are not in this file. The game spec that follows will tell you what to add.
5. Use Luau. Use `task.wait`, `task.spawn` and `task.defer`, never `wait`, `spawn` or `delay`.

## Requirements

- Roblox Studio with **API Services** enabled (Game Settings > Security > Enable Studio Access to API Services). DataStores fail in Studio without it.
- [Rojo](https://rojo.space) 7 or newer, syncing this project into Studio.

---

## Step 1: Project layout

Create `default.project.json` in the project root. Replace `GAME_NAME` with the game's name in PascalCase.

```json
{
  "name": "GAME_NAME",
  "tree": {
    "$className": "DataModel",
    "ReplicatedStorage": {
      "Shared": { "$path": "src/shared" }
    },
    "ServerScriptService": {
      "Server": { "$path": "src/server" }
    },
    "StarterPlayer": {
      "StarterPlayerScripts": {
        "Client": { "$path": "src/client" }
      }
    }
  }
}
```

Create these empty folders: `src/shared`, `src/server/Services`, `src/client`.

**Done when**
- `rojo serve` starts with no errors.
- After connecting in Studio, `ReplicatedStorage.Shared`, `ServerScriptService.Server.Services` and `StarterPlayer.StarterPlayerScripts.Client` exist.

---

## Step 2: Config

Create `src/shared/Config.luau`. Game specs add their own keys to this table; they never create a second config file.

```lua
local Config = {}

Config.DATASTORE_NAME = "PlayerData_v1"
Config.DATASTORE_RETRIES = 3

-- Every key a player saves, with its starting value. Game specs add keys here.
Config.DEFAULT_DATA = {}

return Config
```

**Done when**
- `require(game.ReplicatedStorage.Shared.Config)` in the Studio command bar returns a table.

---

## Step 3: Remotes

All client/server communication goes through one module. The server creates the remotes; the client only waits for them.

Create `src/shared/Remotes.luau`:

```lua
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local FOLDER_NAME = "Remotes"

local Remotes = {}

-- Server only. Call once per remote name, before any client needs it.
function Remotes.Create(name: string): RemoteEvent
	assert(RunService:IsServer(), "Remotes.Create is server only")
	local folder = ReplicatedStorage:FindFirstChild(FOLDER_NAME)
	if not folder then
		folder = Instance.new("Folder")
		folder.Name = FOLDER_NAME
		folder.Parent = ReplicatedStorage
	end
	local existing = folder:FindFirstChild(name)
	if existing then
		return existing
	end
	local remote = Instance.new("RemoteEvent")
	remote.Name = name
	remote.Parent = folder
	return remote
end

-- Works on client and server. Yields until the remote exists.
function Remotes.Get(name: string): RemoteEvent
	local folder = ReplicatedStorage:WaitForChild(FOLDER_NAME)
	return folder:WaitForChild(name) :: RemoteEvent
end

-- Server helper: returns a function that is true at most `perSecond` times per second per player.
function Remotes.RateLimiter(perSecond: number)
	local last: { [Player]: number } = {}
	local interval = 1 / perSecond
	game:GetService("Players").PlayerRemoving:Connect(function(player)
		last[player] = nil
	end)
	return function(player: Player): boolean
		local now = os.clock()
		if last[player] and now - last[player] < interval then
			return false
		end
		last[player] = now
		return true
	end
end

return Remotes
```

**Security rules for every remote you add later**
- The server never trusts a value sent by the client. Check type, range and ownership.
- The client asks, the server decides. Clients send intent ("buy item 3"), never results ("I have 500 cash").
- Every remote that changes data is rate limited with `Remotes.RateLimiter`.

**Done when**
- The module requires without errors on both server and client.

---

## Step 4: DataService

Loads data on join, saves on leave and on shutdown, retries on failure, and never overwrites good data with empty data.

Create `src/server/Services/DataService.luau`:

```lua
local DataStoreService = game:GetService("DataStoreService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage.Shared.Config)

local store = DataStoreService:GetDataStore(Config.DATASTORE_NAME)
local profiles: { [Player]: { [string]: any } } = {}
local loadedEvent = Instance.new("BindableEvent")

local DataService = {}

-- Fires (player, data) once a player's data is ready.
DataService.Loaded = loadedEvent.Event

local function keyFor(player: Player): string
	return "player_" .. player.UserId
end

local function withRetries(fn: () -> any): (boolean, any)
	for attempt = 1, Config.DATASTORE_RETRIES do
		local ok, result = pcall(fn)
		if ok then
			return true, result
		end
		warn(string.format("[DataService] attempt %d failed: %s", attempt, tostring(result)))
		task.wait(2 ^ attempt)
	end
	return false, nil
end

local function load(player: Player)
	local ok, saved = withRetries(function()
		return store:GetAsync(keyFor(player))
	end)
	if not player.Parent then
		return -- left while loading
	end
	if not ok then
		-- Never let a player play on default data: it would overwrite their save.
		player:Kick("We could not load your data. Please rejoin.")
		return
	end

	local data = table.clone(Config.DEFAULT_DATA)
	if type(saved) == "table" then
		for key, value in saved do
			data[key] = value
		end
	end

	profiles[player] = data
	loadedEvent:Fire(player, data)
end

local function save(player: Player)
	local data = profiles[player]
	if not data then
		return -- never loaded, so never save
	end
	withRetries(function()
		store:UpdateAsync(keyFor(player), function()
			return data
		end)
	end)
end

-- Returns the live data table for a player, or nil if not loaded yet.
-- Mutate it directly; it is saved on leave and shutdown.
function DataService.Get(player: Player): { [string]: any }?
	return profiles[player]
end

-- Calls `callback(player, data)` for every player already loaded and every player who loads later.
function DataService.OnLoaded(callback: (Player, { [string]: any }) -> ())
	for player, data in profiles do
		task.spawn(callback, player, data)
	end
	DataService.Loaded:Connect(callback)
end

function DataService.Start()
	Players.PlayerAdded:Connect(load)
	for _, player in Players:GetPlayers() do
		task.spawn(load, player)
	end

	Players.PlayerRemoving:Connect(function(player)
		save(player)
		profiles[player] = nil
	end)

	game:BindToClose(function()
		local pending = 0
		for _, player in Players:GetPlayers() do
			pending += 1
			task.spawn(function()
				save(player)
				pending -= 1
			end)
		end
		while pending > 0 do
			task.wait()
		end
	end)
end

return DataService
```

**Done when**
- Playing in Studio prints no `[DataService]` warnings.
- Stopping play prints no errors.

---

## Step 5: Server entry point

Create `src/server/Main.server.luau`. Game specs add their services to `SERVICES`, in the order they give.

```lua
local Services = script.Parent.Services

-- DataService must stay first.
local SERVICES = {
	"DataService",
}

for _, name in SERVICES do
	local service = require(Services[name])
	service.Start()
end
```

**Done when**
- Playing in Studio shows no errors in Output.

---

## Step 6: Client entry point

Create `src/client/Main.client.luau`:

```lua
local Controllers = script.Parent:WaitForChild("Controllers")

-- Game specs add controllers here.
local CONTROLLERS = {}

for _, name in CONTROLLERS do
	local controller = require(Controllers:WaitForChild(name))
	controller.Start()
end
```

Create the empty folder `src/client/Controllers`.

**Done when**
- Playing in Studio shows no errors in Output.

---

## Core complete

Return to the game spec you came from and continue with its first step.
