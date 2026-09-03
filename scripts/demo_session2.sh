#!/usr/bin/env bash

set -eu

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
PACKET="release-packets/campaign-aurora-neon-drive.json"

if [ -e "$PACKET" ]; then
  echo "Refusing to start: $PACKET already exists." >&2
  exit 2
fi

"$PYTHON_BIN" -m rightsrelay status

set +e
"$PYTHON_BIN" -m rightsrelay attempt \
  --channel instagram \
  --paid \
  --territories US,UK \
  --date 2026-09-02
attempt_status=$?
set -e

if [ "$attempt_status" -ne 1 ]; then
  echo "Expected the release attempt to exit 1 while BLOCKED; got $attempt_status." >&2
  if [ "$attempt_status" -eq 0 ]; then
    exit 2
  fi
  exit "$attempt_status"
fi

if [ -e "$PACKET" ]; then
  echo "Blocked attempt unexpectedly wrote $PACKET." >&2
  exit 2
fi

"$PYTHON_BIN" -m rightsrelay acquire-grant

"$PYTHON_BIN" -m rightsrelay attempt \
  --channel instagram \
  --paid \
  --territories US,UK \
  --date 2026-09-02

if [ ! -f "$PACKET" ]; then
  echo "Cleared attempt did not write $PACKET." >&2
  exit 2
fi

"$PYTHON_BIN" -m rightsrelay status
