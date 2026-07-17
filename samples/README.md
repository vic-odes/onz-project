# Fichiers d'exemple (tests manuels)

PDF de démonstration pour tester le formulaire, le pré-remplissage et l'upload
de documents de référence. Contenu fictif mais cohérent (secteurs/bailleurs
alignés sur `frontend/lib/constants.ts`).

| Fichier | Où l'utiliser | Contenu |
|---|---|---|
| `projet_mali_eau_assainissement.pdf` | Pré-remplissage (prefill) | Mali · Eau & Assainissement · AFD · 75 000 bénéficiaires · 30 mois · 1 200 000 USD |
| `projet_senegal_education.pdf` | Pré-remplissage (prefill) | Sénégal · Éducation · Union Européenne · 12 000 bénéficiaires · 36 mois · 2 500 000 USD |
| `budget_projet_mali.pdf` | Upload « Budget » (étape 4) | Budget détaillé par poste (total 1 200 000 USD) |
| `document_reference_appel_afd.pdf` | Upload « Document de référence » (étape 5) | Appel à projets AFD : priorités, éligibilité, marqueurs OCDE-DAC |

Tous les champs attendus par `backend/prompts/prefill.md` y sont écrits
explicitement (le prompt interdit au modèle d'inventer). Texte extractible par
`pypdf` (fallback des modèles non-vision).
