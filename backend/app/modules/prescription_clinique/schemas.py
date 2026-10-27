"""Modèles Pydantic du module D : validation des entrées du CRUD (types, littéraux, références)."""
from datetime import date

from pydantic import BaseModel, Field, field_validator, model_validator

from .common import ID_PATTERN
from .queries import DONNEE_LEAVES, PRESCRIPTION_TYPES


def _check_ids(values: list[str]) -> list[str]:
    for v in values:
        if not ID_PATTERN.match(v):
            raise ValueError(f"Identifiant invalide : {v}")
    return values


def _check_date(v: date) -> date:
    if v < date(1900, 1, 1) or v > date.today():
        raise ValueError("La date doit être comprise entre 1900-01-01 et aujourd'hui")
    return v


class PrescriptionIn(BaseModel):
    type: str = Field(description="Sous-classe de :Prescription (ex. PrescriptionNormale, RenouvellementCourt)")
    datePrescription: date = Field(description="xsd:date, format AAAA-MM-JJ")
    dureeJours: int = Field(ge=1, le=3650, description="Durée du traitement en jours")
    posologie: str = Field(min_length=2, max_length=200)
    medecin: str = Field(description="Individu :Medecin (prescritPar, propriété fonctionnelle)")
    patient: str = Field(description="Individu :Patient (concernePatient, propriété fonctionnelle)")
    medicaments: list[str] = Field(min_length=1, max_length=10, description="Au moins un médicament (restriction OWL min 1)")
    pharmacien: str | None = Field(default=None, description="Individu :Pharmacien (estDelivreePar), facultatif")
    libelle: str | None = Field(default=None, max_length=120, description="rdfs:label ; par défaut « Ordonnance NNN »")

    @field_validator("type")
    @classmethod
    def type_valide(cls, v):
        if v not in PRESCRIPTION_TYPES:
            raise ValueError(f"Type inconnu. Valeurs possibles : {', '.join(PRESCRIPTION_TYPES)}")
        return v

    @field_validator("datePrescription")
    @classmethod
    def date_plausible(cls, v):
        return _check_date(v)

    @field_validator("medecin", "patient")
    @classmethod
    def id_valide(cls, v):
        return _check_ids([v])[0]

    @field_validator("pharmacien")
    @classmethod
    def pharmacien_valide(cls, v):
        return _check_ids([v])[0] if v else None

    @field_validator("medicaments")
    @classmethod
    def medicaments_valides(cls, v):
        if len(set(v)) != len(v):
            raise ValueError("Un médicament ne peut figurer qu'une fois sur l'ordonnance")
        return _check_ids(v)

    @model_validator(mode="after")
    def coherence_duree(self):
        # Libellés de l'ontologie : RenouvellementCourt (≤ 3 mois), RenouvellementLong (> 3 mois).
        if self.type == "RenouvellementCourt" and self.dureeJours > 90:
            raise ValueError("Un renouvellement court dure au plus 90 jours (≤ 3 mois)")
        if self.type == "RenouvellementLong" and self.dureeJours <= 90:
            raise ValueError("Un renouvellement long dure plus de 90 jours (> 3 mois)")
        return self


class DonneeCliniqueIn(BaseModel):
    type: str = Field(description="SigneVital, AnalyseBiologique, Allergie ou Antecedent")
    patient: str = Field(description="Individu :Patient (estDonneeDe, propriété fonctionnelle)")
    libelle: str = Field(min_length=2, max_length=120, description="rdfs:label, ex. « Glycémie à jeun »")
    dateMesure: date = Field(description="xsd:date de la mesure ou du constat")
    valeur: float | None = Field(default=None, ge=-1000, le=100000, description="Examen clinique uniquement (:valeur)")
    unite: str | None = Field(default=None, max_length=20, description="Examen clinique uniquement (:unite)")
    molecule: str | None = Field(default=None, description="Allergie uniquement (:allergiqueA → :Molecule)")
    pathologie: str | None = Field(default=None, description="Antécédent uniquement (:porteSur → :Pathologie)")

    @field_validator("type")
    @classmethod
    def type_valide(cls, v):
        if v not in DONNEE_LEAVES:
            raise ValueError(f"Type inconnu. Valeurs possibles : {', '.join(DONNEE_LEAVES)}")
        return v

    @field_validator("dateMesure")
    @classmethod
    def date_plausible(cls, v):
        return _check_date(v)

    @field_validator("patient")
    @classmethod
    def id_valide(cls, v):
        return _check_ids([v])[0]

    @field_validator("molecule", "pathologie")
    @classmethod
    def ref_valide(cls, v):
        return _check_ids([v])[0] if v else None

    @model_validator(mode="after")
    def champs_par_type(self):
        # Domaines de l'ontologie : valeur/unite → ExamenClinique, allergiqueA → Allergie, porteSur → Antecedent.
        examen = DONNEE_LEAVES[self.type] == "ExamenClinique"
        if examen and (self.valeur is None or not self.unite):
            raise ValueError("Un examen clinique (signe vital, analyse) exige une valeur et une unité")
        if not examen and (self.valeur is not None or self.unite):
            raise ValueError("Valeur et unité ne concernent que les examens cliniques (domaine de :valeur et :unite)")
        if (self.type == "Allergie") != bool(self.molecule):
            raise ValueError("La molécule (:allergiqueA) est obligatoire pour une allergie et réservée à ce type")
        if (self.type == "Antecedent") != bool(self.pathologie):
            raise ValueError("La pathologie (:porteSur) est obligatoire pour un antécédent et réservée à ce type")
        return self


class SparqlQueryIn(BaseModel):
    requete: str = Field(min_length=5, max_length=5000)
    limite: int = Field(default=500, ge=1, le=2000, description="Nombre maximal de lignes renvoyées")
