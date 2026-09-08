from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import date

import pytest

from rightsrelay.acp_client import missing_acp_env, run_acp_review
from rightsrelay.journal import Journal
from rightsrelay.memory import AuthorizationMemory
from rightsrelay.models import UseAuthorization


HAS_LIVE_ACP_ENV = (
    not missing_acp_env()
    and os.environ.get("RIGHTSRELAY_ACP_ALLOW_TRANSACTIONS") == "1"
    and bool(os.environ.get("RIGHTSRELAY_ACP_MAX_USDC"))
    and os.environ.get("RIGHTSRELAY_RUN_LIVE_ACP_TEST") == "1"
)


@pytest.mark.skipif(
    not HAS_LIVE_ACP_ENV,
    reason="requires ACP signers, funded Base mainnet buyer, approved cap, transaction opt-in and RIGHTSRELAY_RUN_LIVE_ACP_TEST=1",
)
def test_real_acp_job_delivers_and_updates_the_shared_authorization(tmp_path) -> None:
    database = tmp_path / "rightsrelay.sqlite"
    memory = AuthorizationMemory(database)
    memory.set_authorization(
        UseAuthorization(
            asset_id="neon-drive",
            campaign_id="aurora",
            channels=["youtube"],
            paid=False,
            territories=["UK"],
            valid_from=date(2026, 9, 1),
            expires_on=date(2026, 9, 30),
            status="PENDING",
            version=1,
            last_actor="producer",
        )
    )
    environment = os.environ.copy()
    environment["RIGHTSRELAY_DB"] = str(database)
    environment["PYTHONUNBUFFERED"] = "1"
    provider = subprocess.Popen(
        [sys.executable, "-m", "rightsrelay.acp_provider"],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        time.sleep(5)
        if provider.poll() is not None:
            stdout, stderr = provider.communicate()
            pytest.fail(f"ACP provider exited early:\n{stdout}\n{stderr}")
        result = run_acp_review(memory_path=database)
    finally:
        if provider.poll() is None:
            provider.terminate()
            provider.wait(timeout=15)

    recalled = memory.get_authorization()
    event = Journal(database).read_recent(limit=1)[0]

    assert result.job_id > 0
    assert result.phase == "COMPLETED"
    assert recalled.status == "CLEARED_LIMITED"
    assert recalled.acp_job_id == str(result.job_id)
    assert event["extra"]["acp_job_id"] == str(result.job_id)
    assert event["extra"]["actor"] == "reviewer.acp"
