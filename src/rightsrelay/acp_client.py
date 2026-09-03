from __future__ import annotations

import json
import os
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from rightsrelay.memory import AUTHORIZATION_NAME, AuthorizationMemory

ACP_CONFIG_NAME = "BASE_SEPOLIA_CONFIG_V2"
DEFAULT_OFFERING_NAME = "Rights review"
DEFAULT_TIMEOUT_SECONDS = 300.0
DEFAULT_POLL_SECONDS = 5.0

SERVICE_REQUIREMENT = {
    "entity_name": AUTHORIZATION_NAME,
    "requested_use": {
        "channel": "youtube",
        "paid": False,
        "territories": ["UK"],
        "date": "2026-09-02",
    },
}

REQUIRED_ACP_ENV = (
    "WHITELISTED_WALLET_PRIVATE_KEY",
    "BUYER_AGENT_WALLET_ADDRESS",
    "BUYER_ENTITY_ID",
    "SELLER_AGENT_WALLET_ADDRESS",
    "SELLER_ENTITY_ID",
)


def missing_acp_env(environ: Mapping[str, str] | None = None) -> list[str]:
    source = os.environ if environ is None else environ
    return [name for name in REQUIRED_ACP_ENV if not source.get(name)]


class ACPReviewError(RuntimeError):
    """Raised when the real ACP lifecycle cannot prove a memory-backed review."""


@dataclass(frozen=True)
class ACPReviewResult:
    job_id: int
    phase: str
    contract_explorer_url: str


def _positive_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    try:
        value = default if raw is None else float(raw)
    except ValueError as exc:
        raise ACPReviewError(f"{name} must be a number") from exc
    if value <= 0:
        raise ACPReviewError(f"{name} must be greater than zero")
    return value


def _assert_memory_matches_delivery(
    *,
    memory_path: str | Path,
    job_id: int,
    deliverable: object,
) -> None:
    if not isinstance(deliverable, dict):
        raise ACPReviewError("ACP job did not provide a structured deliverable")
    authorization = AuthorizationMemory(memory_path).get_authorization()
    if (
        authorization.status != "CLEARED_LIMITED"
        or authorization.acp_job_id != str(job_id)
    ):
        raise ACPReviewError(
            "ACP delivery exists but the shared authorization was not updated"
        )
    expected = {
        "entity_name": AUTHORIZATION_NAME,
        "version": authorization.version,
        "status": authorization.status,
        "channels": authorization.channels,
        "paid": authorization.paid,
        "territories": authorization.territories,
        "expires_on": authorization.expires_on.isoformat(),
    }
    if deliverable != expected:
        raise ACPReviewError("ACP deliverable does not match the shared authorization")


def run_acp_review(
    *,
    memory_path: str | Path,
    timeout_seconds: float | None = None,
    poll_seconds: float | None = None,
) -> ACPReviewResult:
    missing = missing_acp_env()
    if missing:
        raise ACPReviewError(f"ACP CONFIG MISSING: {', '.join(missing)}")

    from virtuals_acp.client import VirtualsACP
    from virtuals_acp.configs.configs import BASE_SEPOLIA_CONFIG_V2
    from virtuals_acp.contract_clients.contract_client_v2 import ACPContractClientV2
    from virtuals_acp.models import ACPJobPhase

    timeout = timeout_seconds or _positive_float(
        "RIGHTSRELAY_ACP_TIMEOUT_SECONDS",
        DEFAULT_TIMEOUT_SECONDS,
    )
    interval = poll_seconds or _positive_float(
        "RIGHTSRELAY_ACP_POLL_SECONDS",
        DEFAULT_POLL_SECONDS,
    )
    buyer_contract = ACPContractClientV2(
        wallet_private_key=os.environ["WHITELISTED_WALLET_PRIVATE_KEY"],
        agent_wallet_address=os.environ["BUYER_AGENT_WALLET_ADDRESS"],
        entity_id=int(os.environ["BUYER_ENTITY_ID"]),
        config=BASE_SEPOLIA_CONFIG_V2,
    )
    acp = VirtualsACP(
        acp_contract_clients=buyer_contract,
        skip_socket_connection=True,
    )
    print(f"ACP CONFIG: {ACP_CONFIG_NAME}")
    provider_address = os.environ["SELLER_AGENT_WALLET_ADDRESS"]
    provider = acp.get_agent(provider_address, show_hidden_offerings=True)
    if provider is None:
        raise ACPReviewError(
            f"ACP provider {provider_address} is not registered in the sandbox"
        )

    offering_name = os.environ.get(
        "RIGHTSRELAY_ACP_OFFERING_NAME",
        DEFAULT_OFFERING_NAME,
    )
    offering = next(
        (
            candidate
            for candidate in provider.job_offerings
            if candidate.name.casefold() == offering_name.casefold()
        ),
        None,
    )
    if offering is None:
        available = ", ".join(item.name for item in provider.job_offerings) or "none"
        raise ACPReviewError(
            f"ACP offering {offering_name!r} was not found; available: {available}"
        )

    print(f"ACP REQUEST: {json.dumps(SERVICE_REQUIREMENT, sort_keys=True)}")
    job_id = offering.initiate_job(
        service_requirement=SERVICE_REQUIREMENT,
        evaluator_address=acp.wallet_address,
    )
    if not isinstance(job_id, int) or job_id <= 0:
        raise ACPReviewError("Virtuals ACP did not return a valid onchain job ID")
    print(f"ACP JOB ID: {job_id}")

    deadline = time.monotonic() + timeout
    payment_submitted = False
    evaluation_submitted = False
    last_phase = None
    while time.monotonic() < deadline:
        job = acp.get_job_by_onchain_id(job_id)
        if job.phase != last_phase:
            print(f"ACP PHASE: {job.phase.name}")
            last_phase = job.phase

        if (
            job.phase == ACPJobPhase.NEGOTIATION
            and not payment_submitted
            and job.latest_memo is not None
            and job.latest_memo.next_phase == ACPJobPhase.TRANSACTION
        ):
            job.pay_and_accept_requirement(
                "Buyer accepts the scoped rights-review requirement"
            )
            payment_submitted = True
            print("ACP ESCROW: payment submitted")
        elif job.phase == ACPJobPhase.EVALUATION and not evaluation_submitted:
            _assert_memory_matches_delivery(
                memory_path=memory_path,
                job_id=job_id,
                deliverable=job.get_deliverable(),
            )
            job.evaluate(
                True,
                "Self-evaluation: shared authorization matches the deliverable",
            )
            evaluation_submitted = True
            print("ACP EVALUATION: accepted by buyer")
        elif job.phase == ACPJobPhase.COMPLETED:
            _assert_memory_matches_delivery(
                memory_path=memory_path,
                job_id=job_id,
                deliverable=job.get_deliverable(),
            )
            return ACPReviewResult(
                job_id=job_id,
                phase=job.phase.name,
                contract_explorer_url=(
                    "https://sepolia.basescan.org/address/"
                    f"{BASE_SEPOLIA_CONFIG_V2.contract_address}"
                ),
            )
        elif job.phase == ACPJobPhase.REJECTED:
            raise ACPReviewError(
                f"ACP job {job_id} was rejected: {job.rejection_reason or 'no reason'}"
            )
        elif job.phase == ACPJobPhase.EXPIRED:
            raise ACPReviewError(f"ACP job {job_id} expired")

        time.sleep(interval)

    raise ACPReviewError(f"ACP job {job_id} timed out after {timeout:g} seconds")
