#!/usr/bin/env bash
# Installation (macOS / Linux / Git Bash)
set -e
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
command -v "$PY" >/dev/null || PY=python
"$PY" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" || { echo "Python 3.11+ requis"; exit 1; }
command -v npm >/dev/null || { echo "Node.js 18+ requis"; exit 1; }
[ -d backend/.venv ] || "$PY" -m venv backend/.venv
VPY=backend/.venv/bin/python; [ -x "$VPY" ] || VPY=backend/.venv/Scripts/python.exe
"$VPY" -m pip install --upgrade pip -q
"$VPY" -m pip install -r backend/requirements.txt
npm install --no-audit --no-fund
echo "Installation terminée. Lancez : scripts/start.sh"
