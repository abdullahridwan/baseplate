# Baseplate direction: MVP

Source of truth: this repository, `abdullahridwan/baseplate`, on `main`.
Claude built baseplate up to 2026-10-28. From 2026-10-28, Muse is taking over.
No direction, feature, or data lives only on a local Desktop folder, in a chat,
or in a demo artifact. If it is not in this repo, it is not shipped.

## Origin

Baseplate grew from trying to make Roblox games as a non-Roblox dev using
AI agents. The agents kept not working right, not because the game idea was
hard, but because Roblox development is a thousand small things: saves,
remotes, checkpoints, sound uploads, particle tuning, publishing, and more.

Two concrete gaps drove the first work:

- Sounds were limited to Roblox and Pro Pack creator sounds. Community audio
  often has unclear licenses and can be deleted and break a game silently.
  Making your own sounds is slow.
- VFX were hard to find and judge in the Creator Store. An agent had to guess
  from titles and thumbnails, with no way to tell which packs were safe.

The test game for this idea was a Call of Duty Zombies-like game: waves,
enemy AI, weapons, points, sounds, and VFX, all at once. If an agent can
build that without hand-holding every small step, the infrastructure works.

## Goal

Make better games with less money and less time. Build a game fast,
frictionless, and dead easy.

The agent layer is the product, not any single effect or sound. It should
let a cheap model execute the generic work, and reserve a frontier model
for the creative work that makes a game yours.

## Principles

1. Copy, do not install. Files land in the user's project. Once copied,
   the user owns them and is not dependent on Baseplate staying up.
   A shared asset that can be deleted must never break everyone's games.
2. Agent-native text over images. An agent should pick a component from a
   description, tags, and use case, not by reviewing thumbnails one by one.
   Image review costs tokens and context. Text search is fast and cheap.
3. Thorough specs, cheap execution. Implementation specs cover the generic
   half of a game: project layout, saves, messaging, loaders, and the
   game-type systems. They are written long and in order, with a Done When
   check after every step, so a cheap model like Haiku can run them and
   Opus can be saved for creative parts.
4. Safety is a feature, not a claim. A pack is safe only for a pinned
   version, on a stated scan date, under stated scan rules, with a way to
   request a re-check.
5. No login cookies, no manual key pasting as a permanent step. Publishing
   and asset work should use official Open Cloud APIs with an API key
   pulled natively by the agent. Steps that cannot be automated become a
   guided checklist, not a mystery.
6. Free stays useful. Paid must be for premium stuff on top, never for
   taking back something hobbyists already rely on.

## V1: what we ship first

V1 is a safe, searchable component library for VFX and sounds, delivered
through a drop-in MCP server. It is the cleanest first ship because it is
one promise, one install, and one proof point.

### V1 includes

- A published npm package, `baseplate-cli`, where the one-line install
  actually works from a clean folder:
  `claude mcp add baseplate -- npx -y baseplate-cli mcp`
  Fix the bin first: `cli/package.json` currently only lists the `baseplate`
  bin, not `baseplate-cli`, so that install line must be tested, not assumed.
- MCP search by description and use case, not just title. Example:
  `find_vfx("fire explosion")` returns only safe packs, with a description,
  pinned version, and how to use each one.
- `add_vfx` writes a `vfx.json` lockfile and tells the agent to insert the
  pack with the Roblox Studio MCP and strip any scripts.
- Safe packs only in the MCP. Malicious packs are never offered by the MCP.
  They appear only on the website report page and in short demo videos as
  warnings, showing what an agent can pull in without this layer.
- A weekly scan loop: scan VFX packs, lock in results, re-scan on a schedule,
  and flag any pack that changes after it was scanned. Pinning is what
  protects a user from a pack turning bad later.
- The site Connect your agent section: the one install line for Claude Code,
  plus config snippets for Codex and Cursor. The current site is only the
  copy-a-prompt flow, so this section is a V1 blocker.
- The obby recipe as the one working recipe, tested once in Studio.
  Tycoon and simulator are labeled beta until they are tested the same way,
  because they still need a hand-built map. One recipe that works beats
  three that half work.
- The legal and report page made safe to share: a contact email for
  request a re-check, and the old demo artifact updated or deleted if it
  still says "lie" or shows creator names without a verified basis.

### V1 includes from existing work

- The own component library already in this repo: 53 effects and 50 sounds
  at last check, with the Juice runtime, categories, and looping effects.
  These are original or clean-licensed, and they stay free.
- The existing MCP tools in `cli/lib/mcp.js`: `list_recipes`, `get_recipe`,
  `list_components`, `search_components`, `get_component`, `add_component`.
  `find_vfx` and `add_vfx` are for external scanned packs. They do not
  replace the own-registry tools. The distinction must stay clear in docs:
  own registry versus scanned Creator Store packs.

### V1 does not include

- Fastlane shipping (`baseplate ship`), image generation for icons and
  thumbnails, music packs, a creator marketplace, or a full paid tier.
  Those are V2. They are in PLAN.md and stay there until V1 ships.
- More game-type recipes as headlines. Tower defense, horror, fighting,
  and a zombies or survival recipe are expansion, not V1.

### Safe VFX data model

Every scanned pack entry must carry, at minimum:

- name, description, tags, and use cases, written for search, not just a title
- Roblox asset ID and pinned version
- status: safe or flagged, with scan date
- scan rules used, in plain language, for example hidden require by ID,
  data exfiltration, and obfuscated code that phones home
- install steps, and a note to strip scripts on insert
- a re-check path, using the contact email on the report page

Do not publish a pack as safe without those fields. Do not publish
creator names or accusations from a demo artifact without verified evidence.

### Sounds in V1

Own sounds ship in V1. Scanned external sounds do not, because their
licensing is messier than scanned VFX. The can-wait idea of swapping our
sounds for Roblox licensed free sounds, seeded from the 27 CastleSiege
sounds found earlier, needs a license check first and is not a V1 blocker.

## Expansion after V1

In order, after V1 is live and measured:

1. Premium packs and per-game packs: obby, tycoon, simulator, then tower
   defense, horror, fighting, and a zombies or survival pack.
2. Music pack, Studio-recorded effect previews, and packs wired into specs
   so every game ships with sound and effects by default.
3. Fastlane: build with Rojo, publish a place version, upload images,
   audio, and models through Open Cloud, with a guided checklist for
   first-time creation, maturity questionnaire, going public, and the
   API Services toggle.
4. Image generation and capture: generate icons and thumbnails from game
   context, or capture real screenshots with a Studio plugin that moves
   the camera through the map. Captured images are closer to the real
   game and less likely to look misleading.
5. Open contributions: creators submit packs, gated by the safety scan
   and a quality bar. Later, a marketplace with a cut, payouts, and
   moderation. Do not start the marketplace before the scan gate works.

## Monetization direction

Keep it free for hobbyists. Charge for awesome stuff on top.

- Free forever: core recipe, the working obby recipe, the own 53 effects
  and 50 sounds, basic MCP search and add, and the safe search for the
  core safe set.
- Paid later, not on day one: premium packs, music, expanded safe database
  updates, fastlane shipping, store assets, and team use. Start with a
  one-time paid pack before a subscription, because a one-time purchase
  is easier for hobbyists to say yes to than a monthly plan for a new tool.
- Paid delivery: a key-gated registry. The CLI already reads
  `BASEPLATE_REGISTRY` from the environment, so a paid index can sit
  behind a key without a rewrite. Free index stays public.
- Paid additions use a separate, clearly marked proprietary license.
  Do not retroactively close MIT free work.
- Never sell third-party Creator Store packs that Baseplate does not own.
  Sell the scan, the description, the index, and Baseplate's own packs.
  Link or reference external packs. Do not redistribute their code unless
  the license clearly allows it.

V1 itself is free, to get distribution: installs, MCP connections, and a
waitlist for paid. Paywalling the safe library on day one would kill the
discovery that makes paid possible later.

## How Muse works on this repo from now on

- This repo is the source of truth. Work happens in branches, with a pull
  request per feature, and merges only after the change is checked.
- Every feature ships with code, docs updated in the same change, and a
  note in this file or PLAN.md if the scope changes.
- No feature is marked done from a chat claim. Done means: code in main,
  install or MCP flow tested from a clean state where that applies, and
  the site or docs updated if the feature is user-facing.
- Local-only work does not count. If a scan result, report page, or site
  change is not pushed to this repo, it is treated as missing, not done.

## Open blockers, as of 2026-10-28

- npm login and publish: the package name `baseplate-cli` returned 404 on
  npm on 2026-10-28, so it looks free, but publishing needs the owner's
  npm account and token or 2FA. That cannot be done from chat credentials.
- Safe scan data: the 300 scanned packs and the 70 flagged figure from
  Claude's plan are not in this repo at last check. `find_vfx` cannot ship
  real data until that scan data, or a new scan, lands here in the format
  above.
- Studio test: the obby recipe still needs a run in Studio, about 10
  minutes, by the owner. Muse cannot run Roblox Studio from here.
- Contact email: needed for request a re-check on the report and legal page.
- The fourth ask in Claude's plan: the plan said four things were needed
  from the owner, but only three owner items were listed: npm login,
  Studio obby run, and contact email. That fourth item is still unclear.

## Success measures for V1

- npm installs and clean-folder MCP installs that actually work
- MCP connections, `find_vfx` searches, and search to add conversion
- Safe packs added to real projects, not just site visits
- Report page visits and demo video views that convert to installs
- Weekly scan runs completed, with flagged changes surfaced, not silent

If V1 does not move those numbers, the next feature is not more catalog.
It is better search, better descriptions, or a better install.
