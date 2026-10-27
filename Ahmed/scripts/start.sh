#!/usr/bin/env sh
# Lance mon backend (port 8001) puis le projet React commun. → http://localhost:5173/ahmed.html
cd "$(dirname "$0")/.." || exit 1
(cd backend && .venv/bin/python -m uvicorn app.main:app --port 8001) &
BACK=$!
trap 'kill $BACK' EXIT INT TERM
echo "API : http://localhost:8001/docs  ·  Application : http://localhost:5173/ahmed.html"
cd .. && npm run dev
