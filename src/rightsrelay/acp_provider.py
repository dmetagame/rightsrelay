from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from sibyl_memory_client import MemoryClient

from rightsrelay.journal import Journal
from rightsrelay.memory import AUTHORIZATION_KIND, AUTHORIZATION_NAME, TENANT_ID
from rightsrelay.models import UseAuthorization

ACP_REVIEWER_ACTOR = "reviewer.acp"
PROVIDER_REQUIRED_ENV = (
    "SELLER_AGENT_WALLET_ADDRESS", "SELLER_WALLET_ID", "SELLER_SIGNER_PUBLIC_KEY",
    "BUYER_AGENT_WALLET_ADDRESS", "RIGHTSRELAY_ACP_SIGNER_BINARY",
)


def apply_limited_grant(
    *,
    memory_path: str | Path,
    acp_job_id: str,
) -> dict[str, Any]:
    """Apply the deterministic limited review to the shared WARM entity."""
    client = MemoryClient.local(memory_path, tenant_id=TENANT_ID)
    row = client.get_entity(AUTHORIZATION_KIND, AUTHORIZATION_NAME)
    authorization = UseAuthorization.model_validate(row["body"])
    if authorization.acp_job_id == acp_job_id and authorization.status == "CLEARED_LIMITED":
        return limited_deliverable(authorization)
    if authorization.status != "PENDING" or authorization.acp_job_id is not None:
        raise ValueError("ACP review requires PENDING memory; refusing to overwrite an existing grant")
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
    return limited_deliverable(persisted)


def limited_deliverable(persisted: UseAuthorization) -> dict[str, Any]:
    return {
        "entity_name": AUTHORIZATION_NAME,
        "version": persisted.version,
        "status": persisted.status,
        "channels": persisted.channels,
        "paid": persisted.paid,
        "territories": persisted.territories,
        "expires_on": persisted.expires_on.isoformat(),
    }


def missing_provider_env() -> list[str]:
    return [name for name in PROVIDER_REQUIRED_ENV if not os.environ.get(name)]


def run_provider(*, memory_path: str | Path) -> None:
    from rightsrelay.acp_client import (
        ACPReviewError, adapter_command, adapter_environment, require_transaction_approval,
    )

    require_transaction_approval()
    missing = missing_provider_env()
    if missing:
        raise ACPReviewError(f"ACP PROVIDER CONFIG MISSING: {', '.join(missing)}")
    command = adapter_command("provider", memory_path)
    environment = adapter_environment()
    # A provider receives only its own public signer selector, never raw keys.
    environment.pop("BUYER_SIGNER_PUBLIC_KEY", None)
    os.execvpe(command[0], command, environment)


def main() -> int:
    database = Path(
        os.environ.get("RIGHTSRELAY_DB", "./data/rightsrelay.sqlite")
    ).expanduser().resolve()
    try:
        run_provider(memory_path=database)
    except (RuntimeError, ValueError) as exc:
        print(str(exc))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
