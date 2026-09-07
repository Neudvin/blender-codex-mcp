# Decision Log

## D-001 — Maintain one authoritative reusable Blender MCP repository
- **Status:** ACTIVE
- **Date:** 2026-09-06
- **Owner:** Mike Sredzinski / Neudvin
- **Supersedes:** None
- **Related:** WQ-001, AT-001

### Context
Bee Card originated the Agentic Card work and includes an embedded Blender MCP copy, while the standalone checkout contains newer reusable server, add-on, and test work.

### Decision
Treat this repository as the authoritative reusable Blender MCP infrastructure project. Bee Card remains an originating and current consumer; its embedded copy remains unchanged until a separate reconciliation is approved.

### Rationale
A single authority prevents future projects from creating divergent independent copies.

### Consequences
- Future projects should reference or intentionally fork this repository.
- Bee Card’s embedded repository is not moved or rewritten by this project.

### Evidence
Repository comparison and approved Johnny.Decimal migration hierarchy.

---

## D-002 — Atomic relocation with explicit runtime cutover
- **Status:** ACTIVE
- **Date:** 2026-09-06
- **Owner:** Mike Sredzinski / Neudvin
- **Supersedes:** None
- **Related:** WQ-001, WQ-002, AT-001, AT-002

### Context
The authoritative checkout moved from the user profile root to the canonical Organization hierarchy. Codex had a global MCP entry using the old absolute path.

### Decision
Move the repository atomically, verify a complete manifest before modifying configuration, then update only the `blender_agentic` global Codex entry and the repository’s maintained setup guide.

### Rationale
The project must retain its complete Git history and working state while Codex resolves the single authoritative new path.

### Consequences
- The global runtime entry remains necessarily absolute.
- The virtual environment is treated as reproducible runtime content.

### Evidence
Migration audit in the sibling `_migration` folder.

---

## D-003 — Preserve divergent Git histories pending deliberate reconciliation
- **Status:** ACTIVE
- **Date:** 2026-09-06
- **Owner:** Mike Sredzinski / Neudvin
- **Supersedes:** None
- **Related:** WQ-003

### Context
The remote primary branch advanced one commit while 13 local modified files overlapped it.

### Decision
Commit and push local changes to `migration-recovery/2026-09-06-blender-agentic-mcp-relocation`; do not force rebase, merge, reset, or overwrite during migration.

### Rationale
This preserves both states and separates path migration from code reconciliation.

### Consequences
The local branch remains ahead one / behind one until a deliberate reconciliation is performed.

### Evidence
Checkpoint `5e455f2797f71a9d9f30f72897e4c0d147f594f7` and remote primary commit `bc56b9e0d670bb678da7624c91a02f00aa610261`.

---

## Decision Index

| ID | Title | Status | Date |
|---|---|---|---|
| D-001 | One authoritative reusable repository | ACTIVE | 2026-09-06 |
| D-002 | Atomic relocation and targeted runtime cutover | ACTIVE | 2026-09-06 |
| D-003 | Preserve divergent histories for later reconciliation | ACTIVE | 2026-09-06 |