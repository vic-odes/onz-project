"""Schéma Pydantic pour la sortie LLM de génération de projet.

Sert deux buts :
1. **Détecter les sections manquantes** que le modèle aurait omises — sinon `docx_service`
   produit silencieusement un document avec des sections vides (le `.get()` permissif
   masque le bug).
2. **Garantir la shape passée au `docx_service`** — après validation, les champs nested
   absents reçoivent leur valeur par défaut, évitant les `KeyError` partiels.

Stratégie :
- **Top-level strict** : `introduction`, `cadre_logique`, `parties_prenantes`, etc.
  (le socle historique) doivent être présents dans la réponse du LLM. Le prompt l'exige.
- **Top-level optionnel** : les sections ajoutées ultérieurement (`theorie_changement`,
  `arbre_problemes`, `plan_financement`, `perennisation`, `note_conceptuelle`,
  `resume_executif`) ont un default — le prompt les demande, mais leur absence ne doit
  pas faire tomber la requête (même philosophie que `note_conceptuelle`).
- **Nested permissif** : les sous-champs ont des defaults (ex. `Risque.probabilite=""`)
  car le LLM est légitimement variable sur la granularité.
- `extra="ignore"` : on tolère les clés supplémentaires hallucinées par le modèle.
"""

from typing import List
from pydantic import BaseModel, ConfigDict, Field


class CadreLogiqueLigne(BaseModel):
    """Une ligne de la matrice du cadre logique au format UE/AFD."""

    model_config = ConfigDict(extra="ignore")
    niveau: str = ""  # Objectif global / Objectif spécifique / Résultat / Activité
    logique_intervention: str = ""
    indicateurs: str = ""
    baseline: str = ""  # valeur de référence
    cible: str = ""
    sources_verification: str = ""
    hypotheses: str = ""


class CadreLogique(BaseModel):
    model_config = ConfigDict(extra="ignore")
    objectif_global: str = ""
    objectifs_specifiques: List[str] = Field(default_factory=list)
    resultats: List[str] = Field(default_factory=list)
    activites: List[str] = Field(default_factory=list)
    indicateurs_smart: List[str] = Field(default_factory=list)
    sources_verification: List[str] = Field(default_factory=list)
    hypotheses: List[str] = Field(default_factory=list)
    # Matrice complète UE/AFD : Logique / Indicateur / Baseline / Cible / Source / Hypothèse
    matrice: List[CadreLogiqueLigne] = Field(default_factory=list)


class TheorieChangement(BaseModel):
    """Théorie du changement (ToC) — chaîne causale Problème → Impact."""

    model_config = ConfigDict(extra="ignore")
    narratif: str = ""
    probleme: str = ""
    causes: List[str] = Field(default_factory=list)
    activites: List[str] = Field(default_factory=list)
    resultats: List[str] = Field(default_factory=list)
    effets: List[str] = Field(default_factory=list)
    impact: str = ""
    hypotheses: List[str] = Field(default_factory=list)


class ArbreProblemes(BaseModel):
    """Arbre à problèmes (causes/conséquences) et son miroir positif, l'arbre à objectifs."""

    model_config = ConfigDict(extra="ignore")
    probleme_central: str = ""
    causes: List[str] = Field(default_factory=list)  # racines
    consequences: List[str] = Field(default_factory=list)  # branches
    # Arbre à objectifs (reformulation positive)
    objectif_central: str = ""
    moyens: List[str] = Field(default_factory=list)
    fins: List[str] = Field(default_factory=list)


class PartiePrenante(BaseModel):
    model_config = ConfigDict(extra="ignore")
    nom: str = ""
    role: str = ""
    interet: str = ""
    influence: str = ""  # attendu : Faible / Moyen / Fort
    # Quadrant de la matrice pouvoir/intérêt (ex. "Fort pouvoir / Fort intérêt")
    quadrant: str = ""


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


class BudgetAnnee(BaseModel):
    """Ventilation annuelle du budget (projet multi-annuel)."""

    model_config = ConfigDict(extra="ignore")
    annee: str = ""  # ex. "Année 1"
    montant_usd: float = 0.0
    pourcentage: float = 0.0


class BudgetPartenaire(BaseModel):
    """Ventilation du budget par partenaire porteur de la dépense."""

    model_config = ConfigDict(extra="ignore")
    partenaire: str = ""
    montant_usd: float = 0.0
    pourcentage: float = 0.0


class Budget(BaseModel):
    model_config = ConfigDict(extra="ignore")
    lignes: List[BudgetLigne] = Field(default_factory=list)
    total_usd: float = 0.0
    couts_directs: float = 0.0
    couts_indirects: float = 0.0
    # Ventilations détaillées (remarque #5 : budget multi-annuel / par partenaire)
    par_annee: List[BudgetAnnee] = Field(default_factory=list)
    par_partenaire: List[BudgetPartenaire] = Field(default_factory=list)


class LigneFinancement(BaseModel):
    model_config = ConfigDict(extra="ignore")
    financeur: str = ""
    type: str = ""  # Subvention / Cofinancement / Apport propre / Valorisation
    montant_usd: float = 0.0
    pourcentage: float = 0.0


class PlanFinancement(BaseModel):
    """Plan de financement (remarque #6) — répartition par financeur."""

    model_config = ConfigDict(extra="ignore")
    lignes: List[LigneFinancement] = Field(default_factory=list)
    total_usd: float = 0.0
    taux_cofinancement: str = ""


class AnalyseCoutBenefice(BaseModel):
    model_config = ConfigDict(extra="ignore")
    van: float = 0.0  # Valeur actuelle nette (USD)
    tri: float = 0.0  # Taux de rentabilité interne (%)
    ratio_cout_benefice: float = 0.0
    delai_retour_annees: float = 0.0  # Délai de récupération (années)
    benefices_annee1_usd: float = 0.0  # Estimation des bénéfices sur 1 an (approche financière)
    scenario_central: str = ""
    scenario_pessimiste: str = ""
    analyse_sensibilite: str = ""
    justification: str = ""


class Risque(BaseModel):
    model_config = ConfigDict(extra="ignore")
    risque: str = ""
    categorie: str = ""  # Financier / Politique / Climatique / Opérationnel / Technique
    probabilite: str = ""  # Faible / Moyen / Élevé
    impact: str = ""  # Faible / Moyen / Élevé
    niveau: str = ""  # score global : Faible / Moyen / Élevé / Critique
    mitigation: str = ""


class GeneratedContent(BaseModel):
    """Top-level strict pour le socle historique ; optionnel pour les sections ajoutées."""

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
    # --- Sections ajoutées (lot A) : demandées par le prompt, mais leur absence
    #     ne doit pas provoquer un 502 (même politique que note_conceptuelle). ---
    theorie_changement: TheorieChangement = Field(default_factory=TheorieChangement)
    arbre_problemes: ArbreProblemes = Field(default_factory=ArbreProblemes)
    plan_financement: PlanFinancement = Field(default_factory=PlanFinancement)
    perennisation: str = ""  # piloté par le flag `inclure_perennisation` du formulaire
    # Optionnels historiques — pilotés par `generer_note_conceptuelle` /
    # `inclure_resume_executif` du formulaire ; le LLM peut renvoyer "" si désactivés.
    note_conceptuelle: str = ""
    resume_executif: str = ""
