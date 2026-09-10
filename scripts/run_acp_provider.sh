#!/usr/bin/env bash

set -eu

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
missing=""

for name in \
  SELLER_AGENT_WALLET_ADDRESS \
  SELLER_WALLET_ID \
  SELLER_SIGNER_PUBLIC_KEY \
  RIGHTSRELAY_ACP_SIGNER_BINARY \
  BUYER_AGENT_WALLET_ADDRESS
do
  if [ -z "${!name:-}" ]; then
    if [ -n "$missing" ]; then
      missing="$missing, "
    fi
    missing="$missing$name"
  fi
done

if [ -n "$missing" ]; then
  echo "ACP PROVIDER CONFIG MISSING: $missing" >&2
  exit 2
fi

exec "$PYTHON_BIN" -m rightsrelay.acp_provider
