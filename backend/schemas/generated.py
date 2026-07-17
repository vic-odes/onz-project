"""Schéma Pydantic pour la sortie LLM de génération de projet.

Sert deux buts :
1. **Détecter les sections manquantes** que le modèle aurait omises — sinon `docx_service`
   produit silencieusement un document avec des sections vides (le `.get()` permissif
   masque le bug).
2. **Garantir la shape passée au `docx_service`** — après validation, les champs nested
   absents reçoivent leur valeur par défaut, évitant les `KeyError` partiels.

Stratégie :
- **Top-level strict** : `introduction`, `cadre_logique`, `parties_prenantes`, etc.
  doivent être présents dans la réponse du LLM. Le prompt l'exige explicitement.
- **Nested permissif** : les sous-champs ont des defaults (ex. `Risque.probabilite=""`)
  car le LLM est légitimement variable sur la granularité.
- `extra="ignore"` : on tolère les clés supplémentaires hallucinées par le modèle.
"""

from typing import List
from pydantic import BaseModel, ConfigDict, Field


class CadreLogique(BaseModel):
    model_config = ConfigDict(extra="ignore")
    objectif_global: str = ""
    objectifs_specifiques: List[str] = Field(default_factory=list)
    resultats: List[str] = Field(default_factory=list)
    activites: List[str] = Field(default_factory=list)
    indicateurs_smart: List[str] = Field(default_factory=list)
    sources_verification: List[str] = Field(default_factory=list)
    hypotheses: List[str] = Field(default_factory=list)


class PartiePrenante(BaseModel):
    model_config = ConfigDict(extra="ignore")
    nom: str = ""
    role: str = ""
    interet: str = ""
    influence: str = ""  # attendu : Faible / Moyen / Fort


class ActiviteDetaillee(BaseModel):
    model_config = ConfigDict(extra="ignore")
    titre: str = ""
    description: str = ""
    responsable: str = ""
    duree: str = ""
    objectif_lie: str = ""


class ChronogrammeItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    trimestre: str = ""
    activites: List[str] = Field(default_factory=list)


class BudgetLigne(BaseModel):
    model_config = ConfigDict(extra="ignore")
    categorie: str = ""
    description: str = ""
    montant_usd: float = 0.0
    pourcentage: float = 0.0


class Budget(BaseModel):
    model_config = ConfigDict(extra="ignore")
    lignes: List[BudgetLigne] = Field(default_factory=list)
    total_usd: float = 0.0
    couts_directs: float = 0.0
    couts_indirects: float = 0.0


class AnalyseCoutBenefice(BaseModel):
    model_config = ConfigDict(extra="ignore")
    van: float = 0.0
    ratio_cout_benefice: float = 0.0
    scenario_central: str = ""
    scenario_pessimiste: str = ""
    justification: str = ""


class Risque(BaseModel):
    model_config = ConfigDict(extra="ignore")
    risque: str = ""
    probabilite: str = ""  # Faible / Moyen / Élevé
    impact: str = ""  # Faible / Moyen / Élevé
    mitigation: str = ""


class GeneratedContent(BaseModel):
    """Top-level strict — toute clé manquante lève ValidationError."""

    model_config = ConfigDict(extra="ignore")

    introduction: str
    cadre_logique: CadreLogique
    parties_prenantes: List[PartiePrenante]
    activites_detaillees: List[ActiviteDetaillee]
    chronogramme: List[ChronogrammeItem]
    budget: Budget
    analyse_cout_benefice: AnalyseCoutBenefice
    risques: List[Risque]
    communication: str
    # Optionnels — pilotés par les flags `generer_note_conceptuelle` /
    # `inclure_resume_executif` du formulaire ; le LLM peut renvoyer "" si désactivés.
    note_conceptuelle: str = ""
    resume_executif: str = ""
