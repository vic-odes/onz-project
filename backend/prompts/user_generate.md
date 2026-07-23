Génère un document complet de projet de développement international basé sur ces informations :

{project_data_json}
{reference_note}
Réponds avec un objet JSON contenant exactement ces clés :
{{
  "introduction": "...",
  "arbre_problemes": {{
    "probleme_central": "...",
    "causes": [],
    "consequences": [],
    "objectif_central": "...",
    "moyens": [],
    "fins": []
  }},
  "theorie_changement": {{
    "narratif": "...",
    "probleme": "...",
    "causes": [],
    "activites": [],
    "resultats": [],
    "effets": [],
    "impact": "...",
    "hypotheses": []
  }},
  "cadre_logique": {{
    "objectif_global": "...",
    "objectifs_specifiques": [],
    "resultats": [],
    "activites": [],
    "indicateurs_smart": [],
    "sources_verification": [],
    "hypotheses": [],
    "matrice": []
  }},
  "parties_prenantes": [],
  "activites_detaillees": [],
  "chronogramme": [],
  "budget": {{
    "lignes": [],
    "total_usd": 0,
    "couts_directs": 0,
    "couts_indirects": 0,
    "par_annee": [],
    "par_partenaire": []
  }},
  "plan_financement": {{
    "lignes": [],
    "total_usd": 0,
    "taux_cofinancement": "..."
  }},
  "analyse_cout_benefice": {{
    "van": 0,
    "tri": 0,
    "ratio_cout_benefice": 0,
    "delai_retour_annees": 0,
    "benefices_annee1_usd": 0,
    "scenario_central": "...",
    "scenario_pessimiste": "...",
    "analyse_sensibilite": "...",
    "justification": "..."
  }},
  "risques": [],
  "communication": "...",
  "perennisation": "...",
  "note_conceptuelle": "...",
  "resume_executif": "..."
}}

Règles importantes :
- introduction : minimum 300 mots, contexte pays + problématique + justification
- arbre_problemes : analyse causale du problème central.
  - causes : facteurs racines (le « pourquoi » du problème)
  - consequences : effets négatifs observés (le « donc »)
  - objectif_central / moyens / fins : reformulation positive (arbre à objectifs, miroir des causes/conséquences)
- theorie_changement : chaîne causale Problème → Causes → Activités → Résultats → Effets → Impact.
  - narratif : 1 paragraphe expliquant la logique d'ensemble
  - chaque maillon (causes, activites, resultats, effets) est une liste de chaînes courtes
  - hypotheses : conditions critiques pour que la chaîne se réalise
- cadre_logique.objectifs_specifiques / resultats / activites / indicateurs_smart / sources_verification / hypotheses : listes de chaînes de caractères
- cadre_logique.indicateurs_smart : format « Indicateur - Baseline - Cible - Délai »
- cadre_logique.matrice : matrice complète UE/AFD. Une ligne par niveau (Objectif global,
  chaque Objectif spécifique, chaque Résultat, grandes Activités). Chaque objet a les clés :
  "niveau", "logique_intervention", "indicateurs", "baseline", "cible", "sources_verification", "hypotheses"
  (toutes des chaînes de caractères).
- parties_prenantes : liste d'objets avec clés "nom", "role", "interet", "influence" (Faible/Moyen/Fort),
  "quadrant" (un de : « Fort pouvoir / Fort intérêt », « Fort pouvoir / Faible intérêt »,
  « Faible pouvoir / Fort intérêt », « Faible pouvoir / Faible intérêt »)
- activites_detaillees : liste d'objets avec clés "titre", "description", "responsable", "duree", "objectif_lie"
- chronogramme : liste d'objets avec clés "trimestre" (T1, T2...), "activites" (liste de chaînes)
- budget.lignes : liste d'objets avec clés "categorie", "description", "montant_usd", "pourcentage"
- budget.par_annee : ventilation annuelle — objets "annee" (« Année 1 »...), "montant_usd", "pourcentage".
  Adapter le nombre d'années à la durée du projet (duree_mois). Une seule année si le projet dure ≤ 12 mois.
- budget.par_partenaire : ventilation par structure porteuse — objets "partenaire", "montant_usd", "pourcentage"
- Le total de budget.lignes, de budget.par_annee et de budget.par_partenaire doivent être cohérents (= total_usd)
- plan_financement.lignes : répartition du financement — objets "financeur", "type"
  (Subvention/Cofinancement/Apport propre/Valorisation), "montant_usd", "pourcentage".
  total_usd = somme des montants ; taux_cofinancement = part hors bailleur principal (ex. « 20 % »).
- analyse_cout_benefice : CALCULER de vraies valeurs financières, jamais des zéros.
  - van : Valeur actuelle nette en USD (taux d'actualisation ~5-8 %)
  - tri : Taux de rentabilité interne en pourcentage
  - ratio_cout_benefice : bénéfices actualisés / coûts actualisés (> 1 = rentable)
  - delai_retour_annees : délai de récupération de l'investissement
  - benefices_annee1_usd : estimation chiffrée des bénéfices sur la première année
  - analyse_sensibilite : 2-3 phrases sur l'effet d'une variation des hypothèses clés
  - justification : hypothèses de calcul (bénéfices monétisés, horizon, taux)
- risques : liste d'objets avec clés "risque", "categorie" (Financier/Politique/Climatique/Opérationnel/Technique),
  "probabilite" (Faible/Moyen/Élevé), "impact" (Faible/Moyen/Élevé),
  "niveau" (score croisé proba × impact : Faible/Moyen/Élevé/Critique), "mitigation"
- perennisation : si inclure_perennisation est true, rédige une section (250-400 mots) sur la
  pérennisation du projet (appropriation locale, viabilité financière post-financement,
  transfert de compétences, ancrage institutionnel). Sinon, chaîne vide.
- note_conceptuelle : résumé 1 page si generer_note_conceptuelle est true, sinon chaîne vide
- resume_executif : synthèse 500 mots si inclure_resume_executif est true, sinon chaîne vide
