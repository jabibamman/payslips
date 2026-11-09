#!/bin/bash
set -e
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
if [ "$(uname)" = "Linux" ] && [ "$(id -u)" = "0" ]; then
  .venv/bin/playwright install --with-deps chromium   # dependances systeme (LXC/Debian)
else
  .venv/bin/playwright install chromium
fi
[ -f .env ] || cp .env.example .env
chmod 600 .env
command -v rclone >/dev/null || echo "ATTENTION: rclone absent (brew install rclone / apt install rclone)"
.venv/bin/python -m pytest -q
