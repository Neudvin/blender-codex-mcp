# PROJECT.md

# Project: Blender Agentic MCP

## 1. Purpose
**Objective:** Build and maintain the authoritative reusable Blender MCP infrastructure that lets Codex operate a live Blender session through a local bridge, including the typed Agentic Card profile.

**Desired outcome:** A tested, location-stable MCP server and Blender add-on that future projects can consume without copying this repository.

## 2. Scope

### In Scope
- The reusable Blender Codex MCP server, Blender add-ons, typed Agentic Card tools, tests, documentation, and release artifacts.
- The authoritative checkout at the repository path listed in Project Metadata.
- The global Codex entry named `blender_agentic` that starts this repository.

### Out of Scope
- Bee Card's embedded `blender-codex-mcp` repository; it remains an intact project-local dependency/history branch pending deliberate reconciliation.
- Bee Card assets and generated output under `C:\Users\neudv\BlenderAgenticMCP`.
- Automatic reconciliation of the primary branch with newer upstream commits.

## 3. Constraints
- Preserve Git history and never discard uncommitted work.
- Use one authoritative reusable MCP checkout; consumers should depend on it rather than copy it unless an intentional fork is approved.
- The Codex global runtime entry requires an absolute checkout path; repository documentation should avoid unnecessary machine-specific paths.
- Blender and Codex must run under the same local user for the live socket bridge.

## 4. Operating Model
This project follows `Think → Record State → Execute → Verify → Update State` using the least-expensive capable executor described in `AGENTS.md`.

## 5. Project Structure

### Core Files
- `AGENTS.md` — startup and handoff rules.
- `PROJECT.md` — stable charter and knowledge map.
- `CURRENT_STATE.md` — current migration, Git, runtime, and verification state.
- `DECISIONS.md` — durable authority and relocation decisions.
- `WORK_QUEUE.md` — bounded next work.
- `ACCEPTANCE_TESTS.md` — evidence for migration and runtime acceptance.

### Domain Files

| Domain | Authoritative File | Status |
|---|---|---|
| General MCP/server setup | `README.md` | Active |
| Typed Agentic Card profile and Blender workflow | `docs/AGENTIC_CARD.md` | Active |
| Python implementation | `src/blender_codex_mcp/` | Active |
| Blender add-on | `blender_addon/blender_agentic_mcp/` | Active |
| Tests | `tests/` | Active |

## 6. Knowledge Map

| Knowledge Area | Authority | Notes |
|---|---|---|
| Project charter and authority | `PROJECT.md` | This file |
| Current operational truth | `CURRENT_STATE.md` | Read before runtime or migration work |
| Durable decisions | `DECISIONS.md` | Includes Bee Card boundary and Git recovery |
| Tasks | `WORK_QUEUE.md` | Current queue |
| Acceptance evidence | `ACCEPTANCE_TESTS.md` | Migration and functional checks |
| Setup and usage | `README.md`, `docs/AGENTIC_CARD.md` | Technical instructions |

## 7. Project Metadata
- **Owner:** Mike Sredzinski / Neudvin
- **Created:** 2026-09-06
- **Current phase:** Relocated authoritative checkout; runtime cutover and functional verification in progress.
- **Primary executors:** CODEX, WORK, HUMAN
- **Repository / workspace:** `C:\Organization\30-39 Projects\30 Software & AI Projects\30.06 Blender Agentic MCP\blender-agentic-mcp`
- **GitHub:** `https://github.com/Neudvin/blender-codex-mcp.git`
- **Working branch:** `codex/typed-card-prototype`