"""Schéma Pydantic pour la note conceptuelle (concept note) — lot B, remarque #12.

Livrable autonome, orienté bailleur, condensé (2-4 pages). Mêmes principes que les
autres schémas de sortie LLM : champs optionnels avec defaults (permissif),
`extra="ignore"`. Rendu par `docx_service.create_note_conceptuelle_document`.
"""

from typing import List
from pydantic import BaseModel, ConfigDict, Field


class NoteConceptuelle(BaseModel):
    model_config = ConfigDict(extra="ignore")
    titre: str = ""
    resume_executif: str = ""  # synthèse percutante (~150 mots)
    contexte: str = ""
    justification: str = ""  # pertinence + alignement avec les priorités du bailleur
    objectif_global: str = ""
    objectifs_specifiques: List[str] = Field(default_factory=list)
    resultats_attendus: List[str] = Field(default_factory=list)
    activites_principales: List[str] = Field(default_factory=list)
    beneficiaires: str = ""
    budget_synthese: str = ""  # budget indicatif + plan de financement en une synthèse
    partenaires: List[str] = Field(default_factory=list)
    durabilite: str = ""
    conclusion: str = ""  # appel à l'action adressé au bailleur
