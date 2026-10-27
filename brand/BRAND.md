# Baseplate brand kit

**Make better games.** The agent-native layer for Roblox.

## The mark

Four studs on a 2 x 2 plate. The bottom pair is solid: the generic 50% that agents lay down from a Baseplate spec. The top pair is open: the 50% that makes the game yours.

| File | Use |
|---|---|
| `baseplate-mark-ink.svg` | Default, on light backgrounds |
| `baseplate-mark-white.svg` | On Stud Blue or Ink |
| `baseplate-mark-blue.svg` | Accent use on white or Plate |
| `baseplate-mark-small.svg` | 16 to 31 px (thicker rings) |
| `baseplate-app-icon.svg` | App, plugin and directory tiles |
| `favicon.svg` | Browser tab |

## Logos

In `logo/`, each as SVG (text outlined, no font needed) and PNG, in `ink`, `white` and `blue`:

| File | Use |
|---|---|
| `baseplate-logo-horizontal-*` | Default logo: mark plus wordmark |
| `baseplate-logo-stacked-*` | Square spaces: mark above wordmark |
| `baseplate-wordmark-*` | When the mark already appears nearby |

## Social

In `social/`:

| File | Size | Use |
|---|---|---|
| `x-profile.png` | 400 x 400 | X profile picture (white mark on Stud Blue) |
| `x-profile-ink.png` | 400 x 400 | Alternate profile picture (on Ink) |
| `x-header.png` | 1500 x 500 | X header |
| `x-header@2x.png` | 3000 x 1000 | X header, high resolution |

## Construction

- 100 unit grid. Stud centers at 30 and 70 on both axes.
- Solid studs: radius 16. Open studs: radius 12, stroke 8 (outer edge at 16).
- Small mark: solid radius 17, open radius 11, stroke 12.
- Clear space: 28 units on every side of the mark's bounding box.
- Minimum size: 16 px.

## Color

| Name | Hex | Role |
|---|---|---|
| Stud Blue | `#1F4BFF` | The one accent. One use per view |
| Ink | `#111111` | Mark, text, dark grounds |
| Plate | `#F4F2EC` | Light ground |
| Stone | `#55534E` | Secondary text |
| Seam | `#DEDBD2` | Lines and borders |

## Type

- **Inter Tight**: headlines and UI. Semibold 600, tracking minus 2 to 4%.
- **JetBrains Mono**: tool names, file names, code. Medium 500.
- Wordmark: always lowercase `baseplate`, Inter Tight Semibold, tracking minus 4.5%.

## Rules

- Solid studs always at the bottom. Never flip the mark.
- Never fill all four studs. The open half is the point.
- Never stretch, squash, rotate or add effects.
- One color per mark. Never color studs individually.
