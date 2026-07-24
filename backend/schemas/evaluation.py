"""Schéma Pydantic pour la sortie LLM d'évaluation d'un projet (lot B).

Deux volets :
- `analyse_bailleur` : analyse automatique du bailleur ciblé + score de compatibilité (#1).
- `notation` : notation type comité de sélection + recommandations (#14).

Mêmes principes que `schemas/generated.py` : top-level optionnel (default) pour ne
pas provoquer de 502 si le modèle omet un volet, nested permissif, `extra="ignore"`.
"""

from typing import List
from pydantic import BaseModel, ConfigDict, Field


class AnalyseBailleur(BaseModel):
    model_config = ConfigDict(extra="ignore")
    nom: str = ""
    priorites: List[str] = Field(default_factory=list)
    criteres_eligibilite: List[str] = Field(default_factory=list)
    montant_max_finançable: str = ""
    taux_cofinancement: str = ""
    score_compatibilite: int = 0  # pourcentage 0-100
    risques_rejet: List[str] = Field(default_factory=list)


class CritereNotation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    critere: str = ""  # Pertinence / Efficacité / Impact / Durabilité / Budget / Innovation
    note_sur_20: float = 0.0
    commentaire: str = ""


class Notation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    criteres: List[CritereNotation] = Field(default_factory=list)
    score_total_sur_100: float = 0.0
    points_forts: List[str] = Field(default_factory=list)
    axes_amelioration: List[str] = Field(default_factory=list)
    recommandation: str = ""


class Evaluation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    analyse_bailleur: AnalyseBailleur = Field(default_factory=AnalyseBailleur)
    notation: Notation = Field(default_factory=Notation)
