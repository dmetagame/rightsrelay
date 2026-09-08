from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from rightsrelay.acp_client import SERVICE_REQUIREMENT
from rightsrelay.memory import AuthorizationMemory


def bridge(database, action, body):
    return subprocess.run(
        [sys.executable, "-m", "rightsrelay.acp_bridge", action, str(database)],
        input=json.dumps(body), capture_output=True, text=True, timeout=10,
    )


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "rightsrelay.sqlite"
    subprocess.run(
        [sys.executable, "-m", "rightsrelay", "init-aurora"],
        env={**os.environ, "RIGHTSRELAY_DB": str(path)}, capture_output=True,
        text=True, check=True,
    )
    return path


def test_acp_bridge_verifies_real_persisted_delivery_and_rejects_tampering(database):
    # This is an offline memory fixture, NOT a fabricated network lifecycle.
    applied = bridge(database, "apply", {"job_id": "8472"})
    assert applied.returncode == 0
    delivery = json.loads(applied.stdout)
    assert delivery["status"] == "CLEARED_LIMITED"
    verified = bridge(database, "verify", {"job_id": "8472", "deliverable": delivery})
    assert verified.returncode == 0
    assert AuthorizationMemory(database).get_authorization().acp_job_id == "8472"
    delivery["paid"] = True
    assert bridge(database, "verify", {"job_id": "8472", "deliverable": delivery}).returncode == 2
    assert bridge(database, "apply", {"job_id": "8473"}).returncode == 2
    assert AuthorizationMemory(database).get_authorization().version == 2


def test_acp_bridge_cannot_deliver_when_memory_is_missing(tmp_path):
    for action in ["inspect", "apply", "verify"]:
        result = bridge(tmp_path / "missing.sqlite", action, {"job_id": "8472", "deliverable": {}})
        assert result.returncode == 2
        assert "error" in json.loads(result.stdout)


def test_acp_bridge_requires_typed_structured_request_not_transcript(database):
    correct = {"job_id": "8472", "requirement": SERVICE_REQUIREMENT}
    assert bridge(database, "validate", correct).returncode == 0
    assert bridge(database, "validate", {"job_id": "8472", "requirement": "clear my track"}).returncode == 2
    incorrect = json.loads(json.dumps(correct))
    incorrect["requirement"]["requested_use"]["paid"] = 0
    assert bridge(database, "validate", incorrect).returncode == 2


def test_late_acp_review_cannot_downgrade_a_paid_grant(database):
    subprocess.run(
        [sys.executable, "-m", "rightsrelay", "apply-grant", "--paid",
         "--channels", "instagram", "--territories", "US,UK", "--expires", "2026-10-31"],
        env={**os.environ, "RIGHTSRELAY_DB": str(database)},
        capture_output=True, text=True, check=True,
    )
    before = AuthorizationMemory(database).get_authorization()
    assert bridge(database, "apply", {"job_id": "8472"}).returncode == 2
    assert AuthorizationMemory(database).get_authorization() == before
    assert before.paid is True
