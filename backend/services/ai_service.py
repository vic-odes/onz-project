import os
import json
import litellm
from dotenv import load_dotenv

load_dotenv(override=True)

litellm.drop_params = True

MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")

SYSTEM_PROMPT = """
Tu es un expert senior en montage de projets de développement international,
avec 20 ans d'expérience auprès de bailleurs comme l'AFD, l'Union Européenne,
la Banque Mondiale et le PNUD.

Tu maîtrises parfaitement :
- Le cadre logique (Logical Framework Approach)
- Les indicateurs SMART
- L'analyse des parties prenantes
- La gestion axée sur les résultats (GAR)
- L'analyse coût-bénéfice des projets de développement
- Les standards de rédaction de chaque bailleur

Réponds UNIQUEMENT en JSON valide, sans markdown ni backticks.
Toutes les sections doivent être rédigées en français professionnel.
Ne laisse aucune section vide. Si une information manque, complète intelligemment
sur la base du secteur et du pays fournis.
"""


async def generate_project_content(project_data: dict) -> dict:
    """
    Génère le contenu complet du projet via LiteLLM.
    Changer de modèle = modifier LLM_MODEL dans .env uniquement.
    """
    user_prompt = f"""
Génère un document complet de projet de développement international basé sur ces informations :

{json.dumps(project_data, ensure_ascii=False, indent=2)}

Réponds avec un objet JSON contenant exactement ces clés :
{{
  "introduction": "...",
  "cadre_logique": {{
    "objectif_global": "...",
    "objectifs_specifiques": [],
    "resultats": [],
    "activites": [],
    "indicateurs_smart": [],
    "sources_verification": [],
    "hypotheses": []
  }},
  "parties_prenantes": [],
  "activites_detaillees": [],
  "chronogramme": [],
  "budget": {{
    "lignes": [],
    "total_usd": 0,
    "couts_directs": 0,
    "couts_indirects": 0
  }},
  "analyse_cout_benefice": {{
    "van": 0,
    "ratio_cout_benefice": 0,
    "scenario_central": "...",
    "scenario_pessimiste": "...",
    "justification": "..."
  }},
  "risques": [],
  "communication": "...",
  "note_conceptuelle": "...",
  "resume_executif": "..."
}}

Règles importantes :
- introduction : minimum 300 mots, contexte pays + problématique + justification
- cadre_logique.objectifs_specifiques : liste de chaînes de caractères
- cadre_logique.resultats : liste de chaînes de caractères
- cadre_logique.activites : liste de chaînes de caractères
- cadre_logique.indicateurs_smart : liste de chaînes de caractères (format : Indicateur - Baseline - Cible - Délai)
- cadre_logique.sources_verification : liste de chaînes de caractères
- cadre_logique.hypotheses : liste de chaînes de caractères
- parties_prenantes : liste d'objets avec clés "nom", "role", "interet", "influence" (Faible/Moyen/Fort)
- activites_detaillees : liste d'objets avec clés "titre", "description", "responsable", "duree", "objectif_lie"
- chronogramme : liste d'objets avec clés "trimestre" (T1, T2...), "activites" (liste de chaînes)
- budget.lignes : liste d'objets avec clés "categorie", "description", "montant_usd", "pourcentage"
- risques : liste d'objets avec clés "risque", "probabilite" (Faible/Moyen/Élevé), "impact" (Faible/Moyen/Élevé), "mitigation"
- note_conceptuelle : résumé 1 page si generer_note_conceptuelle est true, sinon chaîne vide
- resume_executif : synthèse 500 mots si inclure_resume_executif est true, sinon chaîne vide
"""

    # Paramètres Azure passés explicitement si disponibles
    extra = {}
    if os.getenv("AZURE_API_KEY"):
        extra["api_key"] = os.getenv("AZURE_API_KEY")
    if os.getenv("AZURE_API_BASE"):
        extra["api_base"] = os.getenv("AZURE_API_BASE")
    if os.getenv("AZURE_API_VERSION"):
        extra["api_version"] = os.getenv("AZURE_API_VERSION")

    response = await litellm.acompletion(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=8000,
        temperature=0.3,
        **extra,
    )

    raw = response.choices[0].message.content
    # Nettoyage au cas où le modèle ajoute des backticks malgré les instructions
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)
