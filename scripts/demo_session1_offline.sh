#!/usr/bin/env bash

set -eu

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"

"$PYTHON_BIN" -m rightsrelay status
"$PYTHON_BIN" -m rightsrelay init-aurora
"$PYTHON_BIN" -m rightsrelay review-limited
"$PYTHON_BIN" -m rightsrelay status

echo "Session 1 offline shell PID: $$"
echo "Operator: record this PID, then kill this shell before starting Session 2."
read -r -p "Waiting for process kill (press Enter only outside the recorded take): " _
