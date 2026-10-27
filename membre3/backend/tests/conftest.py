import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config.settings import get_settings  # noqa: E402
from app.services.repository import Repository  # noqa: E402
from app.sparql.client import RdflibClient  # noqa: E402


@pytest.fixture(scope="session")
def base_client():
    return RdflibClient(get_settings().ontology_files())


@pytest.fixture
def client(base_client):
    base_client.reset()  # chaque test repart de l'état initial
    return base_client


@pytest.fixture
def repo(client):
    return Repository(client)
