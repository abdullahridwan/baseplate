-- confetti: colourful pieces that pop up then flutter down. For wins, purchases, unlocks.
local SPARKLE = "rbxasset://textures/particles/sparkles_main.dds"

return {
	emitters = {
		{
			emit = 60,
			properties = {
				Name = "Confetti",
				Texture = SPARKLE,
				Color = ColorSequence.new({
					ColorSequenceKeypoint.new(0, Color3.fromRGB(255, 80, 110)),
					ColorSequenceKeypoint.new(0.25, Color3.fromRGB(255, 200, 40)),
					ColorSequenceKeypoint.new(0.5, Color3.fromRGB(60, 220, 120)),
					ColorSequenceKeypoint.new(0.75, Color3.fromRGB(60, 160, 255)),
					ColorSequenceKeypoint.new(1, Color3.fromRGB(190, 90, 255)),
				}),
				LightEmission = 0.3,
				Lifetime = NumberRange.new(1.8, 2.6),
				Speed = NumberRange.new(25, 40),
				SpreadAngle = Vector2.new(35, 35),
				EmissionDirection = Enum.NormalId.Top,
				Acceleration = Vector3.new(0, -30, 0),
				Drag = 2.5,
				Rotation = NumberRange.new(0, 360),
				RotSpeed = NumberRange.new(-400, 400),
				Size = NumberSequence.new(0.45),
				Transparency = NumberSequence.new({
					NumberSequenceKeypoint.new(0, 0),
					NumberSequenceKeypoint.new(0.85, 0),
					NumberSequenceKeypoint.new(1, 1),
				}),
			},
		},
	},
}
