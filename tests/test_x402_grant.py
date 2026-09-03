from __future__ import annotations

import asyncio

import httpx
from x402.schemas import SupportedKind, SupportedResponse

from rightsrelay.x402_seller import BASE_SEPOLIA_NETWORK, GRANT_PATH, create_app


TEST_PAY_TO = "0x1111111111111111111111111111111111111111"


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
