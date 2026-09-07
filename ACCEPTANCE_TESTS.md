# Acceptance Criteria

## AT-001 — Atomic repository integrity
- **Type:** OBJECTIVE
- **Status:** PASS
- **Related work:** WQ-001
- **Owner:** CODEX
- **Last evaluated:** 2026-09-06

### Requirement
Every pre-move repository file, hash, size, timestamp, Git branch, HEAD, history object, and working-tree state matches after the atomic move.

### Verification Method
Compare the full SHA-256 manifest and Git state before and after movement.

### Result
PASS — 3,102 files / 58,202,117 bytes; zero missing, extra, hash, size, or timestamp differences. Git branch and HEAD matched exactly.

### Evidence / Reference
Sibling `_migration/30.06_Blender_Agentic_MCP_post_move_verification_20260906_234229.json`.

---

## AT-002 — Authoritative runtime path cutover
- **Type:** PROCESS
- **Status:** PASS
- **Related work:** WQ-001
- **Owner:** CODEX
- **Last evaluated:** 2026-09-06

### Requirement
The global Codex `blender_agentic` entry resolves the new authoritative path and Bee Card remains untouched.

### Verification Method
Inspect the targeted configuration entry and verify no Bee Card path or repository is modified.

### Result
PASS — the targeted entry now uses the canonical Organization path; Bee Card remained untouched.

---

## AT-003 — Relocated MCP server startup
- **Type:** OBJECTIVE
- **Status:** PASS
- **Related work:** WQ-002
- **Owner:** CODEX
- **Last evaluated:** 2026-09-06

### Requirement
Codex can start the Blender Agentic MCP from the new checkout.

### Verification Method
Synchronize the environment and perform an MCP stdio initialization from the configured new path.

### Result
PASS — exact `uv --directory … run blender-agentic-mcp` runtime initialized and exposed 11 tools.

---

## AT-004 — Live Blender Agentic Card operation
- **Type:** EXTERNAL
- **Status:** PASS
- **Related work:** WQ-002
- **Owner:** WORK / HUMAN
- **Last evaluated:** 2026-09-06

### Requirement
A running Blender instance with the Agentic Card add-on accepts a representative MCP operation.

### Verification Method
Use `card_status` or another non-mutating representative tool through the relocated MCP runtime and record the result.

### Result
PASS — installed Blender 3.6 add-on bridge started and stopped successfully; exact relocated MCP runtime returned a successful headless `card_status`. The packaged integration test also passed create, edit, preview, save, and update operations in disposable data.

---

## AT-005 — Git reconciliation
- **Type:** PROCESS
- **Status:** NOT_RUN
- **Related work:** WQ-003
- **Owner:** CODEX / HUMAN
- **Last evaluated:** Never

### Requirement
The recovery checkpoint and newer remote primary commit are deliberately reconciled without discarding work.

### Verification Method
Review overlapping diff, resolve with test evidence, and push the approved result.

---

## Acceptance Index

| ID | Criterion | Type | Status |
|---|---|---|---|
| AT-001 | Atomic repository integrity | OBJECTIVE | PASS |
| AT-002 | Authoritative runtime cutover | PROCESS | PASS |
| AT-003 | Relocated MCP startup | OBJECTIVE | PASS |
| AT-004 | Live Blender operation | EXTERNAL | PASS |
| AT-005 | Git reconciliation | PROCESS | NOT_RUN |