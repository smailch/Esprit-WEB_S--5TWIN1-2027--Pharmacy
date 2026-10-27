"""Schémas d'entrée. Les champs inconnus sont refusés."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EffectWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    label: str | None = Field(default=None, max_length=120)
    type: str | None = None
    gravite: str | None = None
    frequence: str | None = Field(default=None, max_length=60)
    molecules: list[str] | None = None


class ContraindicationWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    label: str | None = Field(default=None, max_length=120)
    type: str | None = None
    niveauRisque: str | None = None
    molecules: list[str] | None = None
    pathologies: list[str] | None = None


class SparqlBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=8000)


class AskBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=2, max_length=500)
