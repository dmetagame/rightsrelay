# Project State

> Living handoff for Codex sessions. Read this file before working. Do not put
> secrets or raw credential-bearing values here.

Last updated: `2026-09-03T08:15:00+01:00`
Status: `IN_PROGRESS`
Active objective: Replace the explicit x402 stub with an official-package Base Sepolia seller/buyer flow, reuse the existing same-entity grant mutation, and preserve the frozen core.

## Workspace

- Repository: local Git repository; no remote configured yet
- Worktree: `/home/rouma/rightsrelay`
- Branch: `main`
- Commit: `0919d8f` (`docs: record CLI checkpoint`)
- Protected releases/artifacts: `src/rightsrelay/gate.py`, `src/rightsrelay/models.py`, and existing MemoryClient call shapes are frozen unless an existing test turns red; partner integrations and UI are out of scope

## Constraints

- Sibyl Memory must be load-bearing; export fails closed when memory is absent or unreadable.
- The LLM never decides or mutates authorization fields.
- One WARM source-of-truth entity: tenant `rightsrelay`, kind `UseAuthorization`, name `campaign-aurora:neon-drive`.
- Do not store conversations or implement mock ACP/x402 integrations.
- Release operations only; never claim legal advice or third-party platform integrations.
- No secrets in Git.

## Current Context

- This turn is x402-only: official Python package inspection, Base Sepolia seller/buyer, CLI wiring, demo Session 2 update, x402 tests, environment template, and README documentation.
- GitHub CLI authentication currently reports invalid and no remote exists. Pushing or creating a remote is explicitly forbidden this turn.
- `sibyl-memory-client` was not installed globally when work started.
- The official Sibyl repository documents local-first, unactivated SDK operation and WARM uniqueness by `(tenant_id, category, name)`.
- User-confirmed test seams are `can_release`, fail-closed export, and cross-process Sibyl persistence.

## Work Completed

- Installed and inspected official `x402==2.21.0`. The FastAPI extra alone does not load the EVM scheme; the package explicitly requires its `evm` extra as well.
- Confirmed the official buyer stack from installed source and upstream examples: `x402Client`, `register_exact_evm_client`, `EthAccountSigner`, and `x402HTTPClient`/httpx transport helpers. Settlement is decoded from the real `PAYMENT-RESPONSE` header.
- Added the Base Sepolia rights-holder seller factory with fixed testnet network `eip155:84532`, facilitator `https://x402.org/facilitator`, price `$0.001`, and env-provided pay-to address. Mainnet remains gated off behind explicit environment configuration.
- Proved the paid grant route returns an actual HTTP 402 and non-empty middleware-generated `PAYMENT-REQUIRED` header both in its isolated HTTP test and with `curl -i` against the live x402.org testnet facilitator.
- Inspected the installed SDK source: `write_event` is keyword-only over `evaluated`, `acted`, `forward`, `extra`, and `ts`; `read_events` exists and returns decoded event dictionaries.
- Added `src/rightsrelay/journal.py`, mapping authorization event/status/reasons into the four Sibyl journal payloads and placing entity name, status, reasons, and present partner identifiers in `extra`.
- Added a real temporary-database journal test that writes through `write_event` and verifies the decoded `read_events` result.
- Added the `python -m rightsrelay` CLI with `status`, `init-aurora`, local-only `review-limited`, fail-closed `attempt`, explicit unwired `acquire-grant`, and deterministic `apply-grant` commands. Every command prints the resolved shared database path.
- Added a three-process CLI test: Session 1 persists the limited authorization, Session 2 blocks paid Instagram and writes no packet, the same entity is updated, and Session 3 clears the identical request and writes `release-packets/campaign-aurora-neon-drive.json`.
- Added executable blocked-only demo scripts and an unedited-take shot list. Session 1 waits for a real PID kill; Session 2 ends BLOCKED and makes no ACP/x402 claim.
- Updated README CLI commands and exact journal/memory/export line references.
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
| CLI subprocess lifecycle | passed | `.venv/bin/pytest tests/test_cli_fresh_session.py -q` → `3 passed`; missing entity exits 2, x402 stub is explicit, blocked/no-packet then identical cleared request verified, 2026-09-02 |
| Full suite after CLI | passed | `.venv/bin/pytest -q` → `15 passed in 2.23s`, 2026-09-02 |
| Demo scripts | passed | `bash -n scripts/demo_session1.sh scripts/demo_session2.sh`, 2026-09-02 |
| Python compilation after CLI | passed | `.venv/bin/python -m compileall -q src tests scripts`; generated project `__pycache__` directories removed, 2026-09-02 |
| Final diff hygiene | passed | `git diff --check`, 2026-09-02 |
| x402 package inspection | passed | `x402==2.21.0`; official package source and upstream Python examples agree on seller/buyer symbols, 2026-09-03 |
| Seller unpaid HTTP | passed | `pytest tests/test_x402_grant.py -q` → `1 passed`; live `curl -i` → HTTP 402 with `PAYMENT-REQUIRED`, 2026-09-03 |

## Risks And Blockers

- No Git remote is configured, so checkpoints can be committed locally but not pushed.
- GitHub CLI authentication reports invalid; no authentication change was attempted because this turn forbids pushing and remote creation.
- README file:line references are exact for this checkpoint and must be updated if `memory.py`, `gate.py`, or `export.py` shifts.
- Virtuals ACP and x402 remain deliberately unwired and unclaimed. `acquire-grant` raises `NotImplementedError("x402 not wired")`.
- A real Base Sepolia buyer payment cannot be claimed until `RIGHTSRELAY_BUYER_KEY` and a funded seller address are supplied; no credential is currently present in the project.

## Next Actions

1. Install and inspect the official `x402[fastapi]` package, recording exact seller and buyer APIs.
2. Drive the real unpaid HTTP 402 and failure-without-mutation behavior test-first.
3. Wire Base Sepolia payment and reuse the existing grant-application boundary; keep live payment skippable when wallet funding is unavailable.

## Session Handoff

- Start with this file and `git status --short --branch`.
- Verification command: `.venv/bin/pytest -q`.
- Treat `src/rightsrelay/gate.py`, `src/rightsrelay/models.py`, and the existing MemoryClient call shapes as frozen unless a test turns red.
- Do not begin UI, ACP, or x402 implementation without a new authorized continuation.

## Change Log

| Timestamp | Session/agent | Event | Result |
| --- | --- | --- | --- |
| 2026-09-02T18:25:00+01:00 | Codex | Initialized RightsRelay repository | Frozen core implementation in progress; remote not configured |
| 2026-09-02T20:44:12+01:00 | Codex | Completed SDK proof and deterministic gate checkpoint | Real Sibyl round-trip passed; 7 gate tests passed |
| 2026-09-02T20:49:06+01:00 | Codex | Completed frozen memory/export checkpoint | Commit `cc5d7c1`; 11 tests passed; deletion and real fresh-process requirements verified; partner stacks remain unclaimed |
| 2026-09-02T21:00:00+01:00 | Codex | Started journal and CLI checkpoint | Frozen core protected; no remote/push; journal and CLI test seams confirmed |
| 2026-09-02T21:10:42+01:00 | Codex | Completed real Sibyl journal adapter | `write_event` mapping verified through `read_events`; journal test passed |
| 2026-09-02T21:17:24+01:00 | Codex | Completed filmable CLI checkpoint | 15 tests passed; cross-process BLOCKED/no-packet and CLEARED/packet paths verified; demo remains honest about unwired partners |
| 2026-09-02T21:18:30+01:00 | Codex | Created local CLI checkpoint | Commit `847ab39`; no push attempted because the user forbade pushing and no remote exists |
| 2026-09-02T21:25:00+01:00 | Codex | Reconciled handoff and began x402-only checkpoint | Actual clean HEAD was state-only commit `0919d8f`; frozen policy/models remain protected; no remote/push |
| 2026-09-03T08:15:00+01:00 | Codex | Completed x402 seller 402 tracer | Official middleware emitted HTTP 402 and `PAYMENT-REQUIRED` through live testnet facilitator; no payment attempted |
