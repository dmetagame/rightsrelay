from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import httpx
from eth_account import Account
from x402 import max_amount, prefer_network, prefer_scheme, x402Client
from x402.http import x402HTTPClient
from x402.mechanisms.evm import EthAccountSigner
from x402.mechanisms.evm.exact import register_exact_evm_client

from rightsrelay.x402_seller import (
    BASE_MAINNET_NETWORK,
    BASE_SEPOLIA_NETWORK,
    GRANT_PATH,
    PRICE,
    TESTNET_FACILITATOR,
)

DEFAULT_SELLER_BASE_URL = "http://127.0.0.1:8402"


def _payment_environment() -> tuple[str, str]:
    if os.environ.get("RIGHTSRELAY_X402_MAINNET") == "1":
        facilitator = os.environ.get("RIGHTSRELAY_MAINNET_FACILITATOR")
        if not facilitator:
            raise RuntimeError(
                "RIGHTSRELAY_MAINNET_FACILITATOR is required when "
                "RIGHTSRELAY_X402_MAINNET=1"
            )
        return BASE_MAINNET_NETWORK, facilitator
    return BASE_SEPOLIA_NETWORK, TESTNET_FACILITATOR


def _grant_url(configured: str | None) -> str:
    value = configured or os.environ.get(
        "RIGHTSRELAY_SELLER_URL",
        DEFAULT_SELLER_BASE_URL,
    )
    if value.rstrip("/").endswith(GRANT_PATH):
        return value.rstrip("/")
    return f"{value.rstrip('/')}{GRANT_PATH}"


def _settlement_identifier(settlement: Any) -> tuple[str, dict[str, Any]]:
    payload = settlement.model_dump(mode="json", by_alias=True, exclude_none=True)
    transaction = (
        settlement.transaction.strip()
        if isinstance(settlement.transaction, str)
        else ""
    )
    if transaction:
        return transaction, payload
    return json.dumps(payload, sort_keys=True, separators=(",", ":")), payload


def _validate_grant(grant: object) -> dict[str, Any]:
    if not isinstance(grant, dict):
        raise ValueError("x402 seller returned a non-object grant")
    if grant.get("asset_id") != "neon-drive":
        raise ValueError("x402 grant has the wrong asset")
    if grant.get("campaign_id") != "aurora":
        raise ValueError("x402 grant has the wrong campaign")
    if grant.get("rights_holder") != "rightsrelay-demo":
        raise ValueError("x402 grant has an unexpected rights holder")
    if grant.get("paid") is not True:
        raise ValueError("x402 grant does not authorize paid media")
    if not {"youtube", "instagram"}.issubset(set(grant.get("channels", []))):
        raise ValueError("x402 grant is missing required channels")
    if not {"UK", "US"}.issubset(set(grant.get("territories", []))):
        raise ValueError("x402 grant is missing required territories")
    if grant.get("valid_from") != "2026-09-01":
        raise ValueError("x402 grant has an unexpected start date")
    if grant.get("expires_on") != "2026-10-31":
        raise ValueError("x402 grant has an unexpected expiry")
    return grant


async def _buy_grant(
    *,
    seller_url: str,
    buyer_key: str,
    transport: httpx.AsyncBaseTransport | None,
) -> dict[str, Any]:
    network, facilitator = _payment_environment()
    account = Account.from_key(buyer_key)
    client = x402Client()
    register_exact_evm_client(
        client,
        EthAccountSigner(account),
        networks=network,
        policies=[prefer_network(network), prefer_scheme("exact"), max_amount(1000)],
    )
    protocol = x402HTTPClient(client)

    async with httpx.AsyncClient(transport=transport, timeout=60.0) as http:
        try:
            unpaid = await http.get(seller_url)
        except httpx.HTTPError as exc:
            raise RuntimeError(
                f"x402 seller unavailable at {seller_url}; run scripts/run_seller.sh"
            ) from exc
        if unpaid.status_code != 402:
            raise RuntimeError(
                f"x402 seller returned {unpaid.status_code}; expected 402 before payment"
            )
        required_header = unpaid.headers.get("payment-required")
        if not required_header:
            raise RuntimeError("x402 seller returned 402 without PAYMENT-REQUIRED")

        print("X402 UNPAID: 402 Payment Required")
        print(f"PAYMENT-REQUIRED: {required_header}")
        print(f"X402 PAY: {PRICE} USDC on {network}")

        payment_headers, payment_payload = await protocol.handle_402_response(
            dict(unpaid.headers),
            unpaid.content,
            seller_url,
        )
        paid = await http.get(seller_url, headers=payment_headers)
        if paid.status_code != 200:
            raise RuntimeError(
                f"x402 paid retry failed with {paid.status_code}: {paid.text}"
            )

        processed = await protocol.process_payment_result(
            payment_payload,
            paid.headers.get,
            paid.status_code,
        )
        settlement = processed.settle_response
        if settlement is None:
            raise RuntimeError("x402 paid response omitted PAYMENT-RESPONSE")
        if not settlement.success:
            raise RuntimeError(
                f"x402 settlement failed: {settlement.error_reason or settlement.error_message}"
            )
        if str(settlement.network) != network:
            raise RuntimeError(
                f"x402 settlement used {settlement.network}; expected {network}"
            )

        identifier, settlement_payload = _settlement_identifier(settlement)
        grant = _validate_grant(paid.json())
        grant["x402_tx"] = identifier
        grant["_payment"] = {
            "network": str(settlement.network),
            "facilitator": facilitator,
            "tx": identifier,
            "price": PRICE,
            "settlement": settlement_payload,
        }
        print("X402 PAID: 200 OK")
        print(f"PAYMENT-RESPONSE: {json.dumps(settlement_payload, sort_keys=True)}")
        return grant


def buy_grant(
    *,
    seller_url: str | None = None,
    buyer_key: str | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:
    key = buyer_key or os.environ.get("RIGHTSRELAY_BUYER_KEY")
    if not key:
        raise RuntimeError("RIGHTSRELAY_BUYER_KEY is required to pay for the grant")
    return asyncio.run(
        _buy_grant(
            seller_url=_grant_url(seller_url),
            buyer_key=key,
            transport=transport,
        )
    )
