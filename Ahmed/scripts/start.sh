#!/usr/bin/env sh
# Lance le backend (arrière-plan) puis le frontend. Usage (depuis Ahmed/) : sh scripts/start.sh
cd "$(dirname "$0")/.." || exit 1
(cd backend && .venv/bin/python -m uvicorn app.main:app --port 8000) &
BACK=$!
trap 'kill $BACK' EXIT INT TERM
echo "Backend : http://localhost:8000/docs  ·  Application : http://localhost:5174"
cd frontend && npm run dev
