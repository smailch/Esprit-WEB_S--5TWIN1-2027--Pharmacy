#!/usr/bin/env sh
# Installation complète (Linux/macOS) : venv Python, dépendances épinglées, modèles NLP, dépendances front.
# Usage (depuis Ahmed/) : sh scripts/setup.sh
set -e
cd "$(dirname "$0")/.."
[ -f .env ] || cp .env.example .env
cd backend
[ -d .venv ] || python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/setup_models.py
cd ../frontend
npm ci --no-audit --no-fund
echo "Installation terminée. Lancer : sh scripts/start.sh"
