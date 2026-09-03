from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import httpx

from rightsrelay.console import create_console_app


def _app(tmp_path: Path):
    database = tmp_path / "data" / "rightsrelay.sqlite"
    app = create_console_app(
        database=database,
        working_directory=tmp_path,
        python_executable=sys.executable,
    )
    return app, database


def _request(app, method: str, path: str) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path)

    return asyncio.run(send())


def _apply_grant(workdir: Path, database: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["RIGHTSRELAY_DB"] = str(database)
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "rightsrelay",
            "apply-grant",
            "--paid",
            "--channels",
            "instagram",
            "--territories",
            "US,UK",
            "--expires",
            "2026-10-31",
        ],
        cwd=workdir,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_status_api_exposes_launcher_and_release_state(tmp_path) -> None:
    app, database = _app(tmp_path)

    assert _request(app, "POST", "/actions/init-aurora").status_code == 200
    assert _request(app, "POST", "/actions/review-offline").status_code == 200
    response = _request(app, "GET", "/status")

    assert response.status_code == 200
    body = response.json()
    assert body["pid"] == os.getpid()
    assert body["pid_label"] == "this pid is the launcher"
    assert body["git"]
    assert body["db_path"] == str(database)
    assert body["entity_name"] == "campaign-aurora:neon-drive"
    assert body["status"] == "CLEARED_LIMITED"
    assert body["reasons"] == []
    assert body["packet_written"] is False
    assert body["packet_path"] is None
    assert body["journal"][-1]["status"] == "CLEARED_LIMITED"


def test_blocked_then_cleared_attempt_updates_board_and_packet(tmp_path) -> None:
    app, database = _app(tmp_path)
    _request(app, "POST", "/actions/init-aurora")
    _request(app, "POST", "/actions/review-offline")

    blocked_action = _request(app, "POST", "/actions/attempt")
    blocked = _request(app, "GET", "/status").json()

    assert blocked_action.status_code == 200
    assert blocked_action.json()["returncode"] == 1
    assert blocked["status"] == "BLOCKED"
    assert "paid media is not authorized" in blocked["reasons"]
    assert blocked["packet_written"] is False
    assert blocked["packet_path"] is None

    applied = _apply_grant(tmp_path, database)
    cleared_action = _request(app, "POST", "/actions/attempt-again")
    cleared = _request(app, "GET", "/status").json()

    assert applied.returncode == 0, applied.stderr
    assert cleared_action.status_code == 200
    assert cleared_action.json()["returncode"] == 0
    assert cleared["status"] == "CLEARED"
    assert cleared["reasons"] == []
    assert cleared["packet_written"] is True
    assert cleared["packet_path"] == str(
        tmp_path / "release-packets" / "campaign-aurora-neon-drive.json"
    )
