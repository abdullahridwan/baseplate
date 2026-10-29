# What gets flagged

A VFX asset is a part with particle emitters, beams, trails and lights. None of that
needs code. So we flag any VFX asset whose contents match a pattern used to run code
you didn't ask for, or to get you to run it yourself.

Every rule below is a mechanical check of the model file, run by a script. One match
makes the asset `flagged`. A flag describes what is inside the file on the date we
scanned it. It is not a finding about who made it or why: accounts get compromised and
assets change hands.

| Rule | What we check | Why it matters |
|---|---|---|
| **M1 Hidden code** | A script uses `require(<number>)`, `loadstring`, `getfenv`/`setfenv`, `string.reverse`, runs of byte escapes like `\104\116\116\112`, a line over 1500 characters, or a 400+ character encoded blob | These pull in or unpack code you can't read before it runs. Effects don't need it. |
| **M2 Reaches outside the game** | A script mentions `InsertService`, `LoadAsset`, `GetObjects`, `HttpService`, `HttpGet`/`HttpPost`/`RequestAsync`, purchase prompts, `TeleportService` or `CoreGui` | Loads more code at runtime, sends data out, charges players, or moves them to another game. |
| **M3 Disguised script** | A script sits inside a ParticleEmitter, Beam, Trail, Attachment, Decal, Texture or mesh | Effects don't need code, and a script there is easy to miss when you look through the model. (Scripts inside lights and sounds don't count: old models commonly put flicker scripts there. They still make the asset `has_scripts`.) |
| **M4 Fake tool window** | The asset has scripts and a GUI with text like "troubleshoot", "command", "paste", "copy", "console", "verify", "fix", "execute", "plugin" or "license" | A window that looks like part of Studio and asks you to copy a command into the Command Bar, which runs it with full access to your place. Without a script the window can't do anything, so it doesn't count. |
| **M5 Listing mismatch** | The store description says "no scripts" but the asset has scripts | The listing tells developers there's nothing to run, so they skip checking. |
| **M6 Scripts plus remotes** | The asset has both scripts and RemoteEvents, RemoteFunctions or Bindables | A VFX asset has nothing to send to the server. Remotes plus scripts give code a channel between clients and the server. |

## Every verdict

| Verdict | Meaning | Listed on Baseplate? |
|---|---|---|
| `safe` | Has effects, no scripts, no remotes | **Yes** |
| `has_scripts` | Has scripts but no rule above fired | No. VFX don't need code, and we don't list code we haven't proven safe |
| `flagged` | At least one rule matched | No, and listed in the report |
| `not_vfx` | No emitters, beams, trails, fire, smoke or sparkles (maps, single decals, spam) | No |
| `error` | Couldn't download or read it | No, retried next run |

## Versions

A verdict is for one version of an asset. We pin each one to the store's `updated`
time, which changes every time the creator publishes. If the time on the store doesn't
match the time we scanned, the asset is unverified until the next weekly run.
