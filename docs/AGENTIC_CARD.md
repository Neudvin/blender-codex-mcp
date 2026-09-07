# Agentic Card prototype

This experimental profile lets Codex create and edit the L’Arbre-style layered
business-card concept through eleven typed MCP tools. Blender constructs the
geometry, checks text layout, and manages recipe revisions. The model sends small
parameter changes instead of generating a Blender Python program for each edit.

This is the first benchmark toward the broader agentic Blender design brief.
It is not yet a general-purpose replacement for Blender's modeling, sculpting,
rigging, animation, or node editors. Token savings have **not** been measured.

## Install on your Windows machine

Use a separate checkout so your current setup at
`C:\Users\neudv\blender-codex-mcp` remains available. These PowerShell commands
assume Git and uv are already installed:

```powershell
git clone --branch codex/typed-card-prototype https://github.com/Neudvin/blender-codex-mcp.git C:\Users\neudv\blender-agentic-mcp
Set-Location C:\Users\neudv\blender-agentic-mcp
uv run python scripts/build_agentic_addon.py
```

1. In Blender 4.5 LTS, open **Edit > Preferences > Add-ons > Install from Disk**.
2. Select `C:\Users\neudv\blender-agentic-mcp\dist\blender_agentic_mcp.zip` and
   enable **Blender Agentic Card MCP**.
3. In the 3D Viewport press **N**, open **Agentic Card**, and click **Start MCP**.
4. Add the following separate entry to your Codex configuration at
   `C:\Users\neudv\.codex\config.toml`. Keep your other configuration entries.

```toml
[mcp_servers.blender_agentic]
command = "uv"
args = ["--directory", "C:/Users/neudv/blender-agentic-mcp", "run", "blender-agentic-mcp"]
tool_timeout_sec = 240
```

Restart the local Codex app/CLI session and check that the `card_status` tool
connects. For this benchmark, enable only this Blender profile in the session;
exposing the existing raw-code tool set would change both the behavior and the
token comparison. Continue to use your existing project directory
`C:\Users\neudv\Documents\ChatGPT\Bee_Card`; the prototype does not depend on
that folder's name.

The MCP process and Blender must run as the same local user on the same machine.
Default bridge port: **9877**. If you change it in add-on preferences, set the same
value under `[mcp_servers.blender_agentic.env]` as `BLENDER_AGENTIC_PORT = "9878"`.
The add-on stops when a `.blend` file is loaded; click **Start MCP** again after
opening a file. This also gives the bridge a new session epoch.

Generated files default to `C:\Users\neudv\BlenderAgenticMCP`; the folder can be
changed in add-on preferences. Card exports and previews never overwrite an existing artifact.
Normal project saves update the current `.blend` and keep a native Blender backup. Preview images accumulate in
this folder and can be deleted when no longer needed.

If the separate checkout already exists, inspect its local changes before
updating it; do not repeat the clone command or discard work.

## First conversation

Select **GPT-5** in your existing Codex environment for the intended benchmark.
The bridge does not choose the model or require an OpenAI API key.

> Check the Blender card connection. Create an 85 by 55 mm business card inspired
> by our reference: dark wood veneer over a gold core, gold perimeter and exposed
> diagonal corner. Put YOUR NAME on the front. Use placeholder contact
> details on the back. Show the front and back.

> Change only the email to HELLO@EXAMPLE.COM. Keep its size, spacing and position.

> Make the exposed diagonal corner 10 mm. Then restore only that corner to its
> original size, preserving my email edit.

> Save this current project as working_card.blend. For later edits, keep saving
> that same project; do not create another card or export a separate copy.

Text uses Blender's built-in font unless you provide a local `.ttf` or `.otf`
path. For a closer serif appearance, tell Codex to set `font_path` to an existing
serif font on your computer. This repository does not bundle fonts or the actual
L’Arbre logo. The generated tree is an original branching-line approximation.
Custom font files remain external dependencies; keep them available at their
recorded paths when reopening or regenerating a card.

The [example recipe](../examples/agentic_larbre_card.json) includes placeholder
contact details and example text sizes/positions. Ask Codex to read that file and
use it as the `card_create` spec, then supply your real content in your local
conversation. Dimensions and materials remain approximations.

The following previews show the default placeholder card after an email edit.
They were rendered by this runtime in Blender 4.5.3 with the built-in substitute
font; they are actual model renders.

![Generated front](agentic_card/front.png)
![Generated back](agentic_card/back.png)

## Updating from v0.1: one project throughout the conversation

v0.1 called its card-only export `card_save`. That name encouraged repeated new
files. In **v0.2**, `card_save` performs a normal whole-project Blender save;
`card_export` is the separate-copy operation. Both the server and installed
add-on must be updated together; wire protocol 2 prevents an old client from
silently using the new save semantics.

In the separate checkout, inspect `git status` for local modifications, then
update the `codex/typed-card-prototype` branch without discarding your work.
For a clean checkout:

```powershell
Set-Location C:\Users\neudv\blender-agentic-mcp
git pull --ff-only
uv run python scripts/build_agentic_addon.py
```

Stop the bridge and reinstall/enable the rebuilt ZIP in Blender, then restart
Blender and Codex. The connection should report version `0.3.0`. Tests use
Blender 3.6.23 and 4.5.3 LTS; Blender 3.6.2 is expected to work for this narrow workflow.

The intended sequence is:

1. `card_status` identifies `project.filepath`, the active scene, and card refs.
2. `card_update` changes that card's veneer/core values; it retains the asset ref.
3. `card_text_set` changes `rotation_deg` on the same text id (degrees in its face's
   plane), preserving its other properties. Rotated text must still fit.
4. If the starting file already contains an unmanaged card, call `card_inspect`
   with no ref, then `card_adopt` with the exact four mesh names and optional
   FONT names. Adoption preserves native meshes/materials and assigns a stable
   asset reference; later text, veneer, core, recess and save edits stay in the
   same project.
5. `card_save(expected_filepath=...)` saves all project contents in the **same**
   running Blender instance. Copy the exact filepath from status. Only an unsaved
   project (`filepath == ""`) accepts a new simple filename under the output folder.

Saves retain at least one native `.blend1` backup of the previous on-disk project.
These backup files are expected; they are not separate working designs.
`PROJECT_MISMATCH` refuses a wrong live project, and `PROJECT_DISK_CONFLICT`
refuses a disk file changed since this bridge began observing it or this Blender
instance last saved it. Disk detection uses file metadata, not a durable merge
journal. Loading a file stops the bridge; restart it after reconciling changes.

Do not treat an MCP connection failure as evidence that Blender is busy.
`NOT_CONNECTED` means no request could be sent; check the intended Blender window
and Start MCP. `OUTCOME_UNKNOWN` means a request may have been sent, so inspect
before retrying a mutation. Neither response authorizes switching to a background
Blender process and editing a different copy.

Existing v0.1 files are preserved. The duplicate guard does not delete earlier
cards. Old generated recipes support the new rotation field with a default of
zero. Recessed recipes are supported directly with `construction="recessed"`,
`veneer_mm`, and `recess_mm`. Existing native recessed models are adopted
explicitly by `card_adopt`; the model should discover names with `card_inspect`
instead of rebuilding a second card. Native profile topology and materials are
preserved during typed dimension/text edits.

## Tool contract

| Tool | Purpose |
| --- | --- |
| `card_status` | Connection, Blender version, session epoch, cards and output folder |
| `card_inspect` | Recipe and semantic components, or paginated scene objects |
| `card_create` | Construct a new card; refuse accidental duplicates when a card already exists |
| `card_adopt` | Adopt existing native body/veneer/web meshes and optional text objects |
| `card_update` | Change named dimensions, materials, grain or font |
| `card_text_set` | Edit text, size, position or `rotation_deg`, preserving omitted properties |
| `card_history` | List the last 32 recipe revisions |
| `card_restore` | Restore a recipe or selected top-level parameters as a new revision |
| `card_preview` | Render front, back, edge or perspective; return image and path |
| `card_save` | Save the complete current project at its existing path; filename required only for its first save |
| `card_export` | Explicitly export a separate card-only copy; live project/save target unchanged |

Dimensions are **millimetres**; raw scene inspection reports locations in metres.
Default assumptions are 85 × 55 mm, 0.8 mm core, 0.3 mm veneer per face,
0.8 mm border, 12 mm diagonal and 0.08 mm bevel. These are prototype choices,
not dimensions measured from the photograph. Colors are linear RGB in [0, 1].
Text coordinates are face-relative: positive x is right when viewing that face,
positive y is up. Both veneers expose the same physical corner, which appears at
the lower right on the front and lower left on the back.

Use the returned `asset_ref` and current `revision` for each edit. Semantic
component refs such as `card:.../text:email` survive regeneration; Blender object
identities and names may change. This version rebuilds its owned collection on
each accepted mutation. It leaves unrelated scene objects alone, and refuses
known external dependencies or detected manual changes to generated content.

Each mutation needs a unique `request_id` containing 1–64 letters, digits,
underscores or hyphens. Retrying an uncertain request must reuse **both** its id
and exact arguments. A reused id with different arguments is an error. A replay
returns its original result plus `current_revision`; inspect before the next edit.
The scene-local replay ledger retains up to 256 accepted mutations per card,
then fails explicitly. It persists only in saved `.blend` data: reverting to an
older file also reverts its history/ledger. There is no disk-backed crash journal.

Errors include `TEXT_OVERFLOW`, `TEXT_OVERLAP`, `STALE_REVISION`,
`MANUAL_EDIT_CONFLICT`, `EXTERNAL_DEPENDENCY`, `IDEMPOTENCY_CONFLICT`,
`FILE_EXISTS` and `OUTCOME_UNKNOWN`. Text is never silently shrunk or repositioned.
Layout is validated from Blender-evaluated text bounds in a staging scene before
the live collection is replaced. If a transport timeout occurs, Blender may still
be working: inspect before retrying with the same request id. Saving is a separate
file operation, not part of recipe undo.

## Limits that matter

- Recipe edits require Object Mode. Keep generated cards at their recipe origin;
  duplicate them before incorporating them into a manually edited composition.
  Fingerprints cover common supported properties, not every possible Blender
  edit. Preserve manually customized work through Blender's normal save workflow.
- A `card_export` artifact contains the card scene and native text/mesh/material data,
  not your surrounding project or a custom workspace. Blender may report that
  it is opening a library file and construct a default workspace; the integration
  test verifies that the card scene and revision data can still be opened/edited.
- Text fit and overlap are tested. Self-intersection, typography equivalence,
  fabrication tolerances, gold plating, print output and exact logo matching are
  not certified. Text size means Blender font size, not measured cap height.
- There is no arbitrary code execution or network asset fetching in this profile.
  It uses a bounded 1 MiB framed JSON protocol on `127.0.0.1`, a local shared
  random token, and a main-thread socket pump. This is a local-user trust boundary,
  not isolation against other processes running as the same user.
- Rendering and file operations are synchronous and can briefly block Blender's
  UI. Previews use fixed cameras, CPU Cycles, 16 samples and denoising, at
  128–1024 pixels. Async jobs/cancellation and durable recovery remain future work.
- The existing profile's source remains available. The shared MCP dependency is
  raised to 1.29.x-compatible APIs and locked at 1.29.1; the legacy profile itself
  has not been regression-tested with the updated dependency set.

## Verification and benchmark

**22 Python/MCP tests passed**, plus the Blender render/save/reopen integration
script and a serif-font reference render. Checks ran on Linux with official
**Blender 4.5.3 LTS** and Python
3.12 / MCP 1.29.1. Windows GUI behavior and Blender 5.2 remain unverified.

```bash
PYTHONPATH=src python -m pytest -q tests/test_agentic.py
BLENDER_BIN=/path/to/blender PYTHONPATH=src python -m pytest -q tests/test_stdio_blender.py
AGENTIC_TEST_RENDER=1 /path/to/blender --background --factory-startup --python-exit-code 1 --python tests/blender_integration.py
```

The first command covers contracts, watertight prism topology, malformed and
fragmented frames, authenticated sockets, structured MCP errors and reproducible
ZIP packaging. The second launches the **packaged** add-on and a real MCP STDIO
client/server: initialize → discover → create → text edit → save → veneer edit → save same file → stale-edit
rejection, including an image response and clean add-on shutdown. The third exercises Blender text
layout, failed-edit preservation, pagination beyond ten objects, idempotent
replay, selective restore, manual/external dependency refusal, four previews,
preservation of unrelated objects, duplicate-create refusal, typed rotation,
whole-project save/reopen, external disk-change refusal, and separate export/reopen
with persisted history.

For a developer example render, run Blender with
`--background --factory-startup --python-exit-code 1 --python scripts/render_agentic_example.py`.
Optionally set `AGENTIC_EXAMPLE_FONT` to a local serif font. This writes a manifest,
three previews and an editable card under `test-output`; it does not run a model.

For the GPT-5 benchmark, run the same user prompt sequence against the existing
bridge and this profile, starting from a fresh scene/session each time. Record
total input/output tokens **including tool schemas, returned images and retries**,
elapsed time, tool calls, corrections, and whether the reopened card matches the
intended edits. Use identical image resolutions and comparable output quality;
run several trials. A successful scripted integration test does not establish
conversational reliability or lower model token usage.

Next gates: complete that Windows/GPT-5 benchmark; then add durable transactions
and jobs, stronger generic references/validation, and additional typed modeling
recipes based on observed failures. Expand the general Blender API only after
the narrow workflow's quality and token measurements are repeatable.

Reference documentation: [Codex MCP](https://developers.openai.com/codex/mcp/),
[Blender timers](https://docs.blender.org/api/current/bpy.app.timers.html),
[Blender data libraries](https://docs.blender.org/api/current/bpy.types.BlendDataLibraries.html).
