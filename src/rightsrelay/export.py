from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rightsrelay.gate import can_release
from rightsrelay.memory import AuthorizationMemory
from rightsrelay.models import GateDecision, ReleaseAttempt


class ExportBlockedError(RuntimeError):
    """A 409-compatible refusal containing the deterministic gate decision."""

    status_code = 409

    def __init__(self, decision: GateDecision) -> None:
        super().__init__("release export blocked: " + "; ".join(decision.reasons))
        self.decision = decision


def build_release_packet(
    *,
    memory_path: str | Path,
    attempt: ReleaseAttempt,
    destination: str | Path,
) -> dict[str, Any]:
    """Recall authorization, gate the attempt, and write only approved output."""
    memory = AuthorizationMemory(memory_path)
    memory.set_current_attempt(attempt)
    authorization = memory.get_authorization()
    decision = can_release(authorization, attempt)

    if not decision.ok:
        raise ExportBlockedError(decision)

    packet: dict[str, Any] = {
        "campaign_id": attempt.campaign_id,
        "asset_id": attempt.asset_id,
        "channel": attempt.channel,
        "paid": attempt.paid,
        "territories": attempt.territories,
        "date": attempt.date.isoformat(),
        "authorization_version": authorization.version,
        "gate_status": decision.status,
        "evidence_refs": authorization.evidence_refs,
        "acp_job_id": authorization.acp_job_id,
        "x402_tx": authorization.x402_tx,
    }
    output_path = Path(destination)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return packet
