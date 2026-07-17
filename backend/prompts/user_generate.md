Génère un document complet de projet de développement international basé sur ces informations :

{project_data_json}
{reference_note}
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
