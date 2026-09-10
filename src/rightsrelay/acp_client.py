from __future__ import annotations

import json
import math
import os
import selectors
import subprocess
import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from rightsrelay.memory import AUTHORIZATION_NAME, AuthorizationMemory

ACP_CONFIG_NAME = "BASE_MAINNET_ACP_NODE_V2"
# Official @virtuals-protocol/acp-node-v2@0.1.12 ACP_CONTRACT_ADDRESSES[8453].
ACP_CONTRACT_EXPLORER = "https://basescan.org/address/0x238E541BfefD82238730D00a2208E5497F1832E0"
DEFAULT_OFFERING_NAME = "rights_review"
DEFAULT_TIMEOUT_SECONDS = 300.0
DEFAULT_POLL_SECONDS = 5.0
SERVICE_REQUIREMENT = {
    "entity_name": AUTHORIZATION_NAME,
    "requested_use": {
        "channel": "youtube", "paid": False,
        "territories": ["UK"], "date": "2026-09-02",
    },
}
REQUIRED_ACP_ENV = (
    "BUYER_AGENT_WALLET_ADDRESS", "BUYER_WALLET_ID", "BUYER_SIGNER_PUBLIC_KEY",
    "SELLER_AGENT_WALLET_ADDRESS", "SELLER_WALLET_ID", "SELLER_SIGNER_PUBLIC_KEY",
    "RIGHTSRELAY_ACP_SIGNER_BINARY",
)


def missing_acp_env(environ: Mapping[str, str] | None = None) -> list[str]:
    source = os.environ if environ is None else environ
    return [name for name in REQUIRED_ACP_ENV if not source.get(name)]


class ACPReviewError(RuntimeError):
    """The real ACP lifecycle has not proved a memory-backed review."""


@dataclass(frozen=True)
class ACPReviewResult:
    job_id: int
    phase: str
    contract_explorer_url: str


def require_transaction_approval() -> None:
    if os.environ.get("RIGHTSRELAY_ACP_ALLOW_TRANSACTIONS") != "1":
        raise ACPReviewError(
            "ACP mainnet transactions are disabled; obtain explicit cost approval "
            "before setting RIGHTSRELAY_ACP_ALLOW_TRANSACTIONS=1"
        )


def assert_memory_matches_delivery(
    *, memory_path: str | Path, job_id: int, deliverable: object,
) -> None:
    if not isinstance(deliverable, dict):
        raise ACPReviewError("ACP job did not provide a structured deliverable")
    authorization = AuthorizationMemory(memory_path).get_authorization()
    if (authorization.status != "CLEARED_LIMITED"
            or authorization.acp_job_id != str(job_id)):
        raise ACPReviewError("ACP delivery exists but the shared authorization was not updated")
    expected = {
        "entity_name": AUTHORIZATION_NAME,
        "version": authorization.version,
        "status": authorization.status,
        "channels": authorization.channels,
        "paid": authorization.paid,
        "territories": authorization.territories,
        "expires_on": authorization.expires_on.isoformat(),
    }
    if json.dumps(deliverable, sort_keys=True) != json.dumps(expected, sort_keys=True):
        raise ACPReviewError("ACP deliverable does not match the shared authorization")


def adapter_command(role: str, memory_path: str | Path) -> list[str]:
    root = Path(__file__).resolve().parents[2] / "acp"
    tsx = root / "node_modules" / "tsx" / "dist" / "loader.mjs"
    if not tsx.is_file():
        raise ACPReviewError("ACP Node dependencies missing; run npm ci --prefix acp")
    return ["node", "--import", str(tsx), str(root / "runner.ts"), role,
            str(Path(memory_path).expanduser().resolve())]


def adapter_environment() -> dict[str, str]:
    # x402 credentials and unrelated application secrets never enter Node.
    names = (*REQUIRED_ACP_ENV, "PATH", "HOME", "PYTHONPATH", "NODE_EXTRA_CA_CERTS",
             "XDG_DATA_HOME", "XDG_CONFIG_HOME", "DBUS_SESSION_BUS_ADDRESS",
             "RIGHTSRELAY_ACP_ALLOW_TRANSACTIONS", "RIGHTSRELAY_ACP_MAX_USDC",
             "RIGHTSRELAY_ACP_TIMEOUT_SECONDS", "RIGHTSRELAY_ACP_POLL_SECONDS",
             "RIGHTSRELAY_ACP_RESUME_JOB_ID", "RIGHTSRELAY_ACP_SUBMISSION_BLOCK")
    result = {name: os.environ[name] for name in names if name in os.environ}
    result["RIGHTSRELAY_PYTHON"] = sys.executable
    return result


def run_acp_review(
    *, memory_path: str | Path, timeout_seconds: float | None = None,
    poll_seconds: float | None = None,
) -> ACPReviewResult:
    require_transaction_approval()
    missing = missing_acp_env()
    if missing:
        raise ACPReviewError(f"ACP CONFIG MISSING: {', '.join(missing)}")
    # No network job can be created if Sibyl is missing.
    AuthorizationMemory(memory_path).get_authorization()
    environment = adapter_environment()
    environment.pop("SELLER_SIGNER_PUBLIC_KEY", None)
    for key, supplied, default in (
        ("RIGHTSRELAY_ACP_TIMEOUT_SECONDS", timeout_seconds, DEFAULT_TIMEOUT_SECONDS),
        ("RIGHTSRELAY_ACP_POLL_SECONDS", poll_seconds, DEFAULT_POLL_SECONDS),
    ):
        try:
            value = float(supplied if supplied is not None else environment.get(key, default))
        except ValueError as exc:
            raise ACPReviewError(f"{key} must be a positive finite number") from exc
        if not math.isfinite(value) or value <= 0:
            raise ACPReviewError(f"{key} must be a positive finite number")
        environment[key] = str(value)
    try:
        worker = subprocess.Popen(
            adapter_command("buyer", memory_path), env=environment,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        raise ACPReviewError("ACP Node runtime could not be started") from exc
    result = None
    deadline = time.monotonic() + float(environment["RIGHTSRELAY_ACP_TIMEOUT_SECONDS"]) + 30
    pending = b""
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(worker.stdout, selectors.EVENT_READ)
            while True:
                if time.monotonic() >= deadline:
                    raise ACPReviewError("ACP timed out; inspect active jobs before retrying")
                if not selector.select(timeout=0.5):
                    continue
                chunk = os.read(worker.stdout.fileno(), 65536)
                if not chunk:
                    break
                pending += chunk
                if len(pending) > 131072:
                    raise ACPReviewError("ACP adapter output exceeded its limit")
                while b"\n" in pending:
                    line, pending = pending.split(b"\n", 1)
                    try:
                        item = json.loads(line)
                    except (ValueError, UnicodeError):
                        continue
                    if not isinstance(item, dict):
                        continue
                    # Only adapter-owned safe messages, never raw SDK stderr.
                    if item.get("type") == "progress" and isinstance(item.get("stage"), str):
                        print(f"ACP: {item['stage']}", flush=True)
                    elif item.get("type") == "result":
                        result = item
        worker.wait(timeout=5)
    finally:
        if worker.poll() is None:
            worker.terminate()
            try:
                worker.wait(timeout=5)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.wait()
        worker.stdout.close()
    if worker.returncode != 0 or result is None:
        raise ACPReviewError("ACP adapter failed; check configuration, approval, and active jobs (raw SDK output withheld)")
    try:
        job_id = int(result["job_id"])
        if job_id <= 0 or result["phase"] != "COMPLETED":
            raise ValueError("incomplete result")
        url = result["contract_explorer_url"]
        if not isinstance(url, str) or not url.startswith("https://basescan.org/address/"):
            raise ValueError("wrong network explorer")
        assert_memory_matches_delivery(
            memory_path=memory_path, job_id=job_id, deliverable=result["deliverable"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ACPReviewError("ACP adapter returned an invalid completion result") from exc
    return ACPReviewResult(job_id=job_id, phase="COMPLETED", contract_explorer_url=url)
