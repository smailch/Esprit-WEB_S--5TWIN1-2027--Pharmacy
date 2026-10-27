#!/usr/bin/env bash
# Lance l'API (port 8000) et le site (port 5173). Ctrl+C arrête les deux.
cd "$(dirname "$0")/.."
VPY=backend/.venv/bin/python; [ -x "$VPY" ] || VPY=backend/.venv/Scripts/python.exe
[ -x "$VPY" ] || { echo "Lancez d'abord scripts/setup.sh"; exit 1; }
"$VPY" -m uvicorn app.main:app --app-dir backend --port 8000 &
API_PID=$!
trap 'kill $API_PID 2>/dev/null' EXIT
npm run dev
