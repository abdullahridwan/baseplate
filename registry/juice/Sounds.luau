--!strict
-- Sound IDs for Juice. Each `add` of a sound appends an entry here.
-- `id` is the Roblox asset ID you get after uploading the .ogg to your own account.
-- An empty id means "not uploaded yet": Juice warns once and skips it.

export type SoundDef = {
	id: string,
	volume: number,
	pitchVariance: number?, -- 0.05 = up to 5% random pitch shift per play, so repeats don't sound robotic
}

local Sounds: { [string]: SoundDef } = {
	-- coin_pickup = { id = "", volume = 0.5, pitchVariance = 0.05 },
}

return Sounds
