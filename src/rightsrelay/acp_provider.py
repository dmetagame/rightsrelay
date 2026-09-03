from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any

from sibyl_memory_client import MemoryClient, NotFoundError

from rightsrelay.journal import Journal
from rightsrelay.memory import AUTHORIZATION_KIND, AUTHORIZATION_NAME, TENANT_ID
from rightsrelay.models import UseAuthorization

ACP_REVIEWER_ACTOR = "reviewer.acp"
PROVIDER_REQUIRED_ENV = (
    "WHITELISTED_WALLET_PRIVATE_KEY",
    "SELLER_AGENT_WALLET_ADDRESS",
    "SELLER_ENTITY_ID",
)

logger = logging.getLogger("rightsrelay.acp_provider")


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


def _parse_service_requirement(raw: object) -> dict[str, Any]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("service requirement must be JSON") from exc
    if not isinstance(raw, dict):
        raise ValueError("service requirement must be a JSON object")
    if raw.get("entity_name") != AUTHORIZATION_NAME:
        raise ValueError(f"entity_name must be {AUTHORIZATION_NAME}")
    if not isinstance(raw.get("requested_use"), dict):
        raise ValueError("requested_use must be a JSON object")
    return raw


def _authorization_exists(memory_path: str | Path) -> None:
    client = MemoryClient.local(memory_path, tenant_id=TENANT_ID)
    client.get_entity(AUTHORIZATION_KIND, AUTHORIZATION_NAME)


def make_on_new_task(memory_path: str | Path):
    """Build the installed SDK's `(job, memo_to_sign)` provider callback."""
    from virtuals_acp.models import ACPJobPhase

    def on_new_task(job, memo_to_sign=None) -> None:
        try:
            _parse_service_requirement(job.requirement)
        except ValueError as exc:
            if job.phase == ACPJobPhase.REQUEST:
                job.reject(str(exc))
            logger.error("ACP job %s rejected: %s", job.id, exc)
            return

        if (
            job.phase == ACPJobPhase.REQUEST
            and memo_to_sign is not None
            and memo_to_sign.next_phase == ACPJobPhase.NEGOTIATION
        ):
            try:
                _authorization_exists(memory_path)
            except NotFoundError:
                job.reject(f"authorization entity {AUTHORIZATION_NAME} was not found")
                logger.error("ACP job %s rejected: authorization not found", job.id)
                return
            job.accept("RightsRelay authorization is available for scoped review")
            job.create_requirement(
                "Rights review accepted; transfer the registered ACP job fare "
                "to escrow to continue"
            )
            logger.info("ACP job %s accepted for %s", job.id, AUTHORIZATION_NAME)
            return

        if (
            job.phase == ACPJobPhase.TRANSACTION
            and memo_to_sign is not None
            and memo_to_sign.next_phase == ACPJobPhase.EVALUATION
        ):
            try:
                deliverable = apply_limited_grant(
                    memory_path=memory_path,
                    acp_job_id=str(job.id),
                )
            except NotFoundError:
                job.reject(f"authorization entity {AUTHORIZATION_NAME} was not found")
                logger.error("ACP job %s rejected: authorization disappeared", job.id)
                return
            job.deliver(deliverable)
            logger.info("ACP job %s delivered structured rights review", job.id)

    return on_new_task


def missing_provider_env() -> list[str]:
    return [name for name in PROVIDER_REQUIRED_ENV if not os.environ.get(name)]


def run_provider(*, memory_path: str | Path) -> None:
    missing = missing_provider_env()
    if missing:
        raise RuntimeError(f"ACP PROVIDER CONFIG MISSING: {', '.join(missing)}")

    from virtuals_acp.client import VirtualsACP
    from virtuals_acp.configs.configs import BASE_SEPOLIA_CONFIG_V2
    from virtuals_acp.contract_clients.contract_client_v2 import ACPContractClientV2

    contract_client = ACPContractClientV2(
        wallet_private_key=os.environ["WHITELISTED_WALLET_PRIVATE_KEY"],
        agent_wallet_address=os.environ["SELLER_AGENT_WALLET_ADDRESS"],
        entity_id=int(os.environ["SELLER_ENTITY_ID"]),
        config=BASE_SEPOLIA_CONFIG_V2,
    )
    acp = VirtualsACP(
        acp_contract_clients=contract_client,
        on_new_task=make_on_new_task(memory_path),
    )
    print(f"ACP PROVIDER PID: {os.getpid()}", flush=True)
    print("ACP CONFIG: BASE_SEPOLIA_CONFIG_V2", flush=True)
    print(f"ACP PROVIDER WALLET: {acp.wallet_address}", flush=True)
    print(f"DB: {Path(memory_path).expanduser().resolve()}", flush=True)
    print("ACP provider reads only the shared authorization entity.", flush=True)
    threading.Event().wait()


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
