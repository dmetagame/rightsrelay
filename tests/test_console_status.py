from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import httpx
from sibyl_memory_client import MemoryClient

from rightsrelay.memory import TENANT_ID, AUTHORIZATION_KIND, AUTHORIZATION_NAME
from rightsrelay.journal import Journal
from rightsrelay.memory import CURRENT_ATTEMPT_KEY

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
            base_url="http://127.0.0.1:8080",
        ) as client:
            headers = {}
            if method == "POST":
                board = await client.get("/")
                token = re.search(r'name="rightsrelay-action-token" content="([^"]+)"', board.text)
                assert token is not None
                headers["X-RightsRelay-Action-Token"] = token.group(1)
            return await client.request(method, path, headers=headers)

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


def test_deleted_authorization_cannot_display_old_clearance(tmp_path):
    app, database = _app(tmp_path)
    _request(app, "POST", "/actions/init-aurora")
    _request(app, "POST", "/actions/review-offline")
    assert _apply_grant(tmp_path, database).returncode == 0
    _request(app, "POST", "/actions/attempt-again")
    MemoryClient.local(database, tenant_id=TENANT_ID).delete_entity(AUTHORIZATION_KIND, AUTHORIZATION_NAME)

    status = _request(app, "GET", "/status").json()
    assert status["status"] == "BLOCKED"
    assert status["entity_found"] is False
    assert status["reasons"]
    assert status["packet_written"] is False
    assert status["packet_path"] is None


def test_current_attempt_and_authorization_override_journal_and_old_packet(tmp_path):
    app, database = _app(tmp_path)
    _request(app, "POST", "/actions/init-aurora")
    _request(app, "POST", "/actions/review-offline")
    approved = subprocess.run([sys.executable, "-m", "rightsrelay", "attempt",
        "--channel", "youtube", "--territories", "UK", "--date", "2026-09-02"],
        cwd=tmp_path, env={**os.environ, "RIGHTSRELAY_DB": str(database)}, capture_output=True)
    assert approved.returncode == 0
    assert _request(app, "GET", "/status").json()["packet_written"] is True
    _request(app, "POST", "/actions/attempt")
    # A journal event is historical evidence, never permission for the current attempt.
    Journal(database).record(event="audit.historical_clearance", actor="test.fixture", status="CLEARED")
    status = _request(app, "GET", "/status").json()
    assert status["status"] == "BLOCKED"
    assert "paid media is not authorized" in status["reasons"]
    assert status["packet_written"] is False
    assert status["packet_path"] is None
    assert status["packet_present"] is True
    assert status["packet_state"] == "historical"
    assert (tmp_path / "release-packets/campaign-aurora-neon-drive.json").is_file()


def test_unreadable_hot_attempt_is_blocked_instead_of_using_clear_journal(tmp_path):
    app, database = _app(tmp_path)
    _request(app, "POST", "/actions/init-aurora")
    _request(app, "POST", "/actions/review-offline")
    assert _apply_grant(tmp_path, database).returncode == 0
    MemoryClient.local(database, tenant_id=TENANT_ID).set_state(CURRENT_ATTEMPT_KEY, {"invalid": "attempt"})
    status = _request(app, "GET", "/status").json()
    assert status["status"] == "BLOCKED"
    assert status["memory_available"] is False
    assert status["packet_written"] is False
    assert status["reasons"]


def test_packet_must_match_current_authorization_version_and_scope(tmp_path):
    app, database = _app(tmp_path)
    _request(app, "POST", "/actions/init-aurora")
    assert _apply_grant(tmp_path, database).returncode == 0
    _request(app, "POST", "/actions/attempt")
    packet_path = tmp_path / "release-packets/campaign-aurora-neon-drive.json"
    original = json.loads(packet_path.read_text())
    for changes in [{"authorization_version": 999}, {"territories": ["CA"]}, {"paid": False}]:
        packet_path.write_text(json.dumps({**original, **changes}))
        status = _request(app, "GET", "/status").json()
        assert status["status"] == "CLEARED"
        assert status["packet_written"] is False
        assert status["packet_state"] == "historical"
    packet_path.write_text("{interrupted JSON")
    assert not _request(app, "GET", "/status").json()["packet_written"]
