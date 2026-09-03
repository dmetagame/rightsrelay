# Project State

> Living handoff for Codex sessions. Read this file before working. Do not put
> secrets or raw credential-bearing values here.

Last updated: `2026-09-03T20:56:41+01:00`
Status: `PUBLICATION_IN_PROGRESS`
Active objective: Verify the complete build, rehearse the offline kill/recall flow, create a public GitHub repository, and push a clean tracking branch without changing frozen product logic.

## Workspace

- Repository: public GitHub repository at `https://github.com/dmetagame/rightsrelay`
- Worktree: `/home/rouma/rightsrelay`
- Branch: `main`
- Implementation checkpoint: `03cf2b1` (`feat: add filmable release demo console`)
- Protected releases/artifacts: `src/rightsrelay/gate.py`, `src/rightsrelay/models.py`, existing MemoryClient call shapes, and both x402/ACP adapters are frozen unless an existing test turns red

## Constraints

- Sibyl Memory must be load-bearing; export fails closed when memory is absent or unreadable.
- The LLM never decides or mutates authorization fields.
- One WARM source-of-truth entity: tenant `rightsrelay`, kind `UseAuthorization`, name `campaign-aurora:neon-drive`.
- Do not store conversations or implement mock ACP/x402 integrations.
- Release operations only; never claim legal advice or third-party platform integrations.
- No secrets in Git.

## Current Context

- This turn is limited to verification, offline rehearsal, publication hygiene,
  README repository URL, and public GitHub publication. Frozen product logic
  and partner lifecycles remain read-only unless an existing test fails.
- GitHub device authorization succeeded as `dmetagame`; public HTTPS remote
  `origin` now points to `https://github.com/dmetagame/rightsrelay.git`.
- `sibyl-memory-client` was not installed globally when work started.
- The official Sibyl repository documents local-first, unactivated SDK operation and WARM uniqueness by `(tenant_id, category, name)`.
- User-confirmed test seams are `can_release`, fail-closed export, and cross-process Sibyl persistence.

## Work Completed

- Added `python -m rightsrelay serve`: a fixed-viewport FastAPI console with a
  one-second `/status` projection, launcher PID/clock/commit provenance,
  authorization scope, gate result, partner identifiers, journal history, and
  release-packet evidence.
- Added six fixed action endpoints that execute the existing CLI commands in
  separate processes. The console adds no policy or mutation path; ACP
  configuration failures and x402 failures are surfaced verbatim.
- Added console API tests proving BLOCKED leaves no packet and an identical
  attempt after the shared grant mutation becomes CLEARED and writes the packet.
- Reworked both session launchers around a real server-process kill/restart,
  replaced the shot list with a timed four-minute unedited take, and replaced
  the README with the ordered submission evidence and honest partner status.
- Confirmed the MIT license and `.env.example` already cover x402 and all five
  required ACP registration variables without values.
- Inspected `virtuals-acp==0.3.23` in a supported Python 3.11 environment.
  Confirmed the current callback is `(job, memo_to_sign)` and lifecycle methods
  live on `ACPJob`; the older README-level `respond_job`, `pay_job`, and
  `deliver_job` methods are absent.
- Confirmed the SDK includes `BASE_SEPOLIA_CONFIG_V2` and
  `BASE_SEPOLIA_ACP_X402_CONFIG_V2`; ACP work will use Base Sepolia rather than
  the package's mainnet default.
- Added the offline provider mutation seam. `apply_limited_grant` directly reads
  and rewrites the one real Sibyl WARM entity, records `reviewer.acp` and the ACP
  job ID in COLD history, and returns the structured deliverable.
- Added a fresh-process test proving the provider mutation survives process
  exit and is recalled through the real `MemoryClient` API.
- Added the real ACP provider callback using the installed `(job,
  memo_to_sign)` shape. It validates the structured entity request, accepts and
  creates the ACP requirement, waits for the transaction phase, rewrites Sibyl,
  and calls `ACPJob.deliver` with matching JSON.
- Added the producer-side ACP client. It discovers the registered `Rights
  review` offering, initiates structured JSON, submits the registered fare with
  `pay_and_accept_requirement`, verifies Sibyl against the deliverable before
  self-evaluation, and polls to completion.
- Added fail-closed `acp-review`, separate live/offline Session 1 scripts, a
  provider launcher, registration documentation, and an integration test that
  cannot create a fake job ID.
- Rebuilt the disposable project environment on Python 3.11.15 because every
  published `virtuals-acp` release rejects Python 3.13. Project metadata now
  records the SDK-compatible `<3.13` upper bound.
- Installed and inspected official `x402==2.21.0`. The FastAPI extra alone does not load the EVM scheme; the package explicitly requires its `evm` extra as well.
- Confirmed the official buyer stack from installed source and upstream examples: `x402Client`, `register_exact_evm_client`, `EthAccountSigner`, and `x402HTTPClient`/httpx transport helpers. Settlement is decoded from the real `PAYMENT-RESPONSE` header.
- Added the Base Sepolia rights-holder seller factory with fixed testnet network `eip155:84532`, facilitator `https://x402.org/facilitator`, price `$0.001`, and env-provided pay-to address. Mainnet remains gated off behind explicit environment configuration.
- Proved the paid grant route returns an actual HTTP 402 and non-empty middleware-generated `PAYMENT-REQUIRED` header both in its isolated HTTP test and with `curl -i` against the live x402.org testnet facilitator.
- Added the official buyer flow using `x402Client`, `EthAccountSigner`,
  `register_exact_evm_client`, and `x402HTTPClient`: unpaid GET, package-generated
  payment headers, paid retry, and decoded `PAYMENT-RESPONSE` settlement.
- Replaced the `acquire-grant` stub. A successful settled grant now invokes the
  existing shared `apply_grant` path exactly once, rewrites the same WARM entity,
  and journals network, facilitator, price, and actual settlement identifier.
- Added settlement propagation to the paid grant response. A transaction hash
  is linked only when the facilitator supplies a real 32-byte hash; otherwise
  the actual settlement payload is stored and printed.
- Added `.env.example`, `scripts/run_seller.sh`, and the complete Session 2
  BLOCKED → HTTP 402 → payment → CLEARED script and shot list. The script refuses
  to run over an existing release packet.
- Documented official Base/Circle testnet funding sources, environment setup,
  the rights-holder disclosure, mainnet-off policy, and exact x402 code paths.
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
| x402 tests | partial/pass | `tests/test_x402_grant.py` → `3 passed, 1 skipped`; funded settlement test skipped because wallet/pay-to variables are absent, 2026-09-03 |
| Full suite after x402 | passed | `.venv/bin/pytest -q` → `18 passed, 1 skipped in 4.67s`; skip is the funded Base Sepolia integration only, 2026-09-03 |
| Demo scripts after x402 | passed | `bash -n scripts/demo_session1.sh scripts/demo_session2.sh scripts/run_seller.sh`, 2026-09-03 |
| Python compilation after x402 | passed | `.venv/bin/python -m compileall -q src tests scripts`; generated project bytecode removed, 2026-09-03 |
| x402 diff hygiene | passed | `git diff --check`, 2026-09-03 |
| ACP provider memory seam | passed | `.venv/bin/pytest tests/test_acp_provider_memory.py -q` → `1 passed`; real Sibyl write/journal and fresh-process recall, 2026-09-03 |
| ACP fail-closed CLI | passed | Missing all five registration variables prints their exact names and exits 2 without falling back to `review-limited`, 2026-09-03 |
| Full suite after ACP | passed | `.venv/bin/pytest -q` → `20 passed, 2 skipped in 10.53s`; skips are the two funded live integrations, 2026-09-03 |
| Frozen paths after ACP | passed | No diff in gate, models, MemoryClient wrapper, x402 buyer/seller, or Session 2, 2026-09-03 |
| Dependency compatibility | passed | `uv pip check --python .venv/bin/python` → all 94 installed packages compatible on Python 3.11.15, 2026-09-03 |
| ACP/demo scripts | passed | `bash -n` on live/offline Session 1, unchanged Session 2, and both provider/seller launchers, 2026-09-03 |
| Console API tests | passed | `.venv/bin/pytest tests/test_console_status.py -q` → `2 passed`; launcher/status projection and BLOCKED/no-packet → CLEARED/packet flow verified, 2026-09-03 |
| Full suite after console | passed | `.venv/bin/pytest -q` → `22 passed, 2 skipped in 6.89s`; skips remain the funded ACP and x402 integrations, 2026-09-03 |
| Console/demo scripts | passed | `bash -n` on both Session 1 launchers, the new-process Session 2 launcher, and partner servers, 2026-09-03 |
| Frozen paths after console | passed | No diff in gate, models, MemoryClient wrapper, x402 buyer/seller, or ACP client/provider, 2026-09-03 |
| Console compile/diff hygiene | passed | `.venv/bin/python -m compileall -q src tests scripts` and `git diff --check`; generated bytecode and owned temp database removed, 2026-09-03 |

## Risks And Blockers

- No Git remote is configured, so checkpoints can be committed locally but not pushed.
- GitHub CLI authentication reports invalid; no authentication change was attempted because this turn forbids pushing and remote creation.
- README file:line references are exact for this checkpoint and must be updated if `memory.py`, `gate.py`, or `export.py` shifts.
- Virtuals ACP code is wired but remains unclaimed as live: all five required
  registration variables are absent, so no job was initiated and no job ID
  exists. The real integration test is skipped rather than mocked.
- `virtuals-acp==0.3.23` emits an upstream `websockets.legacy` deprecation
  warning under the current dependency set; tests still pass.
- The x402 runtime is wired, but a real Base Sepolia settlement cannot yet be
  claimed: neither `RIGHTSRELAY_BUYER_KEY` nor `RIGHTSRELAY_PAY_TO` is present.
  No payment was attempted and no transaction exists from this checkpoint.

## Next Actions

1. Rehearse the 1280×720 board and four-minute take from a clean demo database;
   verify the terminal kill and new launcher PID remain legible in the capture.
2. In the Virtuals sandbox, register distinct buyer and RightsRelay provider
   agents, create smart wallets, whitelist the development wallet, and register
   the `Rights review` offering with the documented JSON schema.
3. Fund the buyer with the offering's test-USDC fare; configure the five ACP
   variables without recording their values; start `run_acp_provider.sh`.
4. Run `tests/test_acp_job.py` and retain the real job ID/escrow evidence. At
   the Sep 5–7 workshop, confirm the Python Base Sepolia V2/self-evaluation flow
   counts before claiming Virtuals.
5. Complete the funded x402 integration and retain the real settlement evidence.

## Session Handoff

- Start with this file and `git status --short --branch`.
- Verification command: `.venv/bin/pytest -q`.
- Treat `src/rightsrelay/gate.py`, `src/rightsrelay/models.py`, and the existing MemoryClient call shapes as frozen unless a test turns red.
- The demo console and submission pack are complete. Do not add product UI,
  LLM behavior, or new protocols; do not claim Virtuals until a live job exists.

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
| 2026-09-03T08:24:35+01:00 | Codex | Completed x402 runtime and demo wiring | 18 tests passed; funded Base Sepolia integration skipped because wallet/pay-to variables are absent; frozen core untouched |
| 2026-09-03T08:25:51+01:00 | Codex | Created local x402 implementation checkpoint | Commit `7444ce1`; no push attempted because no remote exists and this turn forbids creating one |
| 2026-09-03T08:30:00+01:00 | Codex | Reconciled handoff and began Virtuals ACP checkpoint | Clean `main` at `4552eaf`; frozen core and completed x402 path protected; GitHub auth remains invalid and no remote exists |
| 2026-09-03T10:36:38+01:00 | Codex | Completed offline ACP provider tracer | Real shared-entity mutation and fresh-process recall passed; current SDK lifecycle drift documented |
| 2026-09-03T11:14:46+01:00 | Codex | Completed ACP code and fail-closed demo wiring | 20 tests passed; two funded integrations skipped; no credentials or real ACP job ID available |
| 2026-09-03T11:16:29+01:00 | Codex | Created local Virtuals ACP implementation checkpoint | Commit `160f3f3`; no push possible because no remote exists and GitHub authentication is invalid |
| 2026-09-03T15:03:00+01:00 | Codex | Reconciled handoff and began demo-console checkpoint | Clean `main` at `e95e1a8`; frozen core and partner adapters protected; no remote/push work authorized |
| 2026-09-03T15:13:22+01:00 | Codex | Completed demo console and submission pack | 22 tests passed, two funded integrations skipped; real process-restart scripts and four-minute shot list verified |
| 2026-09-03T15:15:00+01:00 | Codex | Created local demo-console checkpoint | Commit `03cf2b1`; no push attempted because no remote exists, GitHub authentication is invalid, and this turn forbids remote work |
| 2026-09-03T20:56:41+01:00 | Codex | Began end-to-end verification and publication | GitHub authentication restored as `dmetagame`; public repository created; sensitive-path history audit clean; required ignore patterns completed |
