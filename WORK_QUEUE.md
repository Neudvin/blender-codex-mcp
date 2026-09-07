# Work Queue

## WQ-001 — Complete authoritative repository relocation
- **Status:** DONE
- **Executor:** CODEX
- **Owner:** Mike Sredzinski / Neudvin
- **Priority:** High
- **Created:** 2026-09-06
- **Depends on:** None
- **Acceptance:** AT-001, AT-002

### Objective
Move the authoritative Blender Agentic MCP repository atomically and preserve its full source and Git state.

### Result
Moved and verified against the complete pre-move manifest; old source path has no residue.

---

## WQ-002 — Restore and verify the relocated runtime
- **Status:** DONE
- **Executor:** CODEX / WORK
- **Owner:** Mike Sredzinski / Neudvin
- **Priority:** High
- **Created:** 2026-09-06
- **Depends on:** WQ-001
- **Acceptance:** AT-003, AT-004

### Objective
Repair the reproducible environment, start the MCP from the new path, and verify an Agentic Card operation against Blender.

### Constraints
- Do not touch Bee Card's embedded MCP repository.
- Do not rebase or merge the divergent primary branch during runtime work.

### Result
Locked environment repaired; ZIP rebuilt; add-on installed and bridge verified in Blender 3.6; exact relocated MCP command connected and returned `card_status` successfully.

---

## WQ-003 — Reconcile the local recovery branch with the newer primary branch
- **Status:** READY
- **Executor:** CODEX / HUMAN
- **Owner:** Mike Sredzinski / Neudvin
- **Priority:** High
- **Created:** 2026-09-06
- **Depends on:** WQ-002
- **Acceptance:** AT-005

### Objective
Deliberately compare and reconcile overlapping changes between the recovery checkpoint and remote primary commit without discarding either state.

---

## Queue Index

| ID | Task | Status | Executor | Priority |
|---|---|---|---|---|
| WQ-001 | Authoritative repository relocation | DONE | CODEX | High |
| WQ-002 | Relocated runtime verification | DONE | CODEX / WORK | High |
| WQ-003 | Git branch reconciliation | READY | CODEX / HUMAN | High |