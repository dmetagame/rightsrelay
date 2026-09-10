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
`MemoryClient.set_entity(category, name, body)`. Producer, local reviewer, and
paid-grant mutations use this wrapper for `campaign-aurora:neon-drive`.
The separate ACP provider writes the identical Sibyl entity directly at
`src/rightsrelay/acp_provider.py:49`; the x402 success path calls the shared
grant mutation at `src/rightsrelay/app.py:259` only after a settled grant is
returned.

## Read path

The source-of-truth read is `src/rightsrelay/memory.py:47`, where
`AuthorizationMemory.get_authorization` calls
`MemoryClient.get_entity(category, name)` and validates `row["body"]`. Missing
memory raises and fails closed; it is never converted into an authorization.
The ACP provider reads that entity at `src/rightsrelay/acp_provider.py:27`.
The ACP client verifies the persisted entity before evaluation at
`src/rightsrelay/acp_client.py:65`, through the local JSON-only `acp_bridge.py`.

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
  is returned. A funded CLI run completed on September 4, 2026 and settled
  `$0.001` test USDC (`0x6335…e46d9`), after which the identical blocked
  request cleared and wrote its packet. The CLI emits the full BaseScan link at
  runtime; tracked documentation intentionally avoids 64-byte hex material.
- **Virtuals ACP — yes, Base mainnet job `78052`.** The registered
  `rights_review` offering completed a real fixed-price 0.01 USDC lifecycle on
  September 10, 2026: request, budget negotiation, escrow funding, separate
  reviewer delivery, and self-evaluation. The reviewer rewrote the shared Sibyl
  entity to `CLEARED_LIMITED` and stored the real job ID. During this first live
  run, the Virtuals job API omitted the posted deliverable from `getJob`; the
  buyer failed closed, then completed the same job only after the on-chain
  `JobSubmitted` hash was independently matched to the structured Sibyl JSON.
  No duplicate job or extra-fund request was used. The adapter is pinned to
  `@virtuals-protocol/acp-node-v2@0.1.12`, and both signers use `ACP_ONLY`
  approval.

ACP review escrow and the later x402 rights purchase are separate events.

## Prior Work

RightsRelay implementation began during the Sibyl Labs Hackathon build window
on September 2, 2026. There was no pre-existing RightsRelay codebase. Product
strategy predates the repository; all implementation and tests were created
during the build window.

## How to run session 1 / kill / session 2

Use Python 3.11 and Node.js 22 from this source checkout. The old Python ACP
SDK has been replaced only for ACP connectivity; Sibyl and x402 stay Python:

```bash
python3.11 -m venv .venv
.venv/bin/pip install -e '.[dev]'
npm ci --prefix acp
# Only on a fresh checkout: never overwrite an existing .env.
test -e .env || cp .env.example .env
```

Set one absolute `RIGHTSRELAY_DB` path. For Base Sepolia x402, set the seller
address in `RIGHTSRELAY_PAY_TO` and buyer private key in
`RIGHTSRELAY_BUYER_KEY`; never commit `.env`. Fund the buyer with test ETH using
[Base’s official testnet options](https://docs.base.org/get-started/get-funds)
and test USDC using the [Circle faucet](https://faucet.circle.com/), selecting
Base Sepolia.

For ACP, keep these values only in the ignored local `.env`. Wallet IDs are
the alphanumeric EVM wallet IDs shown in EconomyOS, NOT legacy numeric entity
IDs. Only public signer selectors are configured here; private ACP keys remain
in the official CLI's local keystore, not `.env` or the x402 wallet:

```text
BUYER_AGENT_WALLET_ADDRESS
BUYER_WALLET_ID
BUYER_SIGNER_PUBLIC_KEY
SELLER_AGENT_WALLET_ADDRESS
SELLER_WALLET_ID
SELLER_SIGNER_PUBLIC_KEY
RIGHTSRELAY_ACP_SIGNER_BINARY
```

Authorize each agent's dedicated signer using the
[official ACP CLI](https://github.com/Virtual-Protocol/acp-cli), pinned for this
setup to `@virtuals-protocol/acp-cli@1.0.35`. Use `restricted` / `ACP_ONLY`,
complete the browser approval, and verify `agent signer-policy` for each agent.
Copy only the returned base64 **public** key into the corresponding selector.
Set `RIGHTSRELAY_ACP_SIGNER_BINARY` to the absolute executable path of the
installed package's `bin/acp-cli-signer-linux` (or the matching platform binary).
Run the provider and buyer as the same OS user that approved these signers.
If the installation/cache is removed, restore that path before running; a
missing executable fails closed. No key export or new agent is needed.

`acp/signer.ts` implements the CLI's real
`sign --public-key <selector> --payload <hex>` protocol through the SDK's
`signFn` callback. It verifies returned P256 signatures locally and suppresses
raw subprocess errors. Each role receives only its own public selector; no
raw ACP or x402 private key is forwarded. Shared OS keystore access is not a
separate-process security sandbox.

Register the exact `rights_review` offering through
[Virtuals ACP](https://app.virtuals.io/acp/) before the take. Use fixed pricing,
no extra funds, no subscriptions, and a structured request with `entity_name`
and `requested_use` matching `SERVICE_REQUIREMENT` in `acp_client.py`.
The verified offering is fixed at 0.01 USDC; recheck the live price before
approving a run. `acp/offering.ts` rejects the old `Rights review` label,
duplicates, extra funds, subscriptions, and fares above the approved cap.
Self-evaluation is
intentional: the client evaluates only after comparing the deliverable with the
shared Sibyl entity.

Mainnet transaction execution defaults OFF. After the human has separately
approved the registered fee and any gas/platform costs, configure
`RIGHTSRELAY_ACP_MAX_USDC` to the approved job-fee cap and
`RIGHTSRELAY_ACP_ALLOW_TRANSACTIONS=1`. The cap covers the job fare, not gas.
Do not set these as part of credential setup alone. Neither process receives
x402 keys. Use limited wallet policies.

The buyer uses `createJobFromOffering`; the provider calls `setBudget`, waits
for onchain funding, calls the existing `apply_limited_grant`, and `submit`s
JSON. The buyer checks memory before `complete` and confirms onchain completion.
Only structured requirement messages are passed to Python—never chat history.
Replayed delivery reuses the same authorization version. Existing grants are
not overwritten by a different review. One provider process per shared DB is
supported; do not run concurrent reviewers or edit grants during a live job.

After an interrupted run, inspect active ACP jobs before retrying. The buyer
refuses to create another job if an active Base job exists. To resume a verified
existing job, explicitly set `RIGHTSRELAY_ACP_RESUME_JOB_ID` to its real numeric
onchain ID. A timeout does not imply escrow was refunded. Never invent an ID.

The published SDK accepts `AcpAgent.create({ evmProvider })`, differing from
some upstream examples using `provider`. Installed type declarations are the
integration reference. See the [official migration guide](https://github.com/Virtual-Protocol/acp-node-v2/blob/main/migration.md).

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
npm run check --prefix acp
npm test --prefix acp
```

The ACP integration test additionally requires `RIGHTSRELAY_RUN_LIVE_ACP_TEST=1`;
it can spend real USDC and must not be enabled for ordinary offline tests.
The x402 funded test retains its existing credential-based opt-in; don't load
funded wallet variables when running an offline-only suite.

## Honest limitations

- RightsRelay is release operations, not legal advice.
- The team owns `Neon Drive`; `rightsrelay-demo` is the rights holder operating
  the demo 402 server. No BMI, Meta, TikTok, or other third-party integration is
  claimed.
- The x402 rights purchase settles on Base Sepolia, not mainnet. x402 mainnet is disabled unless
  `RIGHTSRELAY_X402_MAINNET=1` and a production facilitator are explicitly set;
  the x402.org test facilitator is never used for mainnet.
- ACP is configured separately for Base mainnet; no mainnet job is claimed yet.
  Virtuals ACP uses disclosed self-evaluation. A local `review-limited` take is
  an offline memory fallback and does not count as an ACP job or partner claim.
- ACP dependency audit after compatible patches: no high/critical findings;
  15 low and 5 moderate affected dependency entries remain (elliptic, uuid,
  stream-json and their dependents). This is not a clean security audit or
  proof of live safety. Review these and signer policies before funding; no
  mainnet signing keys or transaction approval were added during migration.
- Scope is one track, one campaign, one authorization, and paid-social music
  rights only.
