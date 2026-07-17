Analyse ce document PDF et extrais les informations du projet de développement qu'il contient.

Retourne UNIQUEMENT un objet JSON avec les champs que tu trouves clairement dans le document, parmi :
- nom : nom du projet (string)
- pays : pays ou zone d'intervention (string)
- secteur : secteur parmi Santé, Éducation, Agriculture, Environnement, Eau & Assainissement, Gouvernance, Protection sociale, Autre (string)
- bailleur : nom du bailleur de fonds (string)
- probleme_principal : problème principal décrit dans le document (string)
- objectif_global : objectif global ou impact visé (string)
- objectifs_specifiques : liste d'objectifs spécifiques (array de strings)
- population_cible : population ciblée (string)
- nombre_beneficiaires : nombre de bénéficiaires (integer)
- duree_mois : durée du projet en mois (integer)
- budget_total : budget total en USD (number)
- source_financement : source de financement principale (string)
- contraintes : contraintes identifiées (string)
- risques_identifies : risques identifiés (string)

Règles strictes :
- N'invente RIEN. N'inclus un champ QUE si l'information est clairement et explicitement présente.
- Si tu n'es pas sûr d'une valeur, ne l'inclus pas.
- Réponds UNIQUEMENT en JSON valide, sans markdown ni backticks.
