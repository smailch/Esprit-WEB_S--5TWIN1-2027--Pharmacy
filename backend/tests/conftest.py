import os
import sys
import tempfile
from pathlib import Path

# Les tests écrivent dans un fichier runtime temporaire : la base de démo n'est jamais touchée.
os.environ["RUNTIME_PATH"] = str(Path(tempfile.mkdtemp()) / "runtime_test.ttl")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    from app.main import app
    return TestClient(app)


@pytest.fixture()
def fresh(client):
    client.post("/api/admin/reset")
    yield client
    client.post("/api/admin/reset")
