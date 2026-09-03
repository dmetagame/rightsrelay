#!/usr/bin/env bash

set -eu

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
PACKET="release-packets/campaign-aurora-neon-drive.json"

if [ -e "$PACKET" ]; then
  echo "Refusing to start: $PACKET already exists." >&2
  exit 2
fi

echo "Session 2 starts a new Python launcher process."
echo "Open http://127.0.0.1:8080; confirm the new PID and recalled authorization."
exec "$PYTHON_BIN" -m rightsrelay serve
