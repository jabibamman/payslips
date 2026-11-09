#!/bin/bash
set -e
cd "$(dirname "$0")"
set -a
source ./.env
set +a
PY=.venv/bin/python
[ -x "$PY" ] || PY=python3
"$PY" fetch.py
if [ -n "${RCLONE_DEST:-}" ]; then
  rclone copy "${OUT_DIR:-./out}" "$RCLONE_DEST" --ignore-existing
fi
