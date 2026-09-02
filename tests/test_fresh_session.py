from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SESSION_ONE = """
import json
import os
import sys
from rightsrelay.memory import AuthorizationMemory
from rightsrelay.models import UseAuthorization

memory = AuthorizationMemory(sys.argv[1])
memory.set_authorization(UseAuthorization.model_validate(json.loads(sys.argv[2])))
print(json.dumps({"pid": os.getpid()}))
"""

SESSION_TWO = """
import json
import os
import sys
from rightsrelay.gate import can_release
from rightsrelay.memory import AuthorizationMemory
from rightsrelay.models import ReleaseAttempt, UseAuthorization

memory = AuthorizationMemory(sys.argv[1])
attempt = ReleaseAttempt.model_validate(json.loads(sys.argv[2]))
limited = memory.get_authorization()
before = can_release(limited, attempt)
updated_body = limited.model_dump(mode="json")
updated_body.update({
    "channels": ["youtube", "instagram"],
    "paid": True,
    "territories": ["UK", "US"],
    "expires_on": "2026-10-31",
    "status": "CLEARED",
    "evidence_refs": ["reference:paid-social-grant"],
    "x402_tx": "0xabc123",
    "version": 2,
    "last_actor": "license-buyer",
})
memory.set_authorization(UseAuthorization.model_validate(updated_body))
after = can_release(memory.get_authorization(), attempt)
print(json.dumps({
    "pid": os.getpid(),
    "recalled_status": limited.status,
    "before": before.model_dump(),
    "after": after.model_dump(),
}))
"""


def _run_session(code: str, memory_path: Path, payload: dict) -> dict:
    completed = subprocess.run(
        [sys.executable, "-c", code, str(memory_path), json.dumps(payload)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_fresh_process_recalls_and_updates_release_policy(tmp_path) -> None:
    memory_path = tmp_path / "memory.db"
    limited_authorization = {
        "asset_id": "neon-drive",
        "campaign_id": "aurora",
        "channels": ["youtube"],
        "paid": False,
        "territories": ["UK"],
        "valid_from": "2026-09-01",
        "expires_on": "2026-09-30",
        "status": "CLEARED_LIMITED",
        "blocking_reasons": [],
        "evidence_refs": ["reference:original-grant"],
        "acp_job_id": "acp-demo-job",
        "x402_tx": None,
        "version": 1,
        "last_actor": "acp-reviewer",
    }
    paid_instagram_attempt = {
        "channel": "instagram",
        "paid": True,
        "territories": ["US", "UK"],
        "date": "2026-09-02",
        "campaign_id": "aurora",
        "asset_id": "neon-drive",
    }

    first = _run_session(SESSION_ONE, memory_path, limited_authorization)
    second = _run_session(SESSION_TWO, memory_path, paid_instagram_attempt)

    assert first["pid"] != second["pid"]
    assert second["recalled_status"] == "CLEARED_LIMITED"
    assert second["before"] == {
        "ok": False,
        "status": "BLOCKED",
        "reasons": [
            "channel 'instagram' is not authorized",
            "paid media is not authorized",
            "territories are not authorized: US",
        ],
    }
    assert second["after"] == {
        "ok": True,
        "status": "CLEARED",
        "reasons": [],
    }
