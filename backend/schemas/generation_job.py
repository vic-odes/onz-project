"""Schéma Pydantic pour le suivi d'une génération de document en arrière-plan.

Même philosophie que `schemas/financement.py` : la génération (appel LLM,
potentiellement avec PDFs natifs, jusqu'à 8000+ tokens de sortie) peut prendre
plus d'une minute — trop long pour une requête HTTP bloquante fiable côté
navigateur. Le frontend sonde `GET /api/generate/etat/{id}` jusqu'à
`status != "en_cours"`, puis télécharge le document via
`GET /api/projects/{project_id}/download`.
"""

from typing import Literal, Optional
from datetime import datetime

from pydantic import BaseModel, ConfigDict

StatutGeneration = Literal["en_cours", "termine", "erreur"]


class GenerationJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: StatutGeneration
    erreur: Optional[str] = None
    project_id: Optional[int] = None
    created_at: datetime
