# Baseplate in the Claude Connectors Directory: implementation plan

Status: plan only, not yet built. This is the specific work needed to get
Baseplate listed in Claude's Connectors Directory, so a user can find it
in Claude Desktop Settings > Connectors, instead of only adding it by hand.

Last checked against the repo on 2026-10-28: the local MCP server in
`cli/lib/mcp.js` has 8 tools, no `readOnlyHint` / `destructiveHint`
annotations, and no tool titles. The remote server below does not exist
yet. Do not submit until the gating items in section 9 are done.

## 0. The core architecture decision

Do not try to make the remote directory server do everything the local
server does. It cannot, and reviewers will fail it if it pretends to.

- Remote directory connector: read only, public data only, no auth.
  It answers: what components exist, what matches a description, and
  what a component is for. It never touches a user's project.
- Local add, via the Claude Code plugin (already in this repo) and the
  Desktop Extension (already in this repo): `add_component` and
  `add_vfx`. Those write files into the user's own Rojo project, which
  a remote server cannot and must not do.
- The directory submission pairs the two: submit the remote server as
  the connector, and pair it with the plugin that does the local add.
  The portal explicitly allows pairing a plugin with a submitted server.

That split is what makes the directory listing honest. Discovery is
remote and public. Adding is local and owned by the user.

## 1. Remote server: what to build

### 1.1 Stack and transport

- Node.js 18 or later, TypeScript SDK
  `@modelcontextprotocol/sdk`, Streamable HTTP transport, stateless.
  No SSE endpoint. SSE is deprecated for this purpose.
- Reuse the existing handlers, do not rewrite the search logic from
  scratch. Extract from `cli/lib/mcp.js` and `cli/lib/registry.js`:
  `loadIndex`, `search_components`, `list_components`, and a metadata
  only version of `get_component` (see 1.3).
- New folder in this repo, to be created when building:
  `server/remote/`
  - `server/remote/package.json` (name `baseplate-remote-mcp`,
    type module, Node >= 18, dependency
    `@modelcontextprotocol/sdk` only, no other runtime deps)
  - `server/remote/src/index.js` (HTTP server, MCP endpoint, health)
  - `server/remote/src/tools.js` (the 3 remote tools, with titles
    and annotations from section 3)
  - `server/remote/Dockerfile` (node:20-slim, copy src, expose 3000,
    run `node src/index.js`)
  - `server/remote/fly.toml` or the equivalent for the chosen host
    (see 1.2), with a health check on `/health`
- Endpoints, exact:
  - `POST /mcp` - Streamable HTTP MCP endpoint. This is the URL
    submitted to the portal. Example, once hosted:
    `https://<host>/mcp`
  - `GET /health` - returns `200` with `{"ok": true}`, no auth, no
    MCP protocol. Used by the host health check and by reviewers
    to see the server is up.
  - `GET /` - redirect to the Baseplate docs page, not an MCP
    endpoint. Do not submit the root URL to the portal, submit
    the `/mcp` URL.
- No sessions stored. Each MCP request is handled independently.
  No database. The only upstream fetch is the public registry index
  at `https://abdullahridwan.github.io/baseplate/r/index.json`,
  which `cli/lib/registry.js` already fetches today.

### 1.2 Hosting and URL

- Recommended host: Fly.io, or Railway as an equivalent. Criteria:
  small Node app, automatic HTTPS, automatic deploy from GitHub,
  one machine always on (no auto-stop to zero, reviewers must be
  able to reach it at any time), health check support.
- Fly.io specifics, to be set at deploy time:
  - App name: `baseplate-mcp` (if taken, add a suffix and record
    the final name here, do not guess a URL in the portal)
  - Region: closest to the owner, one machine, `auto_stop_machines`
    off, `min_machines_running = 1`
  - Port: internal 3000, external 443 via Fly's HTTPS proxy
  - Deploy: `fly deploy` from `server/remote/`, on every push to
    main that touches `server/remote/` or `registry/`
- URL rule, hard: the URL submitted to the portal must be the final
  URL. Changing the URL after the portal's connect step forces a
  reconnect and a re-read of the tools. So:
  - Step 1: deploy to a stable `<app>.fly.dev` URL and test it as
    a custom connector first (see section 7).
  - Step 2: only then submit that exact URL.
  - A custom domain such as `mcp.baseplate.example` is a later
    improvement, not a blocker, and it must not be invented in
    the portal. No custom domain is owned yet as of this plan.

### 1.3 Remote tools: only 3, not 8

Current local tools, and what happens to each remotely:

| Local tool | Remote? | Reason |
| --- | --- | --- |
| `list_components` | Yes | Read only, public registry |
| `search_components` | Yes | Read only, public registry, the core discovery tool |
| `get_component` | Yes, metadata only | Read only, but full Luau source is too large to return remotely for every call. Remote returns name, kind, category, description, tags, usage, files, requires, license. Full source stays in the local plugin, where `add_component` already copies it. |
| `find_vfx` | No, until scan data lands | `registry/safe-vfx.json` is currently `packs: []` with `scan_date: null`. A reviewer testing `find_vfx` today gets an empty result. Do not submit it until packs are non-empty and verified. Add it as a connector update later, not in the first submission. |
| `add_component` | No, local only | Writes files into the user's project and edits `Sounds.luau`. A remote server has no access to that project. |
| `add_vfx` | No, local only | Writes `vfx.json` into the user's project. Same reason. |
| `list_recipes` | No | Recipes are not V1. V1 is the component library only. Do not confuse reviewers with recipe tools. |
| `get_recipe` | No | Same reason as `list_recipes`. |

Remote tool count at first submission: 3. That is intentional.
A small, honest connector passes review faster than a large one
with empty or local-only tools.

### 1.4 Auth: none, public data

- Authentication for the directory connector: none.
- Reason: the 3 remote tools only read public data. Components are
  MIT (VFX) and CC0-1.0 (SFX), published on GitHub Pages. No user
  account, no API key, no OAuth is needed to read them.
- Portal field: authentication = "No authentication".
- Test account: not applicable, because there is no login. Reviewers
  test with no account, using the example queries in section 7.
  Do not invent a test account. If the portal requires a value in
  that field, enter "No account needed, public data, see example
  queries in the docs page" and link the docs page.
- No secrets in the remote server. No `user_config` secrets, no
  env API keys. The only env values are host, port, and the
  registry URL, which is already public.

### 1.5 Security, rate limiting, and data handling for the remote server

- DNS rebinding protection: allow only the submitted host name,
  plus `localhost` for local testing. Reject other Host headers.
- Input validation: query strings max 200 characters, trimmed.
  Reject empty queries with a clear "Nothing matches" message,
  the same message the local server already returns.
- No shell execution remotely. No file writes remotely. No
  `project_dir` parameter remotely. If a client sends an add
  request to the remote server, return an error telling it to
  use the local plugin or Desktop Extension for adding.
- Rate limiting: 60 requests per minute per IP, returning `429`
  with a retry message. No account lockout, because there are
  no accounts.
- CORS: allow Claude's web and desktop origins for the MCP
  endpoint. The MCP connection itself is server to server from
  Anthropic's cloud for custom connectors, so CORS is not the
  main path, but do not leave it wide open to every origin.
- Logging and metrics, V1 KPI only: aggregate counts only.
  Allowed: total tool calls per day, per tool, and error rate.
  Not allowed in V1: per-user tracking, per-project tracking,
  storing search terms, storing prompts, or storing IP addresses
  beyond the host's standard access logs (30 day retention,
  aggregate only, not exported). This matches the V1 KPI decision:
  no CLI/MCP phone-home telemetry, no per-user or per-project
  tracking, only public aggregate counts.
- Data retention statement for the privacy policy: queries are
  processed in memory to search the public index and are not
  stored. No training on queries. No sale of data. No third
  party analytics on the MCP endpoint.

## 2. Tool titles and annotations, exact values to implement

The portal flags tools missing a title and a `readOnlyHint` or
`destructiveHint`. Implement these exact values in
`server/remote/src/tools.js`, and in the local server when it is
next updated, so local and remote agree.

MCP annotation fields, per tool:

- `title`: human readable name, shown in Claude's UI
- `readOnlyHint`: true if the tool only reads, false if it writes
- `destructiveHint`: true if the tool can delete or irreversibly
  change something, false otherwise
- `idempotentHint`: true if calling it twice has the same effect
  as calling it once
- `openWorldHint`: true if the tool reaches the open web, false
  if it only reads a closed, known data set

### Remote tools

1. `list_components`
   - title: "List components"
   - readOnlyHint: true
   - destructiveHint: false
   - idempotentHint: true
   - openWorldHint: false
   - Description, exact: "List Baseplate components: visual effects
     (vfx) and sounds (sfx) for Roblox games. Returns name, kind,
     and description only."
   - Input: optional `kind`, enum `vfx` or `sfx`. No other inputs.

2. `search_components`
   - title: "Search components"
   - readOnlyHint: true
   - destructiveHint: false
   - idempotentHint: true
   - openWorldHint: false
   - Description, exact: "Find Baseplate components by what they
     are for, for example 'coin', 'button click', 'win', or
     'damage'. Searches names, descriptions, and tags in text,
     not thumbnails. Returns matching components as name, kind,
     and description only."
   - Input: required `query`, string, max 200 characters.
   - Output: one line per match, `name (kind): description`,
     sorted by match score, same as the local server today.
     If no match, return: `Nothing matches "<query>". Call
     list_components to see everything.`

3. `get_component`
   - title: "Get component details"
   - readOnlyHint: true
   - destructiveHint: false
   - idempotentHint: true
   - openWorldHint: false
   - Description, exact: "Details for one Baseplate component:
     description, category, tags, usage, files, requires, and
     license. Does not return full Luau source remotely. Use
     the local Baseplate plugin or Desktop Extension to copy
     the component into a project."
   - Input: required `name`, string, exact component name.
   - Output: metadata only, no full source, no file contents.

### Local only tools, for reference and for the plugin listing

These are NOT in the remote connector, but they must have the
same titles and hints in the local plugin, so reviewers and
users see a consistent story:

4. `add_component` (local only)
   - title: "Add component to project"
   - readOnlyHint: false
   - destructiveHint: true
   - idempotentHint: true
   - openWorldHint: false
   - Why destructiveHint is true, and how to explain it in the
     listing: it writes files into the user's project and edits
     `src/shared/Juice/Sounds.luau` for sounds. It never
     overwrites an existing file, it skips existing files and
     reports them as "Already there (left unchanged)". That
     explanation must be in the docs page, not just in code.

5. `add_vfx` (local only)
   - title: "Add safe VFX pack"
   - readOnlyHint: false
   - destructiveHint: true
   - idempotentHint: true
   - openWorldHint: false
   - Why: it writes `vfx.json` in the user's project, deduplicated
     by `asset_id:pinned_version`, so calling it twice does not
     duplicate the entry. It never offers or adds a flagged pack.

6. `find_vfx` (future remote tool, after scan data lands)
   - title: "Find safe VFX packs"
   - readOnlyHint: true
   - destructiveHint: false
   - idempotentHint: true
   - openWorldHint: false
   - Description, exact, for when it is added: "Find safe,
     scanned Roblox VFX packs by what they are for, for example
     'fire explosion'. Returns only safe packs, with description,
     pinned asset ID and version, and scan date. Never returns
     a flagged pack."
   - Input: required `query`, string.
   - Output: name, description, asset ID, pinned version,
     scan date, tags, use cases. No full pack code.

### Tools to exclude, and why

- `list_recipes` and `get_recipe`: not V1, recipes are not the
  component library. Excluding them is a product decision, not
  a technical limitation. If recipes return to V1 later, they
  would be readOnlyHint true, destructiveHint false, and would
  need their own review pass.

## 3. Privacy policy: exact page to create

File to create in this repo: `docs/privacy.html`
Public URL once published via GitHub Pages:
`https://abdullahridwan.github.io/baseplate/privacy.html`

That URL is the privacy policy URL submitted to the portal.
Do not submit a placeholder URL. The page must exist and be
public before submission.

Sections, in order, with the exact commitments to state:

1. What Baseplate is: an agent-native library of VFX and sounds
   for Roblox, plus a scanned list of third party VFX packs.
2. What the remote connector collects: nothing that identifies
   a user. Queries are processed in memory to search a public
   index and are not stored. No account, no login, no cookies
   on the MCP endpoint.
3. What the remote connector does not collect: prompts beyond
   the search query itself, project files, project paths, Roblox
   account details, or personal data. The local add tools run
   on the user's own machine and never send project files to
   the remote server.
4. Logs: host standard access logs only, 30 day retention,
   aggregate counts only (total calls per day, per tool, error
   rate). No per-user or per-project tracking, no search term
   logging, no use for training.
5. Third parties: the registry index is fetched from GitHub
   Pages, which is public. The hosting provider (Fly.io or the
   chosen equivalent) processes requests to run the server and
   is subject to its own privacy policy, linked from the page.
   No other third party receives MCP data.
6. Cookies and tracking: none on the MCP endpoint. The website
   itself uses cookieless aggregate counts only, per the V1 KPI
   decision, no session replay, no fingerprinting.
7. Children's data: no data is collected from children, because
   no data is collected that identifies any user.
8. Changes: any change to this policy will be posted here with
   a new effective date. The effective date must be set on the
   day the page is first published, not backdated.
9. Contact: support contact, to be provided by the owner. Do
   not invent an email address in the page. The page must not
   be published with a fake contact. The owner must supply a
   real support contact before submission, and that contact
   is also the support contact submitted to the portal.

## 4. Documentation URL: exact page to create

File to create in this repo: `docs/connectors.html`
Public URL: `https://abdullahridwan.github.io/baseplate/connectors.html`

That URL is the documentation URL submitted to the portal.
It must exist, be public, and answer a reviewer in under 2
minutes. Sections, in order:

1. What Baseplate does, in one paragraph: agents search VFX
   and sounds by description in text, not thumbnails, and add
   only safe, pinned components to a Roblox project.
2. How to add it in Claude Desktop Settings:
   - Directory route, once listed: Settings > Connectors >
     search "Baseplate" > Connect.
   - Custom connector route, before listing: Settings >
     Connectors > Add custom connector > paste the remote
     `/mcp` URL > Connect, no sign in.
   - Local route: Settings > Extensions > drag the DXT file,
     or Settings > Developer > Local MCP servers > Edit Config
     with the `npx -y baseplate-cli mcp` entry.
3. Tool list, with the exact titles from section 2, and which
   tools are remote (list, search, get details) and which are
   local only (add component, add safe VFX pack).
4. Example queries and expected results, to be verified
   against the live registry before publishing the page:
   - "coin" -> coin_pickup, gem_pickup, and other Rewards items
   - "win" -> level_up, confetti, and other Rewards items
   - "damage" -> hit, crit_hit, and other Combat items
   - "button click" -> ui_click and other UI sounds
   Do not publish example results without running them against
   the live index first. If a result differs, update the page,
   do not leave a wrong example in.
5. What it does not do: it does not write to your project
   from the remote server, it does not upload your game, it
   does not need your Roblox login, and it does not return
   flagged VFX packs.
6. Privacy and support links: link to `privacy.html`, and to
   the support contact once supplied by the owner.
7. Troubleshooting, 3 items only: server not listed (restart
   Claude Desktop, check `/mcp`), no matches (try a broader
   description, then `list_components`), add does not work
   remotely (use the local plugin or Desktop Extension, remote
   is read only by design).

## 5. Icon: exact asset to create

- File: `docs/icon.png`, 512 by 512 pixels, PNG, transparent
  background if possible, otherwise solid white.
- Design: Baseplate blue `#1F4BFF` as the main color, matching
  the site hero accent. Simple mark, readable at 32 pixels:
  a bold "B" or a bolt, no text smaller than the mark itself,
  no Roblox logo, no Claude logo, no third party trademark.
- Public URL for the portal: 
  `https://abdullahridwan.github.io/baseplate/icon.png`
  The portal needs a custom URL if the host has no favicon,
  and this URL must be live before submission. Do not submit
  a local file path.
- Source: create from the brand assets in `brand/` in this
  repo if a usable mark exists there, otherwise design a new
  simple mark in that blue and record the source file in this
  plan. Do not copy an icon from another product.

## 6. Plugin pairing: exact files already in this repo

- Claude Code plugin, already pushed: 
  `.claude-plugin/marketplace.json`,
  `plugins/baseplate/.claude-plugin/plugin.json`,
  `plugins/baseplate/.mcp.json` (currently `npx -y baseplate-cli
  mcp`, local stdio).
- Desktop Extension, already pushed:
  `desktop-extension/manifest.json`,
  `desktop-extension/server/index.js`,
  `desktop-extension/server/lib/`.
- Portal pairing step: when submitting the remote server,
  select "pair with plugin" and point to the Claude Code plugin
  above. The plugin's `.mcp.json` must be updated at that point
  to use the remote connector for discovery if the portal
  requires a `type: http` entry with no headers, instead of
  the current stdio entry. Do not change the plugin's stdio
  entry until the portal asks for it, because the stdio entry
  is what makes local add work today.
- After directory approval, update the site Connect section
  (`docs/index.html`) to list, in order: 1) Directory (Settings
  > Connectors, search Baseplate), 2) Claude Code plugin, 3)
  Desktop Extension, 4) Manual local MCP config. Do not remove
  the manual config, because it is the fallback if the
  directory listing is ever removed.

## 7. Testing, in order, before portal submission

Do not open the portal until every item below passes.

1. Local MCP test, already done for the local server, repeat
   for the remote code: `initialize`, `tools/list`, then
   `tools/call` for each of the 3 remote tools.
2. MCP Inspector test: run the remote server locally, connect
   with MCP Inspector, confirm tools/list shows exactly the
   3 remote tools, with the titles and hints from section 2,
   and no add tools, no recipe tools.
3. Custom connector test in Claude Desktop: Settings >
   Connectors > Add custom connector, paste the final `/mcp`
   URL, no sign in, then in a chat call each tool:
   - `list_components` -> returns a list, no error
   - `search_components` with "coin" -> returns coin items
   - `get_component` with "coin_pickup" -> returns metadata,
     no full source, no error
   - Confirm the portal's Test & launch step can be answered
     "yes, tested in Claude as a custom connector" truthfully.
4. Health and HTTPS test: `GET /health` returns 200,
   `POST /mcp` over HTTPS works from a different network,
   not just localhost, rate limiting returns 429 after the
   limit, not a crash.
5. Docs and privacy test: open `connectors.html` and
   `privacy.html` from a private browser window, no login,
   confirm both load, icon loads, and example queries match
   the live registry.
6. No auth test: confirm no OAuth redirect, no API key prompt,
   and no test account is needed for any of the 3 tools.

## 8. Portal submission, exact steps

1. Confirm account access: the submitter must have a paid
   Claude plan and access to the developer portal / org
   settings where submissions live. If the current account
   does not have that access, the owner must grant it or
   submit personally. Do not submit from an account without
   that access and hope it works.
2. Open the developer portal, select Submit new, choose
   MCP connector.
3. Enter, exact:
   - Name: Baseplate
   - Description: Agent-native VFX and sounds for Roblox.
     Search components by description and add them safely.
     (Keep under the portal's character limit, trim the
     second sentence first if needed, never trim the name.)
   - Server URL: the final `/mcp` URL from section 1.2,
     HTTPS only.
   - Authentication: No authentication.
   - Documentation URL: the `connectors.html` URL from
     section 4.
   - Privacy policy URL: the `privacy.html` URL from
     section 3.
   - Support contact: owner supplied, real, not invented.
   - Icon: the `icon.png` URL from section 5.
4. Let the portal read the tools. Check every tool for:
   title present, readOnlyHint or destructiveHint present,
   and no missing annotation flags. Fix in code and redeploy
   if any flag is missing, then reconnect in the portal so
   it re-reads the tools.
5. Test & launch step: confirm each tool was tested as a
   custom connector (section 7, step 3), and confirm the
   docs and privacy pages are live.
6. Submit. Record the submission ID and date in this plan
   when it exists. Do not record a submission ID before it
   exists.
7. Respond to review: if reviewers flag a tool, a description,
   or a data handling statement, fix that exact item, redeploy,
   reconnect in the portal, and reply with what changed.
   Do not resubmit a new listing for the same server, because
   duplicate submissions for the same server can be rejected.
8. After approval: update the site Connect section as in
   section 6, announce the directory listing, and add the
   connector to the V1 KPI tracking: directory installs and
   remote tool calls, aggregate only, no per-user tracking.

## 9. Gating items: do not submit until these are done

- [ ] Remote server built, deployed, and tested as a custom
      connector (sections 1 and 7)
- [ ] Tool titles and hints implemented in code, verified
      via MCP Inspector (section 2)
- [ ] `privacy.html` published, with a real support contact
      supplied by the owner (section 3)
- [ ] `connectors.html` published, with example queries
      verified against the live registry (section 4)
- [ ] `icon.png` published at 512 by 512, Baseplate blue,
      no third party trademark (section 5)
- [ ] Final `/mcp` URL fixed, HTTPS, always on, health check
      passing (section 1.2)
- [ ] Submitter has paid plan and portal access confirmed
      (section 8, step 1)
- [ ] `find_vfx` decision recorded: either scan data has
      landed and `find_vfx` is added as a connector update,
      or it stays out of the first submission. Do not submit
      it empty.
- [ ] Local add path still works: Claude Code plugin and
      Desktop Extension tested after any plugin pairing change
      (section 6)

## 10. What this plan does not change

- It does not change the local MCP server's core search logic.
  It reuses it, with a metadata only change for remote
  `get_component`.
- It does not change V1 scope. V1 is still the component
  library only, recipes are not V1, and the remote connector
  is 3 tools, not 8, for that reason.
- It does not add per-user tracking, phone-home telemetry,
  or search term logging, per the V1 KPI decision.
- It does not require npm publish for the remote connector
  itself, because the remote server is hosted, not fetched
  via npx. Npm publish is still required for the Claude Code
  plugin's current stdio entry, and for the manual local
  config, but not for the directory connector.
- It does not invent a domain, an email, an icon, a test
  account, or a submission ID. Every one of those must be
  supplied or created and verified before submission, and
  this plan names exactly where each one goes.
