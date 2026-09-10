from __future__ import annotations

import json
import subprocess
import sys
from datetime import date

from rightsrelay.acp_provider import apply_limited_grant
from rightsrelay.journal import Journal
from rightsrelay.memory import AuthorizationMemory
from rightsrelay.models import UseAuthorization


def test_acp_provider_updates_the_shared_entity_and_a_fresh_process_recalls_it(
    tmp_path,
) -> None:
    database = tmp_path / "rightsrelay.sqlite"
    AuthorizationMemory(database).set_authorization(
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

    deliverable = apply_limited_grant(
        memory_path=database,
        acp_job_id="8472",
    )

    bridge = subprocess.run(
        [sys.executable, "-m", "rightsrelay.acp_bridge", "delivery", str(database)],
        input=json.dumps({"job_id": "8472"}),
        capture_output=True,
        text=True,
        check=True,
    )

    recalled = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json,sys; "
                "from sibyl_memory_client import MemoryClient; "
                "row=MemoryClient.local(sys.argv[1], tenant_id='rightsrelay')"
                ".get_entity('UseAuthorization', "
                "'campaign-aurora:neon-drive'); "
                "print(json.dumps(row['body'], sort_keys=True))"
            ),
            str(database),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    body = json.loads(recalled.stdout)
    event = Journal(database).read_recent(limit=1)[0]

    assert deliverable == {
        "entity_name": "campaign-aurora:neon-drive",
        "version": 2,
        "status": "CLEARED_LIMITED",
        "channels": ["youtube"],
        "paid": False,
        "territories": ["UK"],
        "expires_on": "2026-09-30",
    }
    assert json.loads(bridge.stdout) == deliverable
    assert body["status"] == "CLEARED_LIMITED"
    assert body["channels"] == ["youtube"]
    assert body["paid"] is False
    assert body["territories"] == ["UK"]
    assert body["acp_job_id"] == "8472"
    assert body["version"] == 2
    assert body["last_actor"] == "reviewer.acp"
    assert event["extra"] == {
        "event": "authorization.reviewed_acp",
        "entity_name": "campaign-aurora:neon-drive",
        "status": "CLEARED_LIMITED",
        "reasons": [],
        "acp_job_id": "8472",
        "actor": "reviewer.acp",
    }

    # A replay of the same funded job must reuse its memory result, not bump
    # the version or append a second review event.
    assert apply_limited_grant(memory_path=database, acp_job_id="8472") == deliverable
    assert AuthorizationMemory(database).get_authorization().version == 2
    assert len(Journal(database).read_recent(limit=5)) == 1
