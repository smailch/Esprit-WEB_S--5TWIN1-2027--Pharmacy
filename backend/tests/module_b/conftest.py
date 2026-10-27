"""Graphe isolé : les tests du module B n'écrivent pas dans ontologie/pharma.ttl."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.b_app import create_app
from app.b_config import PROJECT_ROOT, Settings

AUTH = {"X-Write-Token": "test-token"}


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    settings = Settings(
        ontology_ttl=PROJECT_ROOT / "ontologie" / "pharma.ttl",
        ontology_owl=PROJECT_ROOT / "ontologie" / "pharma.owl",
        queries_path=PROJECT_ROOT / "ontologie" / "requetes.sparql",
        graph_path=tmp_path / "graph.ttl",
        write_token="test-token",
        cors_origins="http://localhost:5173",
        nlp_engine="rules",
    )
    application = create_app(settings)
    with TestClient(application) as test_client:
        yield test_client
