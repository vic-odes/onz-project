Nous sommes le {date_du_jour}. Voici le profil du projet pour lequel il faut rechercher des
financements :

{project_data_json}

{recherche_note}

Identifie les bailleurs, lignes de financement et appels à projets actuellement compatibles
avec ce projet. Pour chaque opportunité identifiée, vérifie si la date limite (si connue)
est bien postérieure au {date_du_jour} avant de la présenter comme disponible.

Réponds avec un objet JSON contenant exactement ces clés :
{{
  "resume": "...",
  "opportunites": [
    {{
      "bailleur": "...",
      "programme": "...",
      "nom_appel": "...",
      "description": "...",
      "categorie": "tres_compatible | compatible | a_etudier | faible | non_eligible",
      "score_compatibilite": 0,
      "montant_min": null,
      "montant_max": null,
      "devise": "EUR",
      "taux_cofinancement_max": "...",
      "date_limite": "JJ/MM/AAAA ou vide si inconnue",
      "depot_permanent": false,
      "raisons_compatibilite": [],
      "points_vigilance": [],
      "conditions_principales": [],
      "source_officielle": "URL ou vide si non trouvée",
      "lien_candidature": "URL ou vide si non trouvée",
      "fiabilite": "verifie | a_confirmer | information_non_disponible",
      "date_verification": "{date_du_jour}"
    }}
  ]
}}

Règles importantes :
- "resume" : 2 à 3 phrases de synthèse (nombre d'opportunités trouvées, tendance générale).
- Trie "opportunites" par score décroissant, les opportunités "non_eligible" en dernier.
- 5 à 15 opportunités si possible ; si peu ou aucune opportunité crédible n'existe, dis-le
  franchement dans "resume" plutôt que de compléter artificiellement la liste.
- "montant_min"/"montant_max" : nombres (pas de texte, pas de symbole monétaire) ou `null`
  si inconnu — la devise va dans "devise".
- "date_verification" : toujours la date du jour ci-dessus.
