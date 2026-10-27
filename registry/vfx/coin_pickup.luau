-- coin_pickup: a quick gold sparkle burst with a soft glow. Built-in textures, no upload needed.
local SPARKLE = "rbxasset://textures/particles/sparkles_main.dds"

return {
	emitters = {
		{
			emit = 14,
			properties = {
				Name = "Sparkles",
				Texture = SPARKLE,
				Color = ColorSequence.new(Color3.fromRGB(255, 236, 140), Color3.fromRGB(255, 176, 32)),
				LightEmission = 1,
				Lifetime = NumberRange.new(0.35, 0.6),
				Speed = NumberRange.new(8, 14),
				SpreadAngle = Vector2.new(180, 180),
				Drag = 6,
				Acceleration = Vector3.new(0, 6, 0),
				Rotation = NumberRange.new(0, 360),
				RotSpeed = NumberRange.new(-180, 180),
				Size = NumberSequence.new({
					NumberSequenceKeypoint.new(0, 0.6),
					NumberSequenceKeypoint.new(1, 0),
				}),
				Transparency = NumberSequence.new({
					NumberSequenceKeypoint.new(0, 0),
					NumberSequenceKeypoint.new(0.7, 0.2),
					NumberSequenceKeypoint.new(1, 1),
				}),
			},
		},
		{
			emit = 1,
			properties = {
				Name = "Glow",
				Texture = SPARKLE,
				Color = ColorSequence.new(Color3.fromRGB(255, 214, 90)),
				LightEmission = 1,
				Lifetime = NumberRange.new(0.25, 0.25),
				Speed = NumberRange.new(0, 0),
				Size = NumberSequence.new({
					NumberSequenceKeypoint.new(0, 1.5),
					NumberSequenceKeypoint.new(1, 3.5),
				}),
				Transparency = NumberSequence.new({
					NumberSequenceKeypoint.new(0, 0.3),
					NumberSequenceKeypoint.new(1, 1),
				}),
			},
		},
	},
}
