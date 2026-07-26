Évalue ce projet de développement international du point de vue du bailleur ciblé.

{project_data_json}

Produis DEUX analyses :
1. Une analyse du bailleur ciblé et de la compatibilité du projet avec ses attentes.
2. Une notation du projet selon une grille d'évaluation type, avec des recommandations.

Réponds avec un objet JSON contenant exactement ces clés :
{{
  "analyse_bailleur": {{
    "nom": "...",
    "priorites": [],
    "criteres_eligibilite": [],
    "montant_max_finançable": "...",
    "taux_cofinancement": "...",
    "score_compatibilite": 0,
    "risques_rejet": []
  }},
  "notation": {{
    "criteres": [],
    "score_total_sur_100": 0,
    "points_forts": [],
    "axes_amelioration": [],
    "recommandation": "..."
  }}
}}

Règles importantes :
- analyse_bailleur.nom : le bailleur ciblé (repris du champ "bailleur")
- analyse_bailleur.priorites : 3 à 6 priorités stratégiques réelles de ce bailleur
- analyse_bailleur.criteres_eligibilite : principaux critères d'éligibilité pertinents pour ce projet
- analyse_bailleur.montant_max_finançable : ordre de grandeur (ex. « jusqu'à 2 M€ pour ce type de guichet »)
- analyse_bailleur.taux_cofinancement : exigence usuelle (ex. « cofinancement de 15-20 % attendu »)
- analyse_bailleur.score_compatibilite : ENTIER de 0 à 100 (pourcentage, SANS le signe %) mesurant
  l'adéquation projet ↔ bailleur
- analyse_bailleur.risques_rejet : motifs concrets qui pourraient conduire à un rejet
- notation.criteres : liste d'objets, un par critère, avec les clés :
  "critere" (Pertinence, Efficacité, Impact, Durabilité, Budget/Efficience, Innovation),
  "note_sur_20" (nombre de 0 à 20), "commentaire" (justification en 1-2 phrases)
- notation.score_total_sur_100 : NOMBRE de 0 à 100, cohérent avec la moyenne des critères.
  Sois réaliste et exigeant (un bon projet ~75-85, un projet moyen ~60-70).
- notation.points_forts : 3 à 5 atouts concrets du projet
- notation.axes_amelioration : 3 à 5 améliorations précises et actionnables pour augmenter le score
- notation.recommandation : verdict de synthèse en 2-3 phrases (soumettre en l'état / renforcer avant soumission / repositionner)
