#!/usr/bin/env sh
# Lance scripts/validate_ontology.py avec le Python du venv backend s'il existe.
cd "$(dirname "$0")/.." || exit 1
PY=backend/.venv/bin/python; [ -x "$PY" ] || PY=python3
exec "$PY" scripts/validate_ontology.py "$@"
