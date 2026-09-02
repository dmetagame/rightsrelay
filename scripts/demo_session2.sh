#!/usr/bin/env bash

set -u

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"

"$PYTHON_BIN" -m rightsrelay status

"$PYTHON_BIN" -m rightsrelay attempt \
  --channel instagram \
  --paid \
  --territories US,UK \
  --date 2026-09-02
attempt_status=$?

if [ "$attempt_status" -ne 1 ]; then
  echo "Expected the release attempt to exit 1 while BLOCKED; got $attempt_status." >&2
  if [ "$attempt_status" -eq 0 ]; then
    exit 2
  fi
  exit "$attempt_status"
fi

echo "next: acquire-grant (not wired this turn)"
