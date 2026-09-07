# AGENTS.md

## Purpose
This project uses a lightweight project operating protocol so humans and AI agents can work from durable project state rather than conversational memory.

## Required Startup
Before acting, read:
1. `PROJECT.md`
2. `CURRENT_STATE.md`
3. The relevant item in `WORK_QUEUE.md`
4. Any referenced entries in `DECISIONS.md`
5. Any referenced criteria in `ACCEPTANCE_TESTS.md`
6. Any domain-specific files named by the task

Do not reopen settled decisions unless new evidence materially contradicts them.

## Operating Model
Use the least-expensive capable executor:

- **CHAT** — reasoning, research, architecture, planning, diagnosis, specifications, critique
- **CODEX** — repository inspection, implementation, refactoring, tests, code changes
- **WORK** — browser/app operation, multi-system execution, file/app workflows, external actions
- **AUTOMATION** — repeated or future monitoring/delivery
- **HUMAN** — physical actions, subjective approval, inaccessible systems, consequential judgment

Default pattern:

`Think → Record State → Execute → Verify → Update State`

## Source of Truth
Conversation history is not authoritative project state.

Project files are authoritative according to the Knowledge Map in `PROJECT.md`.

Do not duplicate durable information across files. Link or reference the authoritative location instead.

## Task Handoff
Before finishing meaningful work:
1. Update the relevant task status in `WORK_QUEUE.md`.
2. Update `CURRENT_STATE.md` if reality changed.
3. Record a decision in `DECISIONS.md` if a meaningful choice was made.
4. Update acceptance results if verification occurred.
5. Record new durable knowledge in the appropriate domain file.
6. Propose a new domain file if repeated knowledge no longer fits the base files cleanly.

## Structural Adaptation
The five core project-state files remain conceptually stable:
- `PROJECT.md`
- `CURRENT_STATE.md`
- `DECISIONS.md`
- `WORK_QUEUE.md`
- `ACCEPTANCE_TESTS.md`

Additional domain files should emerge only when justified by repeated or growing durable knowledge.

Markdown is the default portable representation, not a permanent storage requirement.
