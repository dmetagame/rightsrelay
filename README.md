# RightsRelay

RightsRelay is release-operations software, not legal advice.

## What it does

- Stores one mutable `UseAuthorization` for one original track and campaign.
- Recalls that authorization in a fresh process before every export.
- Applies a pure deterministic gate with no LLM decision-making.
- Blocks export when channel, paid use, territory, date, campaign, or asset is outside the grant.
- Writes a release packet only after the memory-backed gate clears the attempt.

## Current checkpoint

The deterministic gate, Sibyl persistence wrapper, fail-closed export, deletion
test, and real cross-process recall test are implemented. The UI and partner
integrations are intentionally not part of this checkpoint.

## Run the core

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest -q
```

The automated fresh-session proof launches one Python process to write the
limited grant, waits for it to exit, and launches a second Python process to
recall it, block paid Instagram, update the same WARM entity, and clear the
identical attempt:

```bash
.venv/bin/pytest tests/test_fresh_session.py -vv
```

This is the current Session 1 / process exit / Session 2 procedure. Filmable
shell scripts will be added with the real partner integrations; no UI reset is
treated as a fresh session.

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

Tenant, entity kind, and entity name are fixed in `src/rightsrelay/memory.py`:
`rightsrelay`, `UseAuthorization`, and `campaign-aurora:neon-drive`.

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
