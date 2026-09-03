#!/usr/bin/env bash

set -eu

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"

echo "Session 1 offline console: use Init Aurora, then Review (offline)."
echo "Open http://127.0.0.1:8080 and kill the launcher PID shown on the board."
exec "$PYTHON_BIN" -m rightsrelay serve
