#!/usr/bin/env bash

set -eu

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
SELLER_PORT="${RIGHTSRELAY_SELLER_PORT:-8402}"

if [ -z "${RIGHTSRELAY_PAY_TO:-}" ]; then
  echo "RIGHTSRELAY_PAY_TO is required." >&2
  exit 2
fi

if [ "${RIGHTSRELAY_X402_MAINNET:-0}" = "1" ]; then
  if [ -z "${RIGHTSRELAY_MAINNET_FACILITATOR:-}" ]; then
    echo "RIGHTSRELAY_MAINNET_FACILITATOR is required for mainnet." >&2
    exit 2
  fi
  echo "Rights holder: rightsrelay-demo"
  echo "Network: eip155:8453 (Base mainnet)"
  echo "Facilitator: ${RIGHTSRELAY_MAINNET_FACILITATOR}"
else
  echo "Rights holder: rightsrelay-demo"
  echo "Network: eip155:84532 (Base Sepolia)"
  echo "Facilitator: https://x402.org/facilitator"
fi

echo "Price: \$0.001 USDC"
echo "Seller: http://127.0.0.1:${SELLER_PORT}"
exec "$PYTHON_BIN" -m uvicorn rightsrelay.x402_seller:create_app \
  --factory \
  --host 127.0.0.1 \
  --port "$SELLER_PORT"
