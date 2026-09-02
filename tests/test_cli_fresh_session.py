from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _run_cli(
    workdir: Path,
    database: Path,
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["RIGHTSRELAY_DB"] = str(database)
    return subprocess.run(
        [sys.executable, "-m", "rightsrelay", *arguments],
        cwd=workdir,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_persists_blocked_then_cleared_policy_across_processes(tmp_path) -> None:
    database = tmp_path / "data" / "rightsrelay.sqlite"
    packet_path = tmp_path / "release-packets" / "campaign-aurora-neon-drive.json"

    initialized = _run_cli(tmp_path, database, "init-aurora")
    reviewed = _run_cli(tmp_path, database, "review-limited")
    recalled = _run_cli(tmp_path, database, "status", "--last", "5")

    assert initialized.returncode == 0, initialized.stderr
    assert reviewed.returncode == 0, reviewed.stderr
    assert recalled.returncode == 0, recalled.stderr
    for result in (initialized, reviewed, recalled):
        assert f"DB: {database}" in result.stdout
    assert '"status": "CLEARED_LIMITED"' in recalled.stdout
    assert '"event": "authorization.reviewed"' in recalled.stdout

    blocked = _run_cli(
        tmp_path,
        database,
        "attempt",
        "--channel",
        "instagram",
        "--paid",
        "--territories",
        "US,UK",
        "--date",
        "2026-09-02",
    )

    assert blocked.returncode == 1
    assert f"DB: {database}" in blocked.stdout
    assert "BLOCKED" in blocked.stdout
    assert "channel 'instagram' is not authorized" in blocked.stdout
    assert "paid media is not authorized" in blocked.stdout
    assert "territories are not authorized: US" in blocked.stdout
    assert not packet_path.exists()

    applied = _run_cli(
        tmp_path,
        database,
        "apply-grant",
        "--paid",
        "--channels",
        "instagram",
        "--territories",
        "US,UK",
        "--expires",
        "2026-10-31",
    )
    cleared = _run_cli(
        tmp_path,
        database,
        "attempt",
        "--channel",
        "instagram",
        "--paid",
        "--territories",
        "US,UK",
        "--date",
        "2026-09-02",
    )

    assert applied.returncode == 0, applied.stderr
    assert f"DB: {database}" in applied.stdout
    assert "GRANT APPLIED" in applied.stdout
    assert cleared.returncode == 0, cleared.stderr
    assert f"DB: {database}" in cleared.stdout
    assert "CLEARED" in cleared.stdout
    assert str(packet_path) in cleared.stdout
    assert packet_path.exists()
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert packet["gate_status"] == "CLEARED"
    assert packet["channel"] == "instagram"
    assert packet["territories"] == ["US", "UK"]


def test_attempt_without_authorization_exits_two(tmp_path) -> None:
    database = tmp_path / "data" / "rightsrelay.sqlite"

    result = _run_cli(
        tmp_path,
        database,
        "attempt",
        "--channel",
        "instagram",
        "--paid",
        "--territories",
        "US,UK",
        "--date",
        "2026-09-02",
    )

    assert result.returncode == 2
    assert result.stdout.splitlines() == [f"DB: {database}", "NOT FOUND"]
    assert not (tmp_path / "release-packets").exists()


def test_acquire_grant_is_an_explicit_unwired_stub(tmp_path) -> None:
    database = tmp_path / "data" / "rightsrelay.sqlite"

    result = _run_cli(tmp_path, database, "acquire-grant")

    assert result.returncode != 0
    assert f"DB: {database}" in result.stdout
    assert "NotImplementedError: x402 not wired" in result.stderr
