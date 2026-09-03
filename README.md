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
fail-closed export, cross-process CLI, official-package x402 seller/buyer, and
Virtuals ACP reviewer processes are implemented. The UI and LLM are out of
scope. The ACP runtime is not claimed as live until a registered, funded
sandbox job completes.

## Run the core

```bash
python3.11 -m venv .venv
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
.venv/bin/python -m rightsrelay acp-review
.venv/bin/python -m rightsrelay status
echo "Session 1 shell PID: $$"
```

The separate provider must already be running in another terminal with the
same database path:

```bash
./scripts/run_acp_provider.sh
```

If ACP registration is unavailable, use `./scripts/demo_session1_offline.sh`.
That explicit fallback runs `review-limited` as `reviewer.local`; it does not
claim an ACP job, escrow, or multiplier. The live `demo_session1.sh` never
falls through to the local reviewer.

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

## Virtuals ACP reviewer setup

RightsRelay uses `virtuals-acp==0.3.23` with the installed
`BASE_SEPOLIA_CONFIG_V2`. The package supports Python 3.10–3.12, so this project
requires Python 3.11 or 3.12. It does not silently use the package's mainnet
default.

The roles are intentionally narrow:

- **Client:** the producer-side `acp-review` command creates the structured job,
  pays the registered job fare into ACP escrow, polls it, and checks that the
  shared authorization—not merely the deliverable—changed.
- **Provider:** the separate RightsRelay rights-review process reads the one
  Sibyl entity, applies fixed limited rights, writes the same entity and COLD
  event, then delivers matching JSON. It never receives chat history.
- **Evaluator:** the client evaluates its own provider result after comparing
  the ACP deliverable with the shared entity. This is disclosed self-evaluation,
  not an independent legal review.

Self-evaluation on Virtuals ACP; provider is our rights-review agent; job escrow
is ACP, which is separate from the later x402 rights-purchase.

Use the [Virtuals ACP/EconomyOS documentation](https://os.virtuals.io/acp/) and
the [official Python SDK repository](https://github.com/Virtual-Protocol/acp-python)
to prepare the sandbox:

1. Register two real sandbox agents: a buyer/client and the RightsRelay
   provider. Create their smart wallets and whitelist the development wallet.
2. Register a provider offering named `Rights review` with a small test-USDC
   fixed price and a requirement schema containing `entity_name` and
   `requested_use` JSON objects.
3. Fund the sandbox buyer with enough test USDC for that registered offering.
4. Set `WHITELISTED_WALLET_PRIVATE_KEY`, `BUYER_AGENT_WALLET_ADDRESS`,
   `BUYER_ENTITY_ID`, `SELLER_AGENT_WALLET_ADDRESS`, and `SELLER_ENTITY_ID` in
   `.env`. Never commit the private key.
5. Load `.env`, start `./scripts/run_acp_provider.sh`, then run
   `./scripts/demo_session1.sh` in a separate terminal.

`acp-review` exits 2 and lists missing variables when this setup is incomplete;
it never substitutes `review-limited`. SDK version 0.3.23 returns an on-chain
job ID but does not expose a per-job URL or the initiation transaction hash on
this interface, so the CLI prints the actual job ID and the SDK configuration's
Base Sepolia contract explorer URL rather than fabricating a link.

At the Sep 5–7 partner workshop, confirm that this Python SDK sandbox contract,
self-evaluation flow, and on-screen escrow count for the partner multiplier.
Do not claim Virtuals on the submission form until the partner confirms it and
the live integration test records a real job ID.

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
- ACP provider read: `src/rightsrelay/acp_provider.py:33` — `get_entity`
- ACP provider write: `src/rightsrelay/acp_provider.py:51` — `set_entity`
- ACP client memory assertion: `src/rightsrelay/acp_client.py:71` — evaluation
  fails unless the same entity contains that ACP job ID

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
- **Virtuals ACP:** implemented against the official Python SDK's Base Sepolia
  V2 config. The offline provider/memory proof is automated. The live job test
  skips without registered buyer/provider credentials, and no job ID is
  claimed at this checkpoint.

The runtime path never fabricates a successful payment response or transaction
hash. When the facilitator does not return a transaction hash, RightsRelay
stores and prints the actual settlement payload instead of inventing one.

## How memory made this possible

The ACP provider and producer-side client coordinate through the same
authorization rather than exchanging transcripts. The provider's structured
deliverable is insufficient on its own: `acp-review` fails unless the WARM
entity itself becomes `CLEARED_LIMITED` with that real job ID. The limited grant
then survives the producer process and becomes the only input the fresh launcher
may use for release policy. The later x402 purchase rewrites that same entity,
changing the identical request from `BLOCKED` to `CLEARED`. Deleting Sibyl makes
export impossible. HOT stores only the current attempt; conversations are not
stored.

## Prior Work

RightsRelay implementation began during the Sibyl Labs Hackathon build window
on September 2, 2026. There was no pre-existing RightsRelay codebase. The
product strategy predates this repository; all code and tests in this repository
were created during the build window.
