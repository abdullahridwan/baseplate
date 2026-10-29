# Open items: what has not been done yet

Last updated: 2026-10-28, after the simplified component-library homepage. V1 is the component library only. Recipes and implementation.md specs are not V1.
Source of truth: this repo. This file is the list, not a claim that the
items below are done.

## Done, for context

- DIRECTION.md: MVP direction, V1 scope, takeover rules, one-large-push workflow
- npm bin fix: cli/package.json now lists both `baseplate` and `baseplate-cli`
- find_vfx and add_vfx MCP tools, with safe-only search, vfx.json lockfile,
  and refusal of flagged or unknown packs, tested locally with a test index
- Safe VFX index format: registry/safe-vfx.json and docs/r/safe-vfx.json
- Site: Connect your agent section, VFX report page template, tycoon and
  simulator labeled beta in the MCP list_recipes and on the old site
- Simplified homepage 2026-10-28: homepage now leads with the component
  library only, with no pick-a-game, no showcase, and no implementation.md
  flow. Recipes stay in implementations/ in the repo, but are not V1.
- Existing work carried over: 53 effects, 50 sounds, Juice runtime, core,
  obby, tycoon, and simulator recipes, and the existing MCP tools

## Done 2026-10-29: scan data landed

- 300 free VFX packs scanned on 2026-10-28: 188 safe, 70 flagged, 22 with scripts, 20 not VFX.
  Raw results are in pipeline/vfx/data/2026-10-28/, the pipeline is in pipeline/vfx/,
  the safe index is registry/safe-vfx.json, and the report page reads docs/r/vfx-assets.json.
  find_vfx and add_vfx were smoke tested against it; add_vfx refuses flagged packs.

## Not done: blocked on the owner or on external data

- Publish baseplate-cli 0.3.0 to npm. The name returned 404 on npm on
  2026-10-28, so it looks free, but publishing needs the owner's npm
  account, token, or 2FA. Muse cannot do npm login from chat credentials.
- Test the one-line install from a clean folder after publishing:
  `claude mcp add baseplate -- npx -y baseplate-cli mcp`
  The site Connect section currently says this requires 0.3.0 or later
  on npm, and that until it is published the MCP code is in cli/.
- Land real safe scan data. The safe index format is live, but packs is
  empty. No real asset IDs are in the repo, and the 300 scanned / 70
  flagged figure from Claude's plan is not verified in this repo.
  find_vfx therefore returns an empty-index message until scan data lands.
- Build and run the weekly scan job. The scan rules are written down,
  but there is no scheduled scan, no Roblox API key job, and no
  re-scan on pack change yet.
- Give a contact email for request a re-check, and add it to the VFX
  report page. The report page currently says contact email to be added.
- Update or delete the old demo artifact that still says "lie" and shows
  creator names. Its location is not in this repo at last check, so it
  has not been updated or deleted yet.
- Clarify the fourth ask from Claude's plan. The plan said four things
  were needed from the owner, but only two owner items were listed:
  npm login and contact email. The Studio obby run is no longer a V1
  item, because recipes are not V1.

## Not done: V1 code and site, not yet built

- Real safe packs in the MCP and on the VFX report page. See scan data above.
- Verified Codex and Cursor config paths. The site shows config snippets,
  but they have not been tested end to end in Codex or Cursor.
- A tested end-to-end V1 demo: connect MCP, find_vfx, add_vfx, insert in
  Studio, strip scripts, and play. That chain has been tested locally
  for find_vfx and add_vfx only, not in Studio.

## Not done: V2, expansion, and monetization

- Recipes and implementation.md specs: obby, tycoon, and simulator specs
  stay in implementations/, but are not V1 and are not on the V1 homepage.

- Fastlane shipping: `baseplate ship`, build with Rojo, publish a place
  version, upload images, audio, and models through Open Cloud, with a
  guided checklist for first-time creation, maturity questionnaire,
  going public, and the API Services toggle. Agent-native key handling
  is part of this, not a separate manual step.
- Image generation and capture: generate icons and thumbnails from game
  context, or capture real screenshots with a Studio plugin that moves
  the camera through the map.
- Music pack, Studio-recorded effect previews to replace 2D previews,
  own particle textures, and packs per game type wired into specs.
- More recipes: tower defense, horror, fighting, and a zombies or
  survival recipe. The zombies game was the original test case.
- Paid tier: a key-gated paid registry, a payment link, premium packs,
  and later a subscription for new drops, expanded safe database
  updates, and fastlane. No price, payment provider, or paid pack has
  been chosen yet. Free stays free: core, working obby, own 53 effects
  and 50 sounds, and basic MCP.
- Open contributions and marketplace: creator pack submissions gated by
  the safety scan and a quality bar, and later a marketplace with a cut,
  payouts, and moderation.
- Scan more than 300 packs, and expand the safe database weekly.
- Swap our sounds for Roblox licensed free sounds, seeded from the 27
  CastleSiege sounds found earlier. License check still needed, and no
  sound upload path has been changed yet.
- Custom domain, so the prompt and site do not show github.io.
- Launch post: the VFX report as the hook, posted on X and the DevForum,
  plus TikTok videos about malicious packs. Do not post the 70 of 300
  figure until scan data is verified in this repo.
- Cost and reliability benchmarks: frontier model from scratch versus
  Baseplate, as listed in the README roadmap.

## What finished means

The website is live, but it is not finished V1 until: npm is published
and the clean install works, real safe data is in the MCP and report
page, and a re-check contact email is published. Recipes are not part
of finished V1. Until then, the site correctly says the install is not
yet published and the report page has no real packs yet.
