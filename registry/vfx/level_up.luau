-- level_up: a rising column of blue-white sparkles. Target the character's root part.
local SPARKLE = "rbxasset://textures/particles/sparkles_main.dds"

return {
	emitters = {
		{
			emit = 30,
			properties = {
				Name = "Rise",
				Texture = SPARKLE,
				Color = ColorSequence.new(Color3.fromRGB(150, 230, 255), Color3.fromRGB(60, 120, 255)),
				LightEmission = 1,
				Lifetime = NumberRange.new(0.9, 1.4),
				Speed = NumberRange.new(4, 9),
				SpreadAngle = Vector2.new(25, 25),
				EmissionDirection = Enum.NormalId.Top,
				Acceleration = Vector3.new(0, 4, 0),
				Rotation = NumberRange.new(0, 360),
				RotSpeed = NumberRange.new(-90, 90),
				Size = NumberSequence.new({
					NumberSequenceKeypoint.new(0, 0.2),
					NumberSequenceKeypoint.new(0.3, 0.7),
					NumberSequenceKeypoint.new(1, 0),
				}),
				Transparency = NumberSequence.new({
					NumberSequenceKeypoint.new(0, 0),
					NumberSequenceKeypoint.new(1, 1),
				}),
			},
		},
		{
			emit = 1,
			properties = {
				Name = "Ring",
				Texture = SPARKLE,
				Color = ColorSequence.new(Color3.fromRGB(170, 220, 255)),
				LightEmission = 1,
				Lifetime = NumberRange.new(0.5, 0.5),
				Speed = NumberRange.new(0, 0),
				Orientation = Enum.ParticleOrientation.VelocityPerpendicular,
				Size = NumberSequence.new({
					NumberSequenceKeypoint.new(0, 1),
					NumberSequenceKeypoint.new(1, 8),
				}),
				Transparency = NumberSequence.new({
					NumberSequenceKeypoint.new(0, 0.2),
					NumberSequenceKeypoint.new(1, 1),
				}),
			},
		},
	},
}
