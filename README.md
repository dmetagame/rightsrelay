# RightsRelay

RightsRelay is release-operations software, not legal advice.

Public repository: https://github.com/dmetagame/rightsrelay

## What it does

RightsRelay stores one mutable authorization for the original track `Neon
Drive` in campaign `Aurora`. A deterministic gate checks the proposed channel,
paid-media use, territory, and date. Out-of-scope attempts are blocked and
cannot produce a release packet. A scoped x402 purchase can expand the same
authorization, after which the identical attempt clears. No LLM makes or
mutates the decision.

## Where memory is load-bearing

`build_release_packet` accepts a Sibyl database path—not an authorization
object—recalls the single WARM entity, and calls the pure `can_release` policy.
A blocked decision raises the 409-compatible `ExportBlockedError` before any
packet is written. `tests/test_deletion.py` removes the MemoryClient boundary
and proves export fails closed. `tests/test_fresh_session.py` and
`tests/test_console_status.py` kill the writer boundary, recall the entity in a
fresh process, and prove the stored scope changes the later release result.

The policy is `src/rightsrelay/gate.py:6`; the fail-closed export boundary is
`src/rightsrelay/export.py:22`.

## Write path

The source-of-truth write is `src/rightsrelay/memory.py:36`, where
`AuthorizationMemory.set_authorization` calls
`MemoryClient.set_entity(category, name, body)`. Every producer, reviewer, ACP,
and paid-grant mutation reaches this same path for
`campaign-aurora:neon-drive`. The ACP provider enters that path at
`src/rightsrelay/acp_provider.py:26`; the x402 success path calls the shared
grant mutation at `src/rightsrelay/app.py:259` only after a settled grant is
returned.

## Read path

The source-of-truth read is `src/rightsrelay/memory.py:47`, where
`AuthorizationMemory.get_authorization` calls
`MemoryClient.get_entity(category, name)` and validates `row["body"]`. Missing
memory raises and fails closed; it is never converted into an authorization.
The ACP client verifies the persisted entity before evaluation at
`src/rightsrelay/acp_client.py:63`.

## How memory made this possible

The producer, separate reviewer process, and fresh launcher coordinate through
one mutable Sibyl WARM entity rather than a transcript. COLD journal events
preserve who evaluated and acted, while HOT holds only the current release
attempt. The first reviewer narrows the entity to YouTube/organic/UK. That state
survives process death and blocks paid Instagram in US+UK. The later x402 grant
rewrites the same entity, so the exact same request clears. Delete Sibyl and the
export path has no authorization input and cannot function.

## Partner stacks actually exercised

- **Base Sepolia x402 — yes.** `acquire-grant` uses the official `x402==2.21.0`
  client and middleware for a real 402 → payment → retry flow against the
  x402.org testnet facilitator. The demo stores the facilitator’s actual
  settlement identifier and links BaseScan only when a real transaction hash
  is returned. The funded take requires `RIGHTSRELAY_BUYER_KEY` and
  `RIGHTSRELAY_PAY_TO`.
- **Virtuals ACP — code complete; live job pending five environment variables.**
  The adapter uses `virtuals-acp==0.3.23` and `BASE_SEPOLIA_CONFIG_V2`, but no
  job ID is invented or claimed at this checkpoint. Until a registered,
  funded job completes with the five variables below, the submission must not
  claim Virtuals as an exercised partner stack.

ACP review escrow and the later x402 rights purchase are separate events.

## Prior Work

RightsRelay implementation began during the Sibyl Labs Hackathon build window
on September 2, 2026. There was no pre-existing RightsRelay codebase. Product
strategy predates the repository; all implementation and tests were created
during the build window.

## How to run session 1 / kill / session 2

Python 3.11 is required by `virtuals-acp`:

```bash
python3.11 -m venv .venv
.venv/bin/pip install -e '.[dev]'
cp .env.example .env
```

Set one absolute `RIGHTSRELAY_DB` path. For Base Sepolia x402, set the seller
address in `RIGHTSRELAY_PAY_TO` and buyer private key in
`RIGHTSRELAY_BUYER_KEY`; never commit `.env`. Fund the buyer with test ETH using
[Base’s official testnet options](https://docs.base.org/get-started/get-funds)
and test USDC using the [Circle faucet](https://faucet.circle.com/), selecting
Base Sepolia.

For a live ACP review, configure these five values and start the provider:

```text
WHITELISTED_WALLET_PRIVATE_KEY
BUYER_AGENT_WALLET_ADDRESS
BUYER_ENTITY_ID
SELLER_AGENT_WALLET_ADDRESS
SELLER_ENTITY_ID
```

Register the `Rights review` offering through
[Virtuals ACP](https://os.virtuals.io/acp/) before the take. Self-evaluation is
intentional: the client evaluates only after comparing the deliverable with the
shared Sibyl entity.

Load the environment without printing secrets, then start the rights-holder
x402 seller and optional ACP provider in separate terminals:

```bash
set -a
source .env
set +a
./scripts/run_seller.sh
./scripts/run_acp_provider.sh  # live ACP only
```

Session 1 starts the console process:

```bash
./scripts/demo_session1.sh          # click Init Aurora, then ACP review
# or, when ACP is unavailable:
./scripts/demo_session1_offline.sh  # click Init Aurora, then Review (offline)
```

Open `http://127.0.0.1:8080`. The board labels its process “this pid is the
launcher.” After the entity reaches `CLEARED_LIMITED`, kill that exact process
from a visible terminal:

```bash
kill <LAUNCHER_PID_FROM_BOARD>
```

Session 2 uses the same database but starts a new Python process and therefore
shows a different launcher PID:

```bash
./scripts/demo_session2.sh
```

On the reopened board, click **Attempt paid IG US+UK** (red `BLOCKED`, packet
none), **Acquire grant (x402)** (real 402/payment/retry), then **Attempt again**
(green `CLEARED`, packet written). The packet is
`release-packets/campaign-aurora-neon-drive.json`. The exact four-minute take is
in `scripts/record_demo.md`.

Run all automated verification with:

```bash
.venv/bin/pytest -q
```

## Honest limitations

- RightsRelay is release operations, not legal advice.
- The team owns `Neon Drive`; `rightsrelay-demo` is the rights holder operating
  the demo 402 server. No BMI, Meta, TikTok, or other third-party integration is
  claimed.
- Payment settles on Base Sepolia, not mainnet. Mainnet is disabled unless
  `RIGHTSRELAY_X402_MAINNET=1` and a production facilitator are explicitly set;
  the x402.org test facilitator is never used for mainnet.
- Virtuals ACP uses disclosed self-evaluation. A local `review-limited` take is
  an offline memory fallback and does not count as an ACP job or partner claim.
- Scope is one track, one campaign, one authorization, and paid-social music
  rights only.
