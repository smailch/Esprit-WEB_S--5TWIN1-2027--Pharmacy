"""Modèles Pydantic : validation des données entrantes du CRUD."""
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .queries import ID_PATTERN, MOLECULE_CLASSES


def _check_ids(values: list[str]) -> list[str]:
    for v in values:
        if not ID_PATTERN.match(v):
            raise ValueError(f"Identifiant invalide : {v}")
    return values


class MoleculeIn(BaseModel):
    nom: str = Field(min_length=2, max_length=80, description="Nom affiché (rdfs:label)")
    classe: str = Field(description="Classe de la molécule")
    codeATC: str | None = Field(default=None, pattern=r"^[A-Z]\d{2}[A-Z]{2}\d{2}$", description="Ex. N02BE01")
    doseMaxJourMg: float | None = Field(default=None, gt=0, le=100000)
    effets: list[str] = []
    contreIndications: list[str] = []
    interactions: list[str] = []

    @field_validator("classe")
    @classmethod
    def classe_valide(cls, v):
        if v not in MOLECULE_CLASSES:
            raise ValueError(f"Classe inconnue. Valeurs possibles : {', '.join(MOLECULE_CLASSES)}")
        return v

    @field_validator("effets", "contreIndications", "interactions")
    @classmethod
    def ids_valides(cls, v):
        return _check_ids(v)


class MedicamentIn(BaseModel):
    nomCommercial: str = Field(min_length=2, max_length=80)
    type: Literal["Princeps", "Generique"]
    dosage: str = Field(min_length=1, max_length=30, description="Ex. 500 mg")
    formeGalenique: str = Field(min_length=2, max_length=30, description="comprimé, gélule, sirop…")
    surOrdonnance: bool
    prixDT: float = Field(ge=0, le=10000)
    molecules: list[str] = Field(min_length=1, description="Au moins une molécule (axiome de l'ontologie)")
    indications: list[str] = []

    @field_validator("molecules", "indications")
    @classmethod
    def ids_valides(cls, v):
        return _check_ids(v)


class InteractionsIn(BaseModel):
    medicaments: list[str] = Field(min_length=2, max_length=10)

    @field_validator("medicaments")
    @classmethod
    def ids_valides(cls, v):
        return _check_ids(v)


class SparqlIn(BaseModel):
    requete: str = Field(min_length=5, max_length=5000)
