from datetime import date

import pytest

from rightsrelay.gate import can_release
from rightsrelay.models import ReleaseAttempt, UseAuthorization


def test_uk_organic_youtube_is_cleared_limited() -> None:
    authorization = UseAuthorization(
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
    attempt = ReleaseAttempt(
        channel="youtube",
        paid=False,
        territories=["UK"],
        date=date(2026, 9, 2),
        campaign_id="aurora",
        asset_id="neon-drive",
    )

    decision = can_release(authorization, attempt)

    assert decision.model_dump() == {
        "ok": True,
        "status": "CLEARED_LIMITED",
        "reasons": [],
    }


def test_paid_instagram_is_blocked_by_limited_grant() -> None:
    authorization = UseAuthorization(
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
    attempt = ReleaseAttempt(
        channel="instagram",
        paid=True,
        territories=["UK"],
        date=date(2026, 9, 2),
        campaign_id="aurora",
        asset_id="neon-drive",
    )

    decision = can_release(authorization, attempt)

    assert decision.model_dump() == {
        "ok": False,
        "status": "BLOCKED",
        "reasons": [
            "channel 'instagram' is not authorized",
            "paid media is not authorized",
        ],
    }


def test_ungranted_territory_is_blocked() -> None:
    authorization = UseAuthorization(
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
    attempt = ReleaseAttempt(
        channel="youtube",
        paid=False,
        territories=["US"],
        date=date(2026, 9, 2),
        campaign_id="aurora",
        asset_id="neon-drive",
    )

    decision = can_release(authorization, attempt)

    assert decision.model_dump() == {
        "ok": False,
        "status": "BLOCKED",
        "reasons": ["territories are not authorized: US"],
    }


def test_paid_instagram_us_and_uk_is_cleared_after_grant_update() -> None:
    authorization = UseAuthorization(
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
    attempt = ReleaseAttempt(
        channel="instagram",
        paid=True,
        territories=["US", "UK"],
        date=date(2026, 9, 2),
        campaign_id="aurora",
        asset_id="neon-drive",
    )

    decision = can_release(authorization, attempt)

    assert decision.model_dump() == {
        "ok": True,
        "status": "CLEARED",
        "reasons": [],
    }


@pytest.mark.parametrize(
    ("attempt_date", "reason"),
    [
        (
            date(2026, 8, 31),
            "release date 2026-08-31 is before authorization start 2026-09-01",
        ),
        (
            date(2026, 10, 1),
            "release date 2026-10-01 is after authorization expiry 2026-09-30",
        ),
    ],
)
def test_release_outside_grant_dates_is_blocked(
    attempt_date: date,
    reason: str,
) -> None:
    authorization = UseAuthorization(
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
    attempt = ReleaseAttempt(
        channel="youtube",
        paid=False,
        territories=["UK"],
        date=attempt_date,
        campaign_id="aurora",
        asset_id="neon-drive",
    )

    decision = can_release(authorization, attempt)

    assert decision.model_dump() == {
        "ok": False,
        "status": "BLOCKED",
        "reasons": [reason],
    }


def test_attempt_for_another_campaign_or_asset_is_blocked() -> None:
    authorization = UseAuthorization(
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
    attempt = ReleaseAttempt(
        channel="youtube",
        paid=False,
        territories=["UK"],
        date=date(2026, 9, 2),
        campaign_id="another-campaign",
        asset_id="another-track",
    )

    decision = can_release(authorization, attempt)

    assert decision.model_dump() == {
        "ok": False,
        "status": "BLOCKED",
        "reasons": [
            "campaign 'another-campaign' does not match authorization campaign 'aurora'",
            "asset 'another-track' does not match authorization asset 'neon-drive'",
        ],
    }
