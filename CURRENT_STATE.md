# Current State

## Snapshot
- **Last updated:** 2026-09-06
- **Current phase:** Authoritative repository relocated; runtime cutover and functional verification complete.
- **Overall status:** On Track

## Working
- The authoritative reusable repository moved intact to the Organization project location; the full pre-move manifest verified every original file.
- Git checkpoint `5e455f2797f71a9d9f30f72897e4c0d147f594f7` is preserved on `migration-recovery/2026-09-06-blender-agentic-mcp-relocation`.
- The global Codex entry named `blender_agentic` resolves the canonical checkout path.
- The locked environment now installs the project from the relocated checkout; the add-on ZIP was rebuilt and installed in Blender 3.6.
- The exact relocated MCP command connected to the installed Blender bridge and returned a successful headless `card_status` with 11 tools.
- Bee Card remains a consumer and its embedded Blender MCP repository remains unchanged.

## Not Working / Known Issues
- The local working branch is ahead by two commits and behind by one newer primary-branch remote commit. Do not rebase or merge without deliberate code reconciliation.
- No persistent Blender bridge is intentionally left running after verification; start the add-on bridge in an actual Blender session before production use.

## Current Blockers
- None.

## Active Risks / Unknowns
- The global Codex configuration necessarily uses an absolute path for this runtime entry.
- A deliberate Git reconciliation is required before further feature work on the primary branch.

## Immediate Next Action
Deliberately reconcile the overlapping recovery checkpoint with the newer remote primary-branch commit before further feature work.

## Current Milestone
Authoritative migration complete; Git reconciliation pending.

## Relevant References
- `DECISIONS.md#D-001`
- `DECISIONS.md#D-002`
- `DECISIONS.md#D-003`
- `WORK_QUEUE.md#WQ-003`
- `ACCEPTANCE_TESTS.md#AT-005`

## Recent Material State Changes
- 2026-09-06 — Repository moved from `C:\Users\neudv\blender-agentic-mcp` after full file and Git verification.
- 2026-09-06 — Recovery checkpoint pushed without reconciling the newer remote primary-branch commit.
- 2026-09-06 — Locked environment repaired, add-on ZIP rebuilt and installed in Blender 3.6, and the exact relocated MCP command verified against the installed headless bridge.