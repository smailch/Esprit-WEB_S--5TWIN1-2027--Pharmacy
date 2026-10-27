from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

MEMBRE3_DIR = Path(__file__).resolve().parents[3]
REPO_DIR = MEMBRE3_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=MEMBRE3_DIR / ".env", extra="ignore")

    # "rdflib" (graphe en mémoire, aucun service requis) ou "fuseki"
    sparql_backend: str = "rdflib"
    fuseki_url: str = "http://localhost:3030"
    fuseki_dataset: str = "pharma"
    fuseki_user: str = "admin"
    fuseki_password: str = "admin"

    ontology_file: Path = REPO_DIR / "ontologie" / "pharma.ttl"
    extension_dir: Path = MEMBRE3_DIR / "ontology-extension"

    cors_origins: str = "http://localhost:5173"

    def ontology_files(self) -> list[Path]:
        return [self.ontology_file, *sorted(self.extension_dir.glob("*.ttl"))]


@lru_cache
def get_settings() -> Settings:
    return Settings()
