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
fail-closed export, and filmable cross-process CLI are implemented. The UI and
partner integrations are intentionally not part of this checkpoint.

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
```

The attempt exits 1, prints `BLOCKED` with reasons, and writes no packet. The
same sequence is packaged as `./scripts/demo_session1.sh` and
`./scripts/demo_session2.sh`; Session 1 intentionally waits so its printed PID
can be killed. The shot list is `scripts/record_demo.md`.

`apply-grant` exists only as the deterministic mutation boundary for tests and
the later successful x402 path:

```bash
.venv/bin/python -m rightsrelay apply-grant --paid --channels instagram --territories US,UK --expires 2026-10-31
```

`acquire-grant` currently raises `NotImplementedError("x402 not wired")`; it
does not simulate a payment or grant.

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
- COLD journal write: `src/rightsrelay/journal.py:41` — `write_event`

Tenant, entity kind, and entity name are fixed in `src/rightsrelay/memory.py`:
`rightsrelay`, `UseAuthorization`, and `campaign-aurora:neon-drive`.

The journal adapter maps the event into the installed SDK's keyword-only
`write_event(evaluated=, acted=, forward=, extra=, ts=)` call. `evaluated`
records the entity/status/reasons, `acted` records event/actor, `forward`
records the authorization status, and `extra` always contains entity name,
status, and reasons plus `acp_job_id` and `x402_tx` when present.

## Partner stacks

None are claimed at this checkpoint.

- **Base/x402:** not implemented or exercised yet.
- **Virtuals ACP:** not implemented or exercised yet.

No mock ACP or x402 implementation is present. A stack will be named here only
after its real lifecycle is exercised and filmable.

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
