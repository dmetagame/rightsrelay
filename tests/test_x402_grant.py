from __future__ import annotations

import asyncio
import os
from datetime import date

import httpx
import pytest
from x402.schemas import SupportedKind, SupportedResponse

from rightsrelay.app import acquire_grant, apply_grant
from rightsrelay.gate import can_release
from rightsrelay.journal import Journal
from rightsrelay.memory import AuthorizationMemory
from rightsrelay.models import ReleaseAttempt, UseAuthorization
from rightsrelay.x402_buyer import buy_grant
from rightsrelay.x402_seller import BASE_SEPOLIA_NETWORK, GRANT_PATH, create_app


TEST_PAY_TO = "0x1111111111111111111111111111111111111111"
HAS_LIVE_PAYMENT_ENV = bool(
    os.environ.get("RIGHTSRELAY_BUYER_KEY")
    and os.environ.get("RIGHTSRELAY_PAY_TO")
)


class _UnpaidOnlyFacilitator:
    """Capability double matching the official x402 server test seam."""

    def get_supported(self) -> SupportedResponse:
        return SupportedResponse(
            kinds=[
                SupportedKind(
                    x402_version=2,
                    scheme="exact",
                    network=BASE_SEPOLIA_NETWORK,
                    extra={},
                )
            ],
            extensions=[],
            signers={},
        )

    async def verify(self, payload, requirements):
        raise AssertionError("unpaid request must not be verified")

    async def settle(self, payload, requirements):
        raise AssertionError("unpaid request must not be settled")


def test_unpaid_grant_request_is_a_real_http_402() -> None:
    app = create_app(
        pay_to=TEST_PAY_TO,
        facilitator_client=_UnpaidOnlyFacilitator(),
    )

    async def request_grant() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.get(GRANT_PATH)

    response = asyncio.run(request_grant())

    assert response.status_code == 402, response.text
    assert response.headers["payment-required"]


def test_failed_payment_does_not_apply_a_grant(tmp_path) -> None:
    database = tmp_path / "rightsrelay.sqlite"
    memory = AuthorizationMemory(database)
    limited = UseAuthorization(
        asset_id="neon-drive",
        campaign_id="aurora",
        channels=["youtube"],
        paid=False,
        territories=["UK"],
        valid_from=date(2026, 9, 1),
        expires_on=date(2026, 9, 30),
        status="CLEARED_LIMITED",
        version=2,
        last_actor="reviewer.local",
    )
    memory.set_authorization(limited)

    def payment_failure() -> dict[str, object]:
        raise RuntimeError("facilitator refused payment")

    with pytest.raises(RuntimeError, match="facilitator refused payment"):
        acquire_grant(database=database, purchase=payment_failure)

    assert memory.get_authorization() == limited


def test_applied_x402_grant_clears_paid_instagram_and_journals_payment(tmp_path) -> None:
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
            status="CLEARED_LIMITED",
            version=2,
            last_actor="reviewer.local",
        )
    )
    settlement_identifier = "test-settlement-identifier"

    authorization = apply_grant(
        database=database,
        paid=True,
        channels=["youtube", "instagram"],
        territories=["UK", "US"],
        expires="2026-10-31",
        x402_tx=settlement_identifier,
        actor="x402.buyer",
        event="authorization.grant_acquired_x402",
        journal_metadata={
            "network": "eip155:84532",
            "facilitator": "https://x402.org/facilitator",
            "tx": settlement_identifier,
            "price": "$0.001",
        },
    )
    decision = can_release(
        authorization,
        ReleaseAttempt(
            channel="instagram",
            paid=True,
            territories=["US", "UK"],
            date=date(2026, 9, 2),
            campaign_id="aurora",
            asset_id="neon-drive",
        ),
    )
    event = Journal(database).read_recent(limit=1)[0]

    assert decision.ok is True
    assert decision.status == "CLEARED"
    assert authorization.x402_tx == settlement_identifier
    assert event["extra"] == {
        "event": "authorization.grant_acquired_x402",
        "entity_name": "campaign-aurora:neon-drive",
        "status": "CLEARED",
        "reasons": [],
        "x402_tx": settlement_identifier,
        "network": "eip155:84532",
        "facilitator": "https://x402.org/facilitator",
        "tx": settlement_identifier,
        "price": "$0.001",
    }


@pytest.mark.skipif(
    not HAS_LIVE_PAYMENT_ENV,
    reason="requires funded RIGHTSRELAY_BUYER_KEY and RIGHTSRELAY_PAY_TO",
)
def test_real_base_sepolia_buyer_round_trip() -> None:
    app = create_app(pay_to=os.environ["RIGHTSRELAY_PAY_TO"])
    grant = buy_grant(
        seller_url=f"http://testserver{GRANT_PATH}",
        buyer_key=os.environ["RIGHTSRELAY_BUYER_KEY"],
        transport=httpx.ASGITransport(app=app),
    )

    assert grant["asset_id"] == "neon-drive"
    assert grant["campaign_id"] == "aurora"
    assert grant["rights_holder"] == "rightsrelay-demo"
    assert grant["x402_tx"]
    assert grant["_payment"]["network"] == "eip155:84532"
