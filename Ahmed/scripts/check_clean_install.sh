#!/usr/bin/env sh
# Vérifie qu'un clone NEUF fonctionne : clone (état commité) → installation → tests → lint/build → démarrage → /api/health.
# Usage (depuis Ahmed/) : sh scripts/check_clean_install.sh [source] [branche]
set -e
SRC=${1:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel)}
BRANCH=${2:-$(git -C "$(dirname "$0")" rev-parse --abbrev-ref HEAD)}
TMP=$(mktemp -d)
trap 'kill $SERVER 2>/dev/null; rm -rf "$TMP"' EXIT

echo "=== Clone de $SRC ($BRANCH) dans $TMP"
git clone --quiet --branch "$BRANCH" "$SRC" "$TMP/repo"
APP="$TMP/repo/Ahmed"

echo "=== Installation"
sh "$APP/scripts/setup.sh"

echo "=== Tests backend"
cd "$APP/backend" && .venv/bin/python -m pytest -q

echo "=== Lint + build frontend"
cd "$APP/frontend" && npm run lint && npm run build

echo "=== Démarrage de l'API et appel /api/health"
cd "$APP/backend"
.venv/bin/python -m uvicorn app.main:app --port 8765 >/dev/null 2>&1 &
SERVER=$!
for i in $(seq 1 30); do curl -sf http://localhost:8765/api/health && break; sleep 1; done
curl -sf http://localhost:8765/api/health >/dev/null || { echo "ÉCHEC : /api/health"; exit 1; }
echo
echo "✓ Installation propre validée"
