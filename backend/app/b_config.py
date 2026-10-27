"""Réglages du module B. N'écrase pas la configuration commune de l'application."""

from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings:
    def __init__(
        self,
        ontology_ttl: Path | None = None,
        ontology_owl: Path | None = None,
        queries_path: Path | None = None,
        graph_path: Path | None = None,
        cors_origins: str | None = None,
        write_token: str | None = None,
        sparql_max_length: int | None = None,
        sparql_max_rows: int | None = None,
        nlp_engine: str | None = None,
        ollama_url: str | None = None,
        ollama_model: str | None = None,
        ollama_timeout: float | None = None,
    ) -> None:
        self.ontology_ttl = Path(ontology_ttl or PROJECT_ROOT / "ontologie" / "pharma.ttl")
        self.ontology_owl = Path(ontology_owl or PROJECT_ROOT / "ontologie" / "pharma.owl")
        self.queries_path = Path(queries_path or PROJECT_ROOT / "ontologie" / "requetes.sparql")
        self.graph_path = Path(graph_path or BACKEND_DIR / "data" / "graph.ttl")
        self.cors_origins = cors_origins or os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173",
        )
        self.write_token = write_token if write_token is not None else os.getenv("WRITE_TOKEN", "neocoders-module-b")
        self.sparql_max_length = int(sparql_max_length or os.getenv("SPARQL_MAX_LENGTH", "8000"))
        self.sparql_max_rows = int(sparql_max_rows or os.getenv("SPARQL_MAX_ROWS", "200"))
        self.nlp_engine = nlp_engine or os.getenv("NLP_ENGINE", "qwen")
        self.ollama_url = ollama_url or os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
        self.ollama_model = ollama_model or os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
        self.ollama_timeout = float(ollama_timeout or os.getenv("OLLAMA_TIMEOUT", "180"))


def get_settings() -> Settings:
    return Settings()
