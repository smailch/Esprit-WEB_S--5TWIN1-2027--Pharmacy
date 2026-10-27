"""Schémas Pydantic d'entrée/sortie de l'API (validation = axiomes OWL côté API)."""
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

Sexe = Literal["M", "F"]
TypePathologie = Literal["InfectionAigue", "DouleurAigue", "MaladieMetabolique", "InsuffisanceOrgane",
                         "MaladieAigue", "MaladieChronique"]
Nom = Field(min_length=1, max_length=80)
CIM10 = Field(pattern=r"^[A-Z][0-9]{2}(\.[0-9]{1,2})?$", examples=["J11"])
Age = Field(ge=0, le=120)


class Error(BaseModel):
    code: str
    message: str
    details: object | None = None


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class Created(BaseModel):
    id: str


class Out(BaseModel):
    model_config = ConfigDict(extra="allow")


# ---------- Patients ----------
class PatientCreate(BaseModel):
    prenom: str = Nom
    nom: str = Nom
    age: int = Age
    sexe: Sexe
    pathologies: list[str] = []


class PatientUpdate(BaseModel):
    label: str | None = Field(None, min_length=1, max_length=120)
    nom: str | None = Field(None, min_length=1, max_length=80)
    age: int | None = Field(None, ge=0, le=120)
    sexe: Sexe | None = None


class PatientItem(Out):
    id: str
    label: str
    nom: str | None = None
    age: int
    sexe: str | None = None
    classe: Literal["PatientEnfant", "PatientAdulte"]
    asserte: bool
    nbPathologies: int = 0


class PatientDetail(Out):
    id: str
    label: str
    age: int
    classe: str
    asserte: bool
    pathologies: list[dict]
    prescriptions: list[dict]
    alertes: list[dict]


# ---------- Professionnels ----------
class ProCreate(BaseModel):
    nom: str = Nom
    specialite: str = Field(min_length=1, max_length=80)
    label: str | None = Field(None, max_length=120)


class ProUpdate(BaseModel):
    label: str | None = Field(None, min_length=1, max_length=120)
    nom: str | None = Field(None, min_length=1, max_length=80)
    specialite: str | None = Field(None, min_length=1, max_length=80)


class ProItem(Out):
    id: str
    label: str
    nom: str | None = None
    specialite: str | None = None
    nbPrescriptions: int = 0


# ---------- Pathologies ----------
class PathologieCreate(BaseModel):
    label: str = Field(min_length=2, max_length=120)
    type: TypePathologie
    code: str = CIM10


class PathologieUpdate(BaseModel):
    label: str | None = Field(None, min_length=2, max_length=120)
    code: str | None = Field(None, pattern=r"^[A-Z][0-9]{2}(\.[0-9]{1,2})?$")


class PathologieItem(Out):
    id: str
    label: str
    code: str | None = None
    type: str
    famille: str | None = None
    nbPatients: int = 0


# ---------- Console SPARQL / NLP ----------
class SparqlRequest(BaseModel):
    requete: str = Field(min_length=1, max_length=20000)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
