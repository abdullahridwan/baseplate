-- hit: sharp white-orange impact sparks. Fast and short so it reads on rapid hits.
local SPARKLE = "rbxasset://textures/particles/sparkles_main.dds"

return {
	emitters = {
		{
			emit = 10,
			properties = {
				Name = "Sparks",
				Texture = SPARKLE,
				Color = ColorSequence.new(Color3.fromRGB(255, 255, 255), Color3.fromRGB(255, 140, 40)),
				LightEmission = 1,
				Lifetime = NumberRange.new(0.15, 0.3),
				Speed = NumberRange.new(20, 32),
				SpreadAngle = Vector2.new(180, 180),
				Drag = 10,
				Squash = NumberSequence.new(-1.5), -- stretches particles along their motion: streaks instead of dots
				Size = NumberSequence.new({
					NumberSequenceKeypoint.new(0, 0.4),
					NumberSequenceKeypoint.new(1, 0),
				}),
			},
		},
		{
			emit = 1,
			properties = {
				Name = "Flash",
				Texture = SPARKLE,
				Color = ColorSequence.new(Color3.fromRGB(255, 245, 220)),
				LightEmission = 1,
				Lifetime = NumberRange.new(0.1, 0.1),
				Speed = NumberRange.new(0, 0),
				Size = NumberSequence.new({
					NumberSequenceKeypoint.new(0, 2),
					NumberSequenceKeypoint.new(1, 3),
				}),
				Transparency = NumberSequence.new({
					NumberSequenceKeypoint.new(0, 0.1),
					NumberSequenceKeypoint.new(1, 1),
				}),
			},
		},
	},
}
