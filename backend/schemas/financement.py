"""Schéma Pydantic pour la sortie LLM de recherche de financements.

Même philosophie que `schemas/generated.py`/`schemas/evaluation.py` : nested permissif
avec defaults (le LLM est variable sur la granularité), `extra="ignore"` pour tolérer les
clés hallucinées. Contrairement à `GeneratedContent`, il n'y a pas de clé top-level
« obligatoire » : une liste d'opportunités vide est un résultat valide (aucune opportunité
crédible trouvée), pas une erreur.
"""

from typing import List, Literal, Optional
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

Categorie = Literal["tres_compatible", "compatible", "a_etudier", "faible", "non_eligible"]
Fiabilite = Literal["verifie", "a_confirmer", "information_non_disponible"]
StatutRecherche = Literal["en_cours", "termine", "erreur"]

# Valeur du champ `bailleur` posée quand aucun bailleur précis n'est visé — doit
# rester identique à `RECHERCHE_BAILLEUR_LABEL` dans frontend/lib/constants.ts.
RECHERCHE_BAILLEUR_LABEL = "Recherche automatique de bailleur"


class ImporterProjetRequest(BaseModel):
    """Champs extraits d'un PDF externe (via /api/documents/prefill) pour créer
    un projet minimal — sans document généré — et lancer une recherche de
    financement. Permet de rechercher un financement pour un projet monté hors
    de l'application."""

    nom: str = Field(..., min_length=1)
    pays: str = Field(..., min_length=1)
    secteur: str = ""
    probleme_principal: str = ""
    objectif_global: str = ""
    budget_total: Optional[float] = None
    duree_mois: Optional[int] = None


class OpportuniteFinancement(BaseModel):
    model_config = ConfigDict(extra="ignore")

    bailleur: str = ""
    programme: str = ""
    nom_appel: str = ""
    description: str = ""
    categorie: Categorie = "a_etudier"
    score_compatibilite: int = 0  # 0-100
    montant_min: Optional[float] = None
    montant_max: Optional[float] = None
    devise: str = ""
    taux_cofinancement_max: str = ""
    date_limite: str = ""  # "JJ/MM/AAAA" ou "" si inconnue/permanent
    depot_permanent: bool = False
    raisons_compatibilite: List[str] = Field(default_factory=list)
    points_vigilance: List[str] = Field(default_factory=list)
    conditions_principales: List[str] = Field(default_factory=list)
    source_officielle: str = ""
    lien_candidature: str = ""
    fiabilite: Fiabilite = "information_non_disponible"
    date_verification: str = ""


class ResultatsFinancement(BaseModel):
    model_config = ConfigDict(extra="ignore")

    resume: str = ""
    opportunites: List[OpportuniteFinancement] = Field(default_factory=list)


class RechercheFinancementResponse(BaseModel):
    """Réponse de l'API pour une recherche persistée.

    La recherche s'exécute en tâche de fond (l'appel LLM + recherche web peut
    prendre plusieurs minutes) — `status="en_cours"` tant qu'elle n'est pas
    terminée, `resultats` restant vide dans ce cas. Le frontend sonde
    `GET /api/financements/{id}` jusqu'à `status != "en_cours"`.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    project_nom: str
    recherche_live: bool
    status: StatutRecherche
    erreur: Optional[str] = None
    created_at: datetime
    resultats: ResultatsFinancement


class RechercheFinancementSummary(BaseModel):
    """Résumé léger pour lister les recherches passées d'un projet."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    recherche_live: bool
    status: StatutRecherche
    created_at: datetime
    nb_opportunites: int
    resume: str
