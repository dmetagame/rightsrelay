from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from sibyl_memory_client import NotFoundError

from rightsrelay.app import PACKET_RELATIVE_PATH
from rightsrelay.journal import Journal
from rightsrelay.memory import (
    AUTHORIZATION_NAME,
    AuthorizationMemory,
    MemoryUnavailableError,
)

ACP_CONTRACT_EXPLORER = (
    "https://sepolia.basescan.org/address/"
    "0xdf54E6Ed6cD1d0632d973ADECf96597b7e87893c"
)
TRANSACTION_HASH = re.compile(r"0x[0-9a-fA-F]{64}")
DISPLAY_STATUSES = {"PENDING", "CLEARED_LIMITED", "BLOCKED", "CLEARED"}

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

    entity_found = True
    try:
        authorization = AuthorizationMemory(database).get_authorization()
        body = authorization.model_dump(mode="json")
    except MemoryUnavailableError as exc:
        if not _is_not_found(exc):
            raise
        entity_found = False
        body = {
            "status": "PENDING",
            "blocking_reasons": [],
            "channels": [],
            "paid": False,
            "territories": [],
            "expires_on": None,
            "acp_job_id": None,
            "x402_tx": None,
        }

    events = _ordered_events(database)
    latest_extra = events[-1].get("extra", {}) if events else {}
    event_status = latest_extra.get("status")
    status = event_status if event_status in DISPLAY_STATUSES else body["status"]
    reasons = (
        list(latest_extra.get("reasons", []))
        if status == "BLOCKED"
        else list(body.get("blocking_reasons", []))
    )
    transaction = body.get("x402_tx")
    transaction_link = (
        f"https://sepolia.basescan.org/tx/{transaction}"
        if isinstance(transaction, str) and TRANSACTION_HASH.fullmatch(transaction)
        else None
    )
    packet_written = packet_candidate.is_file()
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
        "status": status,
        "authorization_status": body["status"],
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

    @app.get("/", response_class=HTMLResponse)
    async def board() -> str:
        return html_path.read_text(encoding="utf-8")

    @app.get("/status")
    async def status() -> dict[str, Any]:
        return console_status(database=database, working_directory=working_directory)

    @app.post("/actions/{action}")
    async def run_action(action: str) -> dict[str, Any]:
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
