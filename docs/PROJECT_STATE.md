# Project State

> Living handoff for Codex sessions. Read this file before working. Do not put
> secrets or raw credential-bearing values here.

Last updated: `2026-09-02T21:10:42+01:00`
Status: `IN_PROGRESS`
Active objective: Add the real Sibyl journal adapter, filmable CLI, blocked-only demo scripts, subprocess CLI tests, and exact README commands while preserving the frozen core.

## Workspace

- Repository: local Git repository; no remote configured yet
- Worktree: `/home/rouma/rightsrelay`
- Branch: `main`
- Commit: `16e49d3` (`docs: record frozen core checkpoint`)
- Protected releases/artifacts: `src/rightsrelay/gate.py`, `src/rightsrelay/models.py`, and existing MemoryClient call shapes are frozen unless an existing test turns red; partner integrations and UI are out of scope

## Constraints

- Sibyl Memory must be load-bearing; export fails closed when memory is absent or unreadable.
- The LLM never decides or mutates authorization fields.
- One WARM source-of-truth entity: tenant `rightsrelay`, kind `UseAuthorization`, name `campaign-aurora:neon-drive`.
- Do not store conversations or implement mock ACP/x402 integrations.
- Release operations only; never claim legal advice or third-party platform integrations.
- No secrets in Git.

## Current Context

- This turn is restricted to `journal.py`, CLI/entrypoint, two blocked-only demo scripts, the recording shot list, two new test files, and README updates.
- GitHub CLI authentication currently reports invalid and no remote exists. Pushing or creating a remote is explicitly forbidden this turn.
- `sibyl-memory-client` was not installed globally when work started.
- The official Sibyl repository documents local-first, unactivated SDK operation and WARM uniqueness by `(tenant_id, category, name)`.
- User-confirmed test seams are `can_release`, fail-closed export, and cross-process Sibyl persistence.

## Work Completed

- Inspected the installed SDK source: `write_event` is keyword-only over `evaluated`, `acted`, `forward`, `extra`, and `ts`; `read_events` exists and returns decoded event dictionaries.
- Added `src/rightsrelay/journal.py`, mapping authorization event/status/reasons into the four Sibyl journal payloads and placing entity name, status, reasons, and present partner identifiers in `extra`.
- Added a real temporary-database journal test that writes through `write_event` and verifies the decoded `read_events` result.
- Created the repository and required source/test/script directories.
- Added MIT licensing, Python package metadata, and isolated development dependencies.
- Installed and inspected `sibyl-memory-client==0.8.0`; confirmed `MemoryClient.local`, `set_entity`, and `get_entity` signatures from the installed source.
- Added the requested 20-line scratch script and proved a real SQLite-backed entity round-trip under tenant `rightsrelay`; `get_entity` returns an envelope whose `body` contains the authorization JSON.
- Implemented strict Pydantic models and the pure deterministic `can_release` gate with status, campaign, asset, channel, paid-media, territory, and inclusive date-window checks.
- Added gate tests for the frozen acceptance matrix and identity mismatch fail-closed behavior.
- Created local checkpoint commit `7d36485`; no push was attempted because no remote is configured.
- Added `AuthorizationMemory`, which uses the actual SDK envelope shape and fixed tenant/category/name to persist and recall the one WARM authorization while storing the current attempt in HOT state.
- Added `build_release_packet`; callers cannot supply an authorization, every export recalls Sibyl memory, invokes `can_release`, returns a 409-compatible refusal when blocked, and writes no output when memory is unavailable.
- Added the deletion test and a real two-process persistence test. The second process recalls the limited grant, observes BLOCKED, rewrites the same entity, and observes CLEARED.
- Expanded the README with exact current write/read/gate/export line references, load-bearing explanation, honest partner-stack status, and prior-work declaration.
- Created local checkpoint commit `cc5d7c1` for the load-bearing memory/export implementation; no push was possible because no remote is configured.

## Verification

| Check | Result | Evidence/date |
| --- | --- | --- |
| Git repository | passed | `git init -b main`, 2026-09-02 |
| GitHub remote | blocked | No remote configured; do not publish an incomplete repository without explicit scope |
| Sibyl SDK round-trip | passed | `.venv/bin/python scripts/scratch_memory_roundtrip.py <temp-db>` preserved row ID and body, 2026-09-02 |
| Gate tests | passed | `.venv/bin/pytest tests/test_gate.py -q` → `7 passed`, 2026-09-02 |
| Deletion/export tests | passed | `.venv/bin/pytest tests/test_deletion.py -q` → `3 passed`; authorized output, 409 refusal, and removed MemoryClient fail-closed behavior, 2026-09-02 |
| Fresh-session test | passed | `.venv/bin/pytest tests/test_fresh_session.py -q` → `1 passed`; distinct PIDs and persisted policy transition, 2026-09-02 |
| Full suite | passed | `.venv/bin/pytest -q` → `11 passed in 1.00s`, 2026-09-02 |
| Python compilation | passed | `.venv/bin/python -m compileall -q src tests scripts`, 2026-09-02 |
| Diff hygiene | passed | `git diff --check`; generated `__pycache__` directories removed, 2026-09-02 |
| Journal adapter | passed | `.venv/bin/pytest tests/test_journal.py -q` → `1 passed`; exact decoded event mapping verified, 2026-09-02 |

## Risks And Blockers

- Published SDK signatures may differ from the prompt; installed package inspection is authoritative.
- No Git remote is configured, so checkpoints can be committed locally but not pushed.
- README file:line references are exact for this checkpoint and must be updated if `memory.py`, `gate.py`, or `export.py` shifts.
- COLD journal helpers, REFERENCE storage, UI/CLI, demo scripts, ACP, and x402 are deliberately not implemented in this stopped checkpoint.

## Next Actions

1. Implement the CLI and module entrypoint against the frozen core and journal adapter.
2. Add the subprocess CLI lifecycle test, blocked-only demo scripts, and recording shot list.
3. Update exact README commands and journal line citation; stop after the full suite is green.

## Session Handoff

- Start with this file and `git status --short --branch`.
- Frozen core command: `.venv/bin/pytest -q`.
- Inspect `src/rightsrelay/memory.py`, `gate.py`, `export.py`, and the three required test files first.
- Do not begin UI, ACP, or x402 implementation without a new authorized continuation.

## Change Log

| Timestamp | Session/agent | Event | Result |
| --- | --- | --- | --- |
| 2026-09-02T18:25:00+01:00 | Codex | Initialized RightsRelay repository | Frozen core implementation in progress; remote not configured |
| 2026-09-02T20:44:12+01:00 | Codex | Completed SDK proof and deterministic gate checkpoint | Real Sibyl round-trip passed; 7 gate tests passed |
| 2026-09-02T20:49:06+01:00 | Codex | Completed frozen memory/export checkpoint | Commit `cc5d7c1`; 11 tests passed; deletion and real fresh-process requirements verified; partner stacks remain unclaimed |
| 2026-09-02T21:00:00+01:00 | Codex | Started journal and CLI checkpoint | Frozen core protected; no remote/push; journal and CLI test seams confirmed |
| 2026-09-02T21:10:42+01:00 | Codex | Completed real Sibyl journal adapter | `write_event` mapping verified through `read_events`; journal test passed |
