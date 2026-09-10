from __future__ import annotations

import os
import json
import re
import secrets
from ipaddress import ip_address
from urllib.parse import urlsplit
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sibyl_memory_client import NotFoundError

from rightsrelay.acp_client import ACP_CONTRACT_EXPLORER
from rightsrelay.app import PACKET_RELATIVE_PATH
from rightsrelay.journal import Journal
from rightsrelay.gate import can_release
from rightsrelay.memory import (
    AUTHORIZATION_NAME,
    AuthorizationMemory,
    MemoryUnavailableError,
)

TRANSACTION_HASH = re.compile(r"0x[0-9a-fA-F]{64}")

ACTION_COMMANDS: dict[str, list[str]] = {
    "init-aurora": ["init-aurora"],
    "review-offline": ["review-limited"],
    "acp-review": ["acp-review"],
    "attempt": [
        "attempt",
        "--channel",
        "instagram",
        "--paid",
        "--territories",
        "US,UK",
        "--date",
        "2026-09-02",
    ],
    "acquire-grant": ["acquire-grant"],
    "attempt-again": [
        "attempt",
        "--channel",
        "instagram",
        "--paid",
        "--territories",
        "US,UK",
        "--date",
        "2026-09-02",
    ],
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def _git_head(working_directory: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=working_directory,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "NOT A REPOSITORY"


def _is_not_found(error: BaseException) -> bool:
    current: BaseException | None = error
    while current is not None:
        if isinstance(current, NotFoundError):
            return True
        current = current.__cause__
    return False


def _ordered_events(database: Path) -> list[dict[str, Any]]:
    events = Journal(database).read_recent(limit=5)
    return sorted(events, key=lambda event: str(event.get("ts", "")))


def console_status(
    *,
    database: Path,
    working_directory: Path,
) -> dict[str, Any]:
    database = database.expanduser().resolve()
    working_directory = working_directory.expanduser().resolve()
    packet_candidate = (working_directory / PACKET_RELATIVE_PATH).resolve()

    entity_found = False
    memory_available = True
    attempt = None
    decision = None
    authorization = None
    body = {
        "status": "PENDING", "blocking_reasons": [], "channels": [],
        "paid": False, "territories": [], "expires_on": None,
        "acp_job_id": None, "x402_tx": None,
    }
    try:
        memory = AuthorizationMemory(database)
        authorization = memory.get_authorization()
        body = authorization.model_dump(mode="json")
        entity_found = True
        attempt = memory.get_current_attempt()
        decision = can_release(authorization, attempt) if attempt is not None else None
        status = decision.status if decision is not None else authorization.status
        reasons = decision.reasons if decision is not None else authorization.blocking_reasons
    except MemoryUnavailableError as exc:
        memory_available = False
        status = "BLOCKED"
        reasons = ["Authorization is missing; release cannot be verified" if _is_not_found(exc)
                   else "Authorization or current attempt is unavailable; release cannot be verified"]

    try:
        events = _ordered_events(database)
    except Exception:
        events = []
        memory_available = False
        status = "BLOCKED"
        reasons = ["Sibyl journal is unavailable; release cannot be verified"]
    transaction = body.get("x402_tx")
    transaction_link = (
        f"https://sepolia.basescan.org/tx/{transaction}"
        if isinstance(transaction, str) and TRANSACTION_HASH.fullmatch(transaction)
        else None
    )
    packet_present = packet_candidate.is_file()
    packet_written = False
    if memory_available and authorization is not None and attempt is not None and decision is not None and decision.ok:
        expected_packet = {
            **attempt.model_dump(mode="json"),
            "authorization_version": authorization.version,
            "gate_status": decision.status,
            "evidence_refs": authorization.evidence_refs,
            "acp_job_id": authorization.acp_job_id,
            "x402_tx": authorization.x402_tx,
        }
        try:
            packet_written = json.loads(packet_candidate.read_text(encoding="utf-8")) == expected_packet
        except (OSError, ValueError):
            pass
    journal = [
        {
            "evaluated": event.get("evaluated"),
            "acted": event.get("acted"),
            "forward": event.get("forward"),
            "status": (event.get("extra") or {}).get("status"),
            "extra": event.get("extra"),
        }
        for event in events
    ]

    return {
        "pid": os.getpid(),
        "pid_label": "this pid is the launcher",
        "utc": _utc_now(),
        "git": _git_head(working_directory),
        "db_path": str(database),
        "entity_name": AUTHORIZATION_NAME,
        "entity_found": entity_found,
        "memory_available": memory_available,
        "status": status,
        "authorization_status": body["status"],
        "current_attempt": attempt.model_dump(mode="json") if attempt is not None else None,
        "reasons": reasons,
        "channels": body.get("channels", []),
        "paid": body.get("paid", False),
        "territories": body.get("territories", []),
        "expires_on": body.get("expires_on"),
        "acp_job_id": body.get("acp_job_id"),
        "acp_contract_explorer": ACP_CONTRACT_EXPLORER,
        "x402_tx": transaction,
        "x402_explorer": transaction_link,
        "journal": journal,
        "packet_written": packet_written,
        "packet_present": packet_present,
        "packet_state": "current" if packet_written else "historical" if packet_present else "none",
        "packet_path": str(packet_candidate) if packet_written else None,
    }


def create_console_app(
    *,
    database: Path,
    working_directory: Path,
    python_executable: str = sys.executable,
) -> FastAPI:
    database = database.expanduser().resolve()
    working_directory = working_directory.expanduser().resolve()
    html_path = Path(__file__).with_name("console.html")
    app = FastAPI(title="RightsRelay demo console", docs_url=None, redoc_url=None)
    action_token = secrets.token_urlsafe(32)

    @app.middleware("http")
    async def local_operator_boundary(request: Request, call_next):
        try:
            local_peer = request.client is not None and ip_address(request.client.host).is_loopback
            url = request.url
            allowed = local_peer and url.hostname in {"127.0.0.1", "localhost", "::1"}
            origin = request.headers.get("origin")
            if origin is not None:
                parsed = urlsplit(origin)
                allowed = allowed and (
                    parsed.scheme == url.scheme and parsed.netloc == url.netloc
                    and parsed.path == "" and not parsed.query and not parsed.fragment
                )
            allowed = allowed and request.headers.get("sec-fetch-site", "none") in {"none", "same-origin"}
        except ValueError:
            allowed = False
        if not allowed:
            response = JSONResponse(status_code=403, content={"detail": "Console access requires the local origin"})
        else:
            response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
        return response

    @app.get("/", response_class=HTMLResponse)
    async def board() -> str:
        return html_path.read_text(encoding="utf-8").replace("__RIGHTSRELAY_ACTION_TOKEN__", action_token)

    @app.get("/status")
    async def status() -> dict[str, Any]:
        return console_status(database=database, working_directory=working_directory)

    @app.post("/actions/{action}")
    async def run_action(action: str, request: Request) -> dict[str, Any]:
        supplied = request.headers.get("x-rightsrelay-action-token", "")
        if not supplied.isascii() or not secrets.compare_digest(supplied, action_token):
            raise HTTPException(status_code=403, detail="Reload the local console to authorize actions")
        command = ACTION_COMMANDS.get(action)
        if command is None:
            raise HTTPException(status_code=404, detail="unknown demo action")

        environment = os.environ.copy()
        environment["RIGHTSRELAY_DB"] = str(database)
        started = time.monotonic()
        completed = subprocess.run(
            [python_executable, "-m", "rightsrelay", *command],
            cwd=working_directory,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        return {
            "action": action,
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "duration_ms": round((time.monotonic() - started) * 1000),
        }

    return app
