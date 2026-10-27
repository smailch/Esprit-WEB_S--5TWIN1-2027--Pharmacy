from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_DIR = Path(__file__).resolve().parents[3]
REPO_DIR = PROJECT_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_DIR / ".env", extra="ignore")

    # "rdflib" (graphe en mémoire, aucun service requis) ou "fuseki"
    sparql_backend: str = "rdflib"
    fuseki_url: str = "http://localhost:3030"
    fuseki_dataset: str = "pharma"
    fuseki_user: str = "admin"
    fuseki_password: str = "admin"

    ontology_file: Path = REPO_DIR / "ontologie" / "pharma.ttl"
    extension_dir: Path = PROJECT_DIR / "ontology-extension"

    cors_origins: str = "http://localhost:5174"

    def ontology_files(self) -> list[Path]:
        return [self.ontology_file, *sorted(self.extension_dir.glob("*.ttl"))]


@lru_cache
def get_settings() -> Settings:
    return Settings()
