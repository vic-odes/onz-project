"""Tests de fumée du rendu Word.

Objectif : s'assurer que `create_word_document` produit un .docx valide (signature
ZIP `PK`) sur un contenu complet ET sur un contenu minimal, et qu'il ne casse pas
quand les sections optionnelles (lot A) sont absentes.
On ne parse pas le contenu XML — on vérifie que le rendu ne lève pas et qu'un
document ouvrable est produit.
"""
from schemas.generated import GeneratedContent
from services import docx_service


def _full_generated() -> dict:
    """Contenu couvrant toutes les sections, y compris celles du lot A."""
    payload = {
        "introduction": "Contexte du projet au Mali.",
        "arbre_problemes": {
            "probleme_central": "Accès limité à l'eau potable",
            "causes": ["Infrastructures vétustes", "Faible gouvernance"],
            "consequences": ["Maladies hydriques", "Absentéisme scolaire"],
            "objectif_central": "Améliorer l'accès à l'eau potable",
            "moyens": ["Réhabiliter les forages"],
            "fins": ["Réduire les maladies hydriques"],
        },
        "theorie_changement": {
            "narratif": "Si nous réhabilitons les forages, alors...",
            "probleme": "Accès limité à l'eau",
            "causes": ["Forages en panne"],
            "activites": ["Réhabilitation", "Formation"],
            "resultats": ["10 forages fonctionnels"],
            "effets": ["Baisse des maladies"],
            "impact": "Amélioration durable de la santé",
            "hypotheses": ["Stabilité politique"],
        },
        "cadre_logique": {
            "objectif_global": "Améliorer l'accès à l'eau",
            "objectifs_specifiques": ["OS1", "OS2"],
            "resultats": ["R1"],
            "activites": ["A1"],
            "indicateurs_smart": ["Nb forages - 0 - 10 - 24 mois"],
            "sources_verification": ["Rapports"],
            "hypotheses": ["H1"],
            "matrice": [
                {
                    "niveau": "Objectif global",
                    "logique_intervention": "Améliorer l'accès",
                    "indicateurs": "Taux d'accès",
                    "baseline": "40%",
                    "cible": "80%",
                    "sources_verification": "Enquête",
                    "hypotheses": "Sécurité",
                }
            ],
        },
        "parties_prenantes": [
            {"nom": "Commune", "role": "Maître d'ouvrage", "interet": "Fort",
             "influence": "Fort", "quadrant": "Fort pouvoir / Fort intérêt"},
        ],
        "activites_detaillees": [
            {"titre": "Réhabilitation", "description": "...", "responsable": "ONG",
             "duree": "6 mois", "objectif_lie": "OS1"},
        ],
        "chronogramme": [{"trimestre": "T1", "activites": ["A1"]}],
        "budget": {
            "lignes": [{"categorie": "Travaux", "description": "Forages",
                        "montant_usd": 800000, "pourcentage": 80}],
            "total_usd": 1000000,
            "couts_directs": 700000,
            "couts_indirects": 300000,
            "par_annee": [{"annee": "Année 1", "montant_usd": 500000, "pourcentage": 50}],
            "par_partenaire": [{"partenaire": "ONG", "montant_usd": 900000, "pourcentage": 90}],
        },
        "plan_financement": {
            "lignes": [{"financeur": "UE", "type": "Subvention",
                        "montant_usd": 800000, "pourcentage": 80}],
            "total_usd": 1000000,
            "taux_cofinancement": "20 %",
        },
        "analyse_cout_benefice": {
            "van": 250000, "tri": 14.5, "ratio_cout_benefice": 1.8,
            "delai_retour_annees": 3.2, "benefices_annee1_usd": 120000,
            "scenario_central": "...", "scenario_pessimiste": "...",
            "analyse_sensibilite": "Une hausse de 10% des coûts...",
            "justification": "Hypothèses de calcul...",
        },
        "risques": [
            {"risque": "Retard", "categorie": "Opérationnel", "probabilite": "Moyen",
             "impact": "Élevé", "niveau": "Élevé", "mitigation": "Suivi renforcé"},
        ],
        "communication": "Plan de communication...",
        "perennisation": "Le projet sera pérennisé par...",
        "note_conceptuelle": "Note conceptuelle...",
        "resume_executif": "Résumé exécutif...",
    }
    # On passe par le schéma pour garantir la même shape qu'en production.
    return GeneratedContent.model_validate(payload).model_dump()


def _project_data() -> dict:
    return {
        "nom": "Eau potable Mali",
        "pays": "Mali",
        "secteur": "Eau & Assainissement",
        "bailleur": "AFD",
        "duree_mois": 24,
        "budget_total": 1000000,
    }


def test_full_document_renders_valid_docx():
    data = docx_service.create_word_document(_project_data(), _full_generated())
    assert isinstance(data, bytes)
    assert len(data) > 1000
    assert data[:2] == b"PK"  # signature ZIP / OOXML


def test_minimal_document_without_optional_sections():
    """Contenu minimal validé par le schéma : les sections optionnelles du lot A
    sont vides et ne doivent pas casser le rendu ni la numérotation."""
    minimal = GeneratedContent.model_validate({
        "introduction": "intro",
        "cadre_logique": {},
        "parties_prenantes": [],
        "activites_detaillees": [],
        "chronogramme": [],
        "budget": {},
        "analyse_cout_benefice": {},
        "risques": [],
        "communication": "comm",
    }).model_dump()
    data = docx_service.create_word_document(_project_data(), minimal)
    assert isinstance(data, bytes)
    assert data[:2] == b"PK"
