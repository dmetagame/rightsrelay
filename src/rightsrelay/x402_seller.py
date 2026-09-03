from __future__ import annotations

import os
import re
from dataclasses import dataclass

from fastapi import FastAPI
from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.server import x402ResourceServer

GRANT_PATH = "/grants/campaign-aurora:neon-drive"
BASE_SEPOLIA_NETWORK = "eip155:84532"
BASE_MAINNET_NETWORK = "eip155:8453"
TESTNET_FACILITATOR = "https://x402.org/facilitator"
PRICE = "$0.001"

_EVM_ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")


@dataclass(frozen=True)
class SellerSettings:
    pay_to: str
    network: str
    facilitator_url: str
    price: str = PRICE


def seller_settings(*, pay_to: str | None = None) -> SellerSettings:
    resolved_pay_to = pay_to or os.environ.get("RIGHTSRELAY_PAY_TO")
    if not resolved_pay_to:
        raise RuntimeError("RIGHTSRELAY_PAY_TO is required")
    if not _EVM_ADDRESS.fullmatch(resolved_pay_to):
        raise ValueError("RIGHTSRELAY_PAY_TO must be a 20-byte 0x EVM address")

    mainnet = os.environ.get("RIGHTSRELAY_X402_MAINNET") == "1"
    if mainnet:
        facilitator_url = os.environ.get("RIGHTSRELAY_MAINNET_FACILITATOR")
        if not facilitator_url:
            raise RuntimeError(
                "RIGHTSRELAY_MAINNET_FACILITATOR is required when "
                "RIGHTSRELAY_X402_MAINNET=1"
            )
        network = BASE_MAINNET_NETWORK
    else:
        network = BASE_SEPOLIA_NETWORK
        facilitator_url = TESTNET_FACILITATOR

    return SellerSettings(
        pay_to=resolved_pay_to,
        network=network,
        facilitator_url=facilitator_url,
    )


def create_app(
    *,
    pay_to: str | None = None,
    facilitator_client: object | None = None,
) -> FastAPI:
    settings = seller_settings(pay_to=pay_to)
    facilitator = facilitator_client or HTTPFacilitatorClient(
        FacilitatorConfig(url=settings.facilitator_url)
    )
    server = x402ResourceServer(facilitator)
    server.register(settings.network, ExactEvmServerScheme())

    routes = {
        f"GET {GRANT_PATH}": RouteConfig(
            accepts=PaymentOption(
                scheme="exact",
                pay_to=settings.pay_to,
                price=settings.price,
                network=settings.network,
            ),
            mime_type="application/json",
            description="Scoped paid-social license for RightsRelay's Neon Drive",
        )
    }

    app = FastAPI(title="RightsRelay x402 rights-holder server")
    app.add_middleware(
        PaymentMiddlewareASGI,
        routes=routes,
        server=server,
    )

    @app.get(GRANT_PATH)
    async def issue_grant() -> dict[str, object]:
        return {
            "asset_id": "neon-drive",
            "campaign_id": "aurora",
            "channels": ["youtube", "instagram"],
            "paid": True,
            "territories": ["UK", "US"],
            "valid_from": "2026-09-01",
            "expires_on": "2026-10-31",
            "x402_tx": None,
            "rights_holder": "rightsrelay-demo",
        }

    return app
