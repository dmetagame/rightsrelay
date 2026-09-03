# RightsRelay

RightsRelay is release-operations software, not legal advice.

## What it does

- Stores one mutable `UseAuthorization` for one original track and campaign.
- Recalls that authorization in a fresh process before every export.
- Applies a pure deterministic gate with no LLM decision-making.
- Blocks export when channel, paid use, territory, date, campaign, or asset is outside the grant.
- Writes a release packet only after the memory-backed gate clears the attempt.

## Current checkpoint

The deterministic gate, Sibyl persistence wrapper, COLD journal adapter,
fail-closed export, cross-process CLI, and official-package x402 seller/buyer
are implemented. The UI, LLM, and Virtuals ACP are out of scope.

## Run the core

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest -q
```

The automated fresh-session proof launches separate Python processes to write
the limited grant, recall and block paid Instagram, update the same WARM entity,
and clear the identical attempt:

```bash
.venv/bin/pytest tests/test_cli_fresh_session.py -vv
```

### Session 1 / kill / Session 2

Use one absolute database path in both shells. From the repository root, the
filmable Session 1 commands are:

```bash
export RIGHTSRELAY_DB="$(pwd)/data/rightsrelay.sqlite"
.venv/bin/python -m rightsrelay status
.venv/bin/python -m rightsrelay init-aurora
.venv/bin/python -m rightsrelay review-limited
.venv/bin/python -m rightsrelay status
echo "Session 1 shell PID: $$"
```

Record that PID, then kill it from another terminal so the handoff is a real
process restart:

```bash
kill <SESSION_1_SHELL_PID>
```

Open a new shell, export the same database path, and run Session 2:

```bash
export RIGHTSRELAY_DB="$(pwd)/data/rightsrelay.sqlite"
.venv/bin/python -m rightsrelay status
.venv/bin/python -m rightsrelay attempt --channel instagram --paid --territories US,UK --date 2026-09-02
.venv/bin/python -m rightsrelay acquire-grant
.venv/bin/python -m rightsrelay attempt --channel instagram --paid --territories US,UK --date 2026-09-02
.venv/bin/python -m rightsrelay status
```

The first attempt exits 1, prints `BLOCKED` with reasons, and writes no packet.
After a successful x402 purchase updates the same WARM authorization, the
identical attempt prints `CLEARED` and writes
`release-packets/campaign-aurora-neon-drive.json`. The sequence is packaged as
`./scripts/demo_session1.sh` and `./scripts/demo_session2.sh`; Session 1 waits
so its printed PID can be killed. The shot list is `scripts/record_demo.md`.

`apply-grant` exists only as the deterministic mutation boundary for tests and
the later successful x402 path:

```bash
.venv/bin/python -m rightsrelay apply-grant --paid --channels instagram --territories US,UK --expires 2026-10-31
```

The direct `apply-grant` command is not a payment simulation and must not be
shown as x402. `acquire-grant` is the only filmed payment path.

## Base Sepolia x402 setup

Demo settles on Base Sepolia via x402.org facilitator; we are the rights holder
for this track. The original track is `Neon Drive`, and the paid endpoint is
operated by `rightsrelay-demo`. No BMI, Meta, TikTok, or other third-party
rights/platform API is claimed.

Create `.env` from `.env.example` and provide:

- `RIGHTSRELAY_PAY_TO`: the seller's 20-byte EVM address.
- `RIGHTSRELAY_BUYER_KEY`: the buyer wallet's hex private key. Never commit it.
- `RIGHTSRELAY_SELLER_URL`: seller base URL; defaults to
  `http://127.0.0.1:8402`.
- `RIGHTSRELAY_DB`: shared Sibyl SQLite path.

Fund the buyer address with Base Sepolia test ETH and USDC. Base lists its
[official testnet funding options](https://docs.base.org/get-started/get-funds),
and test USDC is available from the [Circle faucet](https://faucet.circle.com/)
by selecting Base Sepolia. Testnet funds have no monetary value.

Load the variables without printing secret values, then start the rights-holder
server in one terminal:

```bash
set -a
source .env
set +a
./scripts/run_seller.sh
```

In another terminal, run `./scripts/demo_session2.sh` after completing Session
1. The buyer performs an unpaid GET, parses the middleware-generated
`PAYMENT-REQUIRED`, signs with the configured wallet, retries, validates the
real `PAYMENT-RESPONSE`, and only then mutates the authorization. If settlement
fails, no grant is applied.

Mainnet is off by default. Enabling it requires both
`RIGHTSRELAY_X402_MAINNET=1` and a production
`RIGHTSRELAY_MAINNET_FACILITATOR`; the test-only x402.org facilitator is never
used for mainnet. This checkpoint has not been tested or claimed on mainnet.

## Where memory is load-bearing

`build_release_packet` accepts a memory database path, never an authorization
object. It must recall the single WARM entity and call `can_release` before it
can write output. A blocked decision raises a 409-compatible
`ExportBlockedError` before the destination is created. If `MemoryClient` is
removed, construction fails closed and no packet is written; this is enforced
by `tests/test_deletion.py`.

Critical paths at this checkpoint:

- WARM write: `src/rightsrelay/memory.py:36` — `set_entity`
- WARM read: `src/rightsrelay/memory.py:47` — `get_entity`
- Pure policy: `src/rightsrelay/gate.py:6` — `can_release`
- Export boundary: `src/rightsrelay/export.py:22` — `build_release_packet`
- COLD journal write: `src/rightsrelay/journal.py:46` — `write_event`
- x402 payment route: `src/rightsrelay/x402_seller.py:127` — protected route
- Paid grant handler: `src/rightsrelay/x402_seller.py:147` — grant JSON
- Apply after payment: `src/rightsrelay/app.py:259` — calls the shared
  `apply_grant` mutation path only after the buyer returns a settled grant

Tenant, entity kind, and entity name are fixed in `src/rightsrelay/memory.py`:
`rightsrelay`, `UseAuthorization`, and `campaign-aurora:neon-drive`.

The journal adapter maps the event into the installed SDK's keyword-only
`write_event(evaluated=, acted=, forward=, extra=, ts=)` call. `evaluated`
records the entity/status/reasons, `acted` records event/actor, `forward`
records the authorization status, and `extra` always contains entity name,
status, and reasons plus `acp_job_id` and `x402_tx` when present.

## Partner stacks

- **Base/x402:** implemented with the official `x402==2.21.0` Python package.
  Automated tests exercise the real middleware's HTTP 402 response. The funded
  Base Sepolia round-trip is an integration test that skips unless
  `RIGHTSRELAY_BUYER_KEY` and `RIGHTSRELAY_PAY_TO` are present; do not claim the
  hackathon multiplier until a real settlement is recorded on screen.
- **Virtuals ACP:** not implemented or claimed.

The runtime path never fabricates a successful payment response or transaction
hash. When the facilitator does not return a transaction hash, RightsRelay
stores and prints the actual settlement payload instead of inventing one.

## How memory made this possible

The limited grant survives the producer process and becomes the only input the
fresh launcher may use for release policy. Updating the same WARM entity changes
the later result from `BLOCKED` to `CLEARED`; deleting Sibyl makes export
impossible rather than falling back to a PDF, prompt, or caller-supplied grant.
HOT state stores only the current release attempt. Conversations are not stored.

## Prior Work

RightsRelay implementation began during the Sibyl Labs Hackathon build window
on September 2, 2026. There was no pre-existing RightsRelay codebase. The
product strategy predates this repository; all code and tests in this repository
were created during the build window.
