from __future__ import annotations

from pathlib import Path
from typing import Any

from sibyl_memory_client import MemoryClient

from rightsrelay.journal import Journal
from rightsrelay.memory import AUTHORIZATION_KIND, AUTHORIZATION_NAME, TENANT_ID
from rightsrelay.models import UseAuthorization

ACP_REVIEWER_ACTOR = "reviewer.acp"


def apply_limited_grant(
    *,
    memory_path: str | Path,
    acp_job_id: str,
) -> dict[str, Any]:
    """Apply the deterministic limited review to the shared WARM entity."""
    client = MemoryClient.local(memory_path, tenant_id=TENANT_ID)
    row = client.get_entity(AUTHORIZATION_KIND, AUTHORIZATION_NAME)
    authorization = UseAuthorization.model_validate(row["body"])
    body = authorization.model_dump(mode="json")
    body.update(
        {
            "channels": ["youtube"],
            "paid": False,
            "territories": ["UK"],
            "valid_from": "2026-09-01",
            "expires_on": "2026-09-30",
            "status": "CLEARED_LIMITED",
            "blocking_reasons": [],
            "acp_job_id": acp_job_id,
            "version": authorization.version + 1,
            "last_actor": ACP_REVIEWER_ACTOR,
        }
    )
    reviewed = UseAuthorization.model_validate(body)
    persisted_row = client.set_entity(
        AUTHORIZATION_KIND,
        AUTHORIZATION_NAME,
        reviewed.model_dump(mode="json"),
    )
    persisted = UseAuthorization.model_validate(persisted_row["body"])
    Journal(memory_path).record(
        event="authorization.reviewed_acp",
        actor=ACP_REVIEWER_ACTOR,
        status=persisted.status,
        reasons=persisted.blocking_reasons,
        acp_job_id=persisted.acp_job_id,
        x402_tx=persisted.x402_tx,
        metadata={"actor": ACP_REVIEWER_ACTOR},
    )
    return {
        "entity_name": AUTHORIZATION_NAME,
        "version": persisted.version,
        "status": persisted.status,
        "channels": persisted.channels,
        "paid": persisted.paid,
        "territories": persisted.territories,
        "expires_on": persisted.expires_on.isoformat(),
    }
