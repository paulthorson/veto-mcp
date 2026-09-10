#!/usr/bin/env bash
# Idempotent Cloud Agent setup for job-apply-mcp (Veto).
#
# Creates the Python virtualenv the project expects (.venv), installs the
# pinned dependencies, and installs the Playwright browsers used by the
# Phase 2 browser-apply path and the real-browser e2e tests. Safe to run
# repeatedly: each step converges instead of duplicating state.
set -euo pipefail

cd "$(dirname "$0")/.."

# The base image ships CPython 3.12 but not the venv module on Debian/Ubuntu.
if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq python3-venv || sudo apt-get install -y -qq python3.12-venv
fi

if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

# Chromium (default engine) + Firefox, with the OS libraries they need.
# --with-deps escalates via sudo for the apt step when not running as root.
.venv/bin/python -m playwright install --with-deps chromium firefox

echo "job-apply-mcp environment ready: $(.venv/bin/python --version)"
