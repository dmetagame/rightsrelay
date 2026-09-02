# Project State

> Living handoff for Codex sessions. Read this file before working. Do not put
> secrets or raw credential-bearing values here.

Last updated: `2026-09-02T20:44:12+01:00`
Status: `IN_PROGRESS`
Active objective: Implement and verify the frozen Sep 2 RightsRelay core: real Sibyl entity persistence, deterministic release gating, fail-closed export, deletion test, and fresh-process recall.

## Workspace

- Repository: local Git repository; no remote configured yet
- Worktree: `/home/rouma/rightsrelay`
- Branch: `main`
- Commit: unborn branch
- Protected releases/artifacts: none; partner integrations and UI are out of scope for this checkpoint

## Constraints

- Sibyl Memory must be load-bearing; export fails closed when memory is absent or unreadable.
- The LLM never decides or mutates authorization fields.
- One WARM source-of-truth entity: tenant `rightsrelay`, kind `UseAuthorization`, name `campaign-aurora:neon-drive`.
- Do not store conversations or implement mock ACP/x402 integrations.
- Release operations only; never claim legal advice or third-party platform integrations.
- No secrets in Git.

## Current Context

- `sibyl-memory-client` was not installed globally when work started.
- The official Sibyl repository documents local-first, unactivated SDK operation and WARM uniqueness by `(tenant_id, category, name)`.
- User-confirmed test seams are `can_release`, fail-closed export, and cross-process Sibyl persistence.

## Work Completed

- Created the repository and required source/test/script directories.
- Added MIT licensing, Python package metadata, and isolated development dependencies.
- Installed and inspected `sibyl-memory-client==0.8.0`; confirmed `MemoryClient.local`, `set_entity`, and `get_entity` signatures from the installed source.
- Added the requested 20-line scratch script and proved a real SQLite-backed entity round-trip under tenant `rightsrelay`; `get_entity` returns an envelope whose `body` contains the authorization JSON.
- Implemented strict Pydantic models and the pure deterministic `can_release` gate with status, campaign, asset, channel, paid-media, territory, and inclusive date-window checks.
- Added gate tests for the frozen acceptance matrix and identity mismatch fail-closed behavior.

## Verification

| Check | Result | Evidence/date |
| --- | --- | --- |
| Git repository | passed | `git init -b main`, 2026-09-02 |
| GitHub remote | blocked | No remote configured; do not publish an incomplete repository without explicit scope |
| Sibyl SDK round-trip | passed | `.venv/bin/python scripts/scratch_memory_roundtrip.py <temp-db>` preserved row ID and body, 2026-09-02 |
| Gate tests | passed | `.venv/bin/pytest tests/test_gate.py -q` → `7 passed`, 2026-09-02 |
| Deletion test | pending | |
| Fresh-session test | pending | |

## Risks And Blockers

- Published SDK signatures may differ from the prompt; installed package inspection is authoritative.
- No Git remote is configured, so checkpoints can be committed locally but not pushed.

## Next Actions

1. Implement the Sibyl-backed authorization wrapper and fail-closed export boundary in red-green slices.
2. Add the MemoryClient deletion test and verify no packet is written.
3. Add the real cross-process fresh-session test and stop after the frozen core is green.

## Session Handoff

- Start with this file and `git status --short --branch`.
- Stop after the frozen Sep 2 core is green; do not begin UI, ACP, or x402 implementation.

## Change Log

| Timestamp | Session/agent | Event | Result |
| --- | --- | --- | --- |
| 2026-09-02T18:25:00+01:00 | Codex | Initialized RightsRelay repository | Frozen core implementation in progress; remote not configured |
| 2026-09-02T20:44:12+01:00 | Codex | Completed SDK proof and deterministic gate checkpoint | Real Sibyl round-trip passed; 7 gate tests passed |
