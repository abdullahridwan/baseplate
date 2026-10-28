-- heal: soft green motes drifting upward. Target the character's root part.
local SPARKLE = "rbxasset://textures/particles/sparkles_main.dds"

return {
	emitters = {
		{
			emit = 18,
			properties = {
				Name = "Motes",
				Texture = SPARKLE,
				Color = ColorSequence.new(Color3.fromRGB(170, 255, 170), Color3.fromRGB(40, 200, 90)),
				LightEmission = 0.8,
				Lifetime = NumberRange.new(1, 1.6),
				Speed = NumberRange.new(1, 3),
				SpreadAngle = Vector2.new(180, 180),
				Acceleration = Vector3.new(0, 5, 0),
				Drag = 1,
				Size = NumberSequence.new({
					NumberSequenceKeypoint.new(0, 0),
					NumberSequenceKeypoint.new(0.3, 0.6),
					NumberSequenceKeypoint.new(1, 0),
				}),
				Transparency = NumberSequence.new({
					NumberSequenceKeypoint.new(0, 0.2),
					NumberSequenceKeypoint.new(1, 1),
				}),
			},
		},
	},
}
