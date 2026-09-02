import json
from datetime import date

import pytest

from rightsrelay import memory as memory_module
from rightsrelay.export import ExportBlockedError, build_release_packet
from rightsrelay.memory import AuthorizationMemory, MemoryUnavailableError
from rightsrelay.models import ReleaseAttempt, UseAuthorization


def test_authorized_export_writes_release_packet(tmp_path) -> None:
    memory_path = tmp_path / "memory.db"
    destination = tmp_path / "release-packet.json"
    memory = AuthorizationMemory(memory_path)
    memory.set_authorization(
        UseAuthorization(
            asset_id="neon-drive",
            campaign_id="aurora",
            channels=["youtube", "instagram"],
            paid=True,
            territories=["UK", "US"],
            valid_from=date(2026, 9, 1),
            expires_on=date(2026, 10, 31),
            status="CLEARED",
            evidence_refs=["reference:paid-social-grant"],
            x402_tx="0xabc123",
            version=2,
            last_actor="license-buyer",
        )
    )
    attempt = ReleaseAttempt(
        channel="instagram",
        paid=True,
        territories=["US", "UK"],
        date=date(2026, 9, 2),
        campaign_id="aurora",
        asset_id="neon-drive",
    )

    packet = build_release_packet(
        memory_path=memory_path,
        attempt=attempt,
        destination=destination,
    )

    assert packet == {
        "campaign_id": "aurora",
        "asset_id": "neon-drive",
        "channel": "instagram",
        "paid": True,
        "territories": ["US", "UK"],
        "date": "2026-09-02",
        "authorization_version": 2,
        "gate_status": "CLEARED",
        "evidence_refs": ["reference:paid-social-grant"],
        "acp_job_id": None,
        "x402_tx": "0xabc123",
    }
    assert json.loads(destination.read_text(encoding="utf-8")) == packet


def test_blocked_attempt_returns_409_and_writes_no_packet(tmp_path) -> None:
    memory_path = tmp_path / "memory.db"
    destination = tmp_path / "release-packet.json"
    memory = AuthorizationMemory(memory_path)
    memory.set_authorization(
        UseAuthorization(
            asset_id="neon-drive",
            campaign_id="aurora",
            channels=["youtube"],
            paid=False,
            territories=["UK"],
            valid_from=date(2026, 9, 1),
            expires_on=date(2026, 9, 30),
            status="CLEARED_LIMITED",
            version=1,
            last_actor="acp-reviewer",
        )
    )
    attempt = ReleaseAttempt(
        channel="instagram",
        paid=True,
        territories=["US", "UK"],
        date=date(2026, 9, 2),
        campaign_id="aurora",
        asset_id="neon-drive",
    )

    with pytest.raises(ExportBlockedError) as caught:
        build_release_packet(
            memory_path=memory_path,
            attempt=attempt,
            destination=destination,
        )

    assert caught.value.status_code == 409
    assert caught.value.decision.reasons == [
        "channel 'instagram' is not authorized",
        "paid media is not authorized",
        "territories are not authorized: US",
    ]
    assert not destination.exists()


def test_removing_memory_client_makes_export_fail_closed(
    monkeypatch,
    tmp_path,
) -> None:
    memory_path = tmp_path / "memory.db"
    destination = tmp_path / "release-packet.json"
    memory = AuthorizationMemory(memory_path)
    memory.set_authorization(
        UseAuthorization(
            asset_id="neon-drive",
            campaign_id="aurora",
            channels=["instagram"],
            paid=True,
            territories=["UK", "US"],
            valid_from=date(2026, 9, 1),
            expires_on=date(2026, 10, 31),
            status="CLEARED",
            version=2,
            last_actor="license-buyer",
        )
    )
    attempt = ReleaseAttempt(
        channel="instagram",
        paid=True,
        territories=["US", "UK"],
        date=date(2026, 9, 2),
        campaign_id="aurora",
        asset_id="neon-drive",
    )
    monkeypatch.setattr(memory_module, "MemoryClient", None)

    with pytest.raises(MemoryUnavailableError, match="MemoryClient is unavailable"):
        build_release_packet(
            memory_path=memory_path,
            attempt=attempt,
            destination=destination,
        )

    assert not destination.exists()
