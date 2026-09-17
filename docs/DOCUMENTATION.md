# ONZ Projet — Documentation générale

> Présentation fonctionnelle et technique, guide de lancement, modes de déploiement et budget.
> Destiné aux équipes projet et à la direction — les parties 1, 4 et 5 ne demandent aucune
> compétence technique.
>
> Version en ligne (mise en page) : https://claude.ai/artifact/TA1t9Uze6YES6t2KYHHMx1
>
> État du code : branche `main`, 17 septembre 2026.

---

## Sommaire

1. [Ce que fait l'application](#1--ce-que-fait-lapplication)
2. [Comment c'est construit](#2--comment-cest-construit)
3. [Lancer le projet quand on a le code](#3--lancer-le-projet-quand-on-a-le-code)
4. [Modes de déploiement](#4--modes-de-déploiement)
5. [Budget](#5--budget)
6. [À savoir avant la production](#6--à-savoir-avant-la-production)

---

## 1 — Ce que fait l'application

### Le problème

Monter un dossier de projet pour un bailleur international demande un travail long et très normé :
cadre logique, indicateurs SMART, analyse des parties prenantes, chronogramme, budget détaillé,
analyse coût-bénéfice, matrice des risques. Chaque bailleur a ses attendus. Un chargé de projet
expérimenté y passe plusieurs jours ; une petite ONG n'a souvent pas cette expertise en interne.

ONZ Projet ramène ce travail à **un formulaire guidé et quelques minutes d'attente**. L'utilisateur
renseigne ce qu'il connaît de son projet ; l'IA rédige le dossier aux standards du bailleur visé, et
l'application le met en forme dans un document Word directement utilisable.

### Les six livrables

| Livrable | Description |
|---|---|
| **Dossier de projet complet** | Document Word structuré : introduction, cadre logique, parties prenantes, activités, chronogramme, budget, analyse coût-bénéfice, risques, communication. |
| **Note conceptuelle** | Document court (2-4 pages), format demandé par beaucoup de bailleurs en première approche. |
| **Évaluation du projet** | Score de compatibilité avec le bailleur visé + notation façon comité de sélection, avec recommandations. |
| **Recherche de financements** | Identification de bailleurs et programmes compatibles, classés par niveau de compatibilité. |
| **Budget Excel** | Export tableur du budget du projet. |
| **Pré-remplissage par PDF** | Dépôt d'un document existant → le formulaire se remplit automatiquement. |

### Le parcours utilisateur

1. **Créer un compte** — chaque utilisateur a son espace ; les projets ne sont jamais visibles par autrui.
2. **Choisir le type de dossier** — montage de projet, ou demande de financement.
3. **Remplir six étapes** — informations générales, problématique & objectifs, planification, budget, documents de référence, confirmation.
4. **Générer** — traitement en arrière-plan ; l'onglet peut être fermé sans perdre la génération.
5. **Récupérer le document** — téléchargement Word, puis retour possible via « Mes projets ».
6. **Chercher un financement** — optionnel, à partir du projet qui vient d'être monté.

> Le brouillon du formulaire est sauvegardé automatiquement dans le navigateur : fermer la page en
> cours de saisie ne fait rien perdre.

### Les deux modes de rédaction

| Mode | Quand l'utiliser | Ce qui change |
|---|---|---|
| **Montage** | Le projet est encore à concevoir ou structurer. | Rédaction orientée conception : cohérence du cadre logique, faisabilité, structuration des activités. |
| **Demande de financement** | Le projet existe ; il faut convaincre un bailleur. | Rédaction orientée argumentaire. La section pérennisation est ajoutée d'office (attendu systématique des financeurs). |

---

## 2 — Comment c'est construit

Trois blocs indépendants. Chaque sous-partie commence par une explication en langage courant.

### 2.1 — Backend (le moteur)

> **En clair** — la partie invisible qui reçoit les informations du formulaire, appelle l'IA,
> fabrique le fichier Word et garde la mémoire des projets.

**Python 3.13 + FastAPI.** 19 points d'entrée en cinq familles : authentification, génération,
projets, documents, financements.

- **Authentification** — comptes utilisateurs, mots de passe bcrypt, jeton JWT en cookie sécurisé.
  Tous les endpoints métier sont protégés et filtrés sur le propriétaire (le projet d'autrui renvoie 404).
- **Base de données** — SQLite via SQLAlchemy 2, migrations Alembic appliquées au démarrage.
  Quatre tables : `users`, `projects`, `recherches_financement`, `generation_jobs`.
- **Traitements longs en arrière-plan** — génération et recherche de financement renvoient
  immédiatement un identifiant de suivi ; le frontend sonde l'avancement. Évite les coupures
  navigateur/proxy sur des traitements de plusieurs minutes.
- **Sécurité des uploads** — trois niveaux : rejet au-delà de 50 Mo (middleware), limites par fichier
  (10 Mo, 30 Mo au total, 5 fichiers max), vérification des magic bytes PDF.
- **Limitation de débit** — 5 connexions et 3 inscriptions par minute (anti brute-force).
- **Mise en forme** — Word via `python-docx`, Excel via `openpyxl`.
- **Tests** — 20 fichiers pytest (validation PDF, prompts, schémas, authentification, génération, services).

### 2.2 — Frontend (l'interface)

> **En clair** — tout ce que l'utilisateur voit et manipule dans son navigateur.

**Next.js 14 (App Router) + TypeScript + Tailwind CSS.** Dépendances **volontairement minimales** :
uniquement React et Next.js, aucune bibliothèque de composants. Tout est écrit sur mesure — moins de
dette technique et de failles héritées.

| Écran | Rôle |
|---|---|
| Accueil | Page publique de présentation |
| Connexion / Inscription | Création de compte et authentification |
| Nouveau projet | Formulaire en six étapes |
| Mes projets | Liste, téléchargement, suppression |
| Recherche de financement | Lancement, suivi, consultation des résultats |

Les pages privées sont protégées par un `AuthGuard` : l'utilisateur non connecté est redirigé vers la
connexion puis ramené à la page visée. Une session expirée est détectée, la session locale nettoyée,
et l'utilisateur redirigé — sans message d'erreur technique.

### 2.3 — Couche IA

> **En clair** — la partie qui « écrit » le contenu : elle dialogue avec le modèle, lui donne les
> consignes, puis vérifie que la réponse est complète avant d'en faire un document.

C'est l'élément le plus soigné de l'architecture, et le plus stratégique.

#### Indépendance vis-à-vis du fournisseur

L'application passe par **LiteLLM**. Changer de modèle se fait **en modifiant une seule ligne de
configuration** (`LLM_MODEL`), sans toucher au code :

| Fournisseur | Valeur | Particularité |
|---|---|---|
| Anthropic (Claude) | `claude-sonnet-4-20250514` | Lit les PDF nativement, sait chercher sur le web |
| Azure OpenAI | `azure/<déploiement>` | Données dans votre propre abonnement Azure |
| OpenAI | `gpt-5-mini`, `gpt-4o-mini` | — |
| Google | `gemini/gemini-2.5-flash` | — |
| Mistral | `mistral/mistral-large-latest` | Souverain européen |
| Ollama | `ollama/llama3` | 100 % local, aucune donnée ne sort, aucun coût par usage |

Atout de négociation et de conformité : possibilité de changer si les tarifs évoluent, ou de basculer
sur une solution souveraine si un bailleur l'exige.

**Point d'architecture** : tout appel LLM passe par `backend/services/llm_client.py`. Ne jamais
importer `litellm` ailleurs.

#### Consignes de rédaction éditables

Les instructions données à l'IA ne sont pas dans le code : ce sont **onze fichiers Markdown** dans
`backend/prompts/` (un par usage). Une personne qui maîtrise le métier, sans être développeur, peut
les relire et les affiner.

#### Quatre garde-fous sur la sortie du modèle

1. **Format imposé** — réponse en JSON structuré ; mode JSON natif activé quand le fournisseur le supporte.
2. **Réparation automatique** — un JSON légèrement malformé (guillemet non échappé, virgule en trop) est réparé avant abandon (`json_repair`).
3. **Détection de troncature** — `finish_reason == "length"` produit une erreur explicite et actionnable, pas un plantage.
4. **Validation stricte** — vérification section par section (Pydantic, `schemas/generated.py`) : top-level strict, imbriqué permissif. Une section obligatoire manquante fait échouer la requête plutôt que de produire un document silencieusement amputé.

#### Documents joints

Avec Claude, les PDF sont envoyés tels quels (blocs `document` natifs). Avec les autres modèles, le
texte est extrait via `pypdf` puis injecté dans la consigne (tronqué à 3 000 caractères). Si l'envoi
natif échoue, l'extraction prend le relais automatiquement.

---

## 3 — Lancer le projet quand on a le code

Compter **20 à 30 minutes** la première fois.

### Prérequis

- **Python 3.13** et **Node.js 20**
- **Une clé d'API** d'un fournisseur d'IA — seul élément payant

### Étape 1 — Le moteur

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Renseigner **trois choses obligatoires** dans `.env` :

| Paramètre | Rôle |
|---|---|
| `LLM_MODEL` | Le modèle d'IA à utiliser |
| La clé d'API correspondante | `ANTHROPIC_API_KEY`, ou le trio `AZURE_API_KEY` / `AZURE_API_BASE` / `AZURE_API_VERSION` |
| `JWT_SECRET_KEY` | Signe les sessions. **Sans lui, la connexion ne fonctionne pas.** |

Générer la clé de session :

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Démarrer :

```bash
uvicorn main:app --reload
```

Le moteur écoute sur `http://localhost:8000`. La base est créée et migrée automatiquement au démarrage.

### Étape 2 — L'interface

Dans un **second terminal**, en laissant le premier tourner :

```bash
cd frontend
npm install
npm run dev
```

Application accessible sur `http://localhost:3000`.

### Étape 3 — Vérifier

1. Ouvrir `http://localhost:3000` et créer un compte.
2. Lancer un projet avec le jeu d'essai de référence : *Accès à l'eau potable en milieu rural*,
   Mali, Eau & Assainissement, AFD, 24 mois, 500 000 USD.
3. Le document Word doit se télécharger au bout de quelques minutes.

Vérifications utiles : `http://localhost:8000/health` doit répondre `ok` ;
`http://localhost:8000/docs` liste tous les points d'entrée ; des PDF d'exemple sont fournis dans
`samples/` pour tester le pré-remplissage.

### Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest -q
```

### ⚠️ À propos de Docker

Le `docker-compose.yml` est **configuré pour un serveur d'hébergement (Dokploy)**, pas pour un usage
local : les ports ne sont pas publiés vers l'hôte (`expose` et non `ports`), il exige le réseau externe
`dokploy-network`, et **il ne transmet pas `JWT_SECRET_KEY`** — l'authentification échouerait. Pour un
démarrage local, utiliser la voie manuelle ci-dessus.

---

## 4 — Modes de déploiement

Question centrale : **chaque personne fait-elle tourner l'application chez elle, ou existe-t-il une
seule installation partagée ?** Le choix engage le budget, la charge de travail et le profil des
utilisateurs possibles.

### Mode 1 — Décentralisé : chacun installe chez soi

Chaque personne récupère le code, l'installe (partie 3) et utilise sa propre clé d'API.

**Avantages** — aucun coût de serveur ; les données ne quittent jamais la machine ; chacun choisit son modèle.

**Inconvénients** — réservé à des profils techniques ; chaque personne doit ouvrir un compte chez un
fournisseur d'IA et gérer sa facturation ; aucun partage de projets ; chaque mise à jour doit être
refaite par chacun ; aucune visibilité sur les coûts ni sur l'usage.

**Pertinent pour** le développement, les tests, ou une à deux personnes techniques autonomes.
**Inadapté** à un usage en équipe ou par des profils non techniques — qui constituent pourtant le public visé.

### Mode 2 — Centralisé : une installation partagée

L'application est déployée une fois ; les utilisateurs s'y connectent via une adresse web, sans rien
installer. Les comptes utilisateurs déjà présents prennent tout leur sens dans ce mode.

**C'est le mode déjà outillé dans le projet** : infrastructure Azure décrite en code (`infra/`) et
déploiement automatisé (`.github/workflows/deploy-azure.yml`) — chaque merge sur `main` reconstruit et
met en ligne l'application sans intervention.

| Ressource Azure | Rôle |
|---|---|
| Container Apps | Héberge moteur et interface, gère HTTPS et montée en charge |
| Container Registry | Stocke les versions de l'application |
| Key Vault | Coffre-fort des clés d'API et du secret de session |
| Log Analytics + Application Insights | Journaux et supervision |
| Identité managée | Authentification entre composants sans mot de passe stocké |

Aucun secret n'est écrit dans le code : les clés vivent dans le coffre-fort et sont lues à l'exécution
par une identité managée.

### Mode 3 — Centralisé sur serveur simple (intermédiaire)

Même principe, sur un VPS avec Docker plutôt que sur Azure. Moins cher, mais mise à jour, sauvegardes,
certificat HTTPS et supervision sont à la charge de l'équipe. C'est vers cette cible que pointe le
`docker-compose.yml` existant.

### Comparatif

| Critère | Mode 1 — Décentralisé | Mode 2 — Azure | Mode 3 — VPS |
|---|---|---|---|
| Coût d'infrastructure | 0 € | 30–45 €/mois | 5–20 €/mois |
| Installation par l'utilisateur | 1–2 h, technique | Aucune | Aucune |
| Accessible aux non-techniciens | Non | Oui | Oui |
| Mise à jour | Par chaque personne | Automatique | Manuelle |
| Projets partagés | Non | Oui | Oui |
| Maîtrise des coûts d'IA | Aucune | Centralisée | Centralisée |
| Charge d'administration | Nulle mais démultipliée | Faible | Moyenne à élevée |
| Sauvegardes | À la charge de chacun | À mettre en place | À mettre en place |

### Recommandation

**Au-delà de deux utilisateurs, ou dès qu'une personne non technique doit s'en servir, le mode
centralisé s'impose.** Le public visé — chargés de projet et ONG — n'installera pas Python sur son poste.

Le coût d'infrastructure du mode 2 (30–45 €/mois) est très inférieur au coût caché du mode 1 : dix
personnes à 1 h 30 d'installation chacune, plus dix abonnements à gérer, dépassent une année
d'hébergement dès le premier mois.

---

## 5 — Budget

Deux natures de coûts : l'**infrastructure**, fixe et prévisible ; et l'**IA**, proportionnelle à l'usage.

> ⚠️ **Précaution de lecture** — les montants sont des **ordres de grandeur**, calculés sur la
> configuration réellement déclarée dans le code, en région France Centre. Les tarifs Azure et ceux
> des modèles évoluent : à valider avec le calculateur de prix Azure et la grille de votre fournisseur
> avant tout engagement.

### Coûts fixes — infrastructure (mode 2)

Configuration actuelle : deux conteneurs de 0,5 vCPU et 1 Gio, maintenus actifs en permanence.

| Poste | Par mois | Commentaire |
|---|---:|---|
| Container Apps (moteur + interface) | 20–25 € | Poste principal |
| Container Registry (Basic) | ≈ 5 € | Forfait |
| Journaux et supervision | 3–15 € | Facturé au volume |
| Key Vault | < 1 € | Négligeable |
| Stockage | < 1 € | Provisionné, aujourd'hui inutilisé |
| **Total infrastructure** | **30–45 €** | Hors IA |

> **Économie immédiate** — l'application journalise en mode **DEBUG** (très verbeux). Passer en `INFO`
> réduit sensiblement le poste « journaux », facturé au volume ingéré.

### Coûts variables — IA

L'IA se facture au « jeton » (token, ~4 caractères), à l'entrée et à la sortie. Plafonds réellement
configurés dans le code :

| Action | Plafond de sortie | Sortie réelle typique |
|---|---:|---:|
| Dossier de projet complet | 16 000 | 4 000–8 000 |
| Recherche de financements | 16 000 | 6 000–12 000 |
| Note conceptuelle | 4 000 | 2 000–3 500 |
| Évaluation de projet | 2 500 | 1 500–2 500 |
| Pré-remplissage depuis PDF | 2 000 | 500–1 500 |

Calcul : **(jetons d'entrée × tarif d'entrée) + (jetons de sortie × tarif de sortie)**, tarifs par
million de jetons.

| Catégorie de modèle | Coût par dossier | Exemples |
|---|---:|---|
| Économique | < 0,01–0,03 € | gpt-5-nano, gpt-4o-mini, Gemini Flash |
| Premium | 0,10–0,30 € | Claude Sonnet, GPT-4o |
| Local (Ollama) | 0 € | Aucun coût par usage, machine puissante requise |

**La configuration actuellement déployée utilise un modèle économique** (`gpt-5-nano` sur Azure
OpenAI) : le coût d'IA reste marginal face à l'infrastructure.

### Scénarios chiffrés

| Usage mensuel | Mode 1 — Décentralisé | Mode 2 — Azure | Mode 3 — VPS |
|---|---:|---:|---:|
| 3 utilisateurs — 20 dossiers | ≈ 1 € (réparti sur 3 comptes) | 31–46 € | 6–21 € |
| 10 utilisateurs — 100 dossiers | ≈ 3 € (réparti sur 10 comptes) | 33–48 € | 8–23 € |
| 30 utilisateurs — 400 dossiers | ≈ 12 € (réparti sur 30 comptes) | 42–57 € | 17–32 € |

Avec un modèle premium, ajouter environ 10–30 € pour 100 dossiers et 40–120 € pour 400 dossiers.

> **Lecture** — le mode 1 paraît imbattable, mais sa colonne ne comptabilise **que** l'IA. Elle ignore
> le temps d'installation, la gestion de plusieurs abonnements, l'absence de partage et la reprise
> manuelle de chaque mise à jour. À partir d'une dizaine d'utilisateurs, le mode centralisé est moins
> cher *en coût complet*, et incomparablement plus simple à vivre.

### Coût à prévoir pour une vraie production

La partie 6 explique pourquoi la base de données actuelle n'est pas durable. Une base PostgreSQL
gérée représente **15–25 €/mois supplémentaires** et porte le budget du mode 2 à environ
**50–70 €/mois**. C'est le prix de la fiabilité.

---

## 6 — À savoir avant la production

L'application fonctionne et est déployée. Les points ci-dessous ne remettent pas cela en cause, mais
doivent être connus avant d'ouvrir le service à de vrais utilisateurs et de vrais dossiers.

### 🔴 Priorité 1 — Les données ne survivent pas à un redémarrage

Sur le déploiement Azure actuel, la base est stockée dans un volume **éphémère** (`EmptyDir`). À chaque
redéploiement ou redémarrage du conteneur, **comptes et projets sont effacés**. C'était un choix
assumé pour débloquer la mise en ligne : SQLite est incompatible avec Azure Files (verrouillage de
fichiers SMB → `database is locked`). La correction est identifiée — migrer vers PostgreSQL — et
chiffrée en partie 5. **Prérequis absolu avant tout usage réel.**

### Autres points

| Point | Conséquence | Correction |
|---|---|---|
| Un seul réplica du moteur | Pas de montée en charge horizontale ; interruption pendant un redéploiement | Levé automatiquement par la migration PostgreSQL |
| Journaux en DEBUG | Coût de supervision plus élevé, journaux peu exploitables | Passer en `INFO` — une ligne |
| Aucune sauvegarde automatique | Perte définitive en cas d'incident | Sauvegardes gérées, incluses avec PostgreSQL |
| Pas de supervision des erreurs ni des coûts d'IA | Erreurs utilisateurs invisibles, aucun suivi de la dépense | Outil de suivi d'erreurs + compteur de jetons |
| Aucun quota par utilisateur | Un usage intensif peut faire grimper la facture d'IA | Quota mensuel par compte |
| `docker-compose.yml` incomplet | Ne transmet pas `JWT_SECRET_KEY` : authentification cassée | Ajouter la variable |
| Interface non testée automatiquement | Régression possible en production | Tests frontend (le backend en a déjà 20 fichiers) |

### Ordre de priorité suggéré

1. **Migrer vers PostgreSQL** — bloquant pour toute mise en service réelle.
2. **Mettre en place les sauvegardes** — largement simplifié par le point 1.
3. **Passer les journaux en INFO** — gain immédiat, effort minime.
4. **Ajouter supervision et quotas** — maîtrise du budget d'IA.
5. **Compléter les tests frontend** — confort de maintenance.

### En résumé

Le produit est fonctionnellement riche et techniquement bien construit : architecture modulaire,
sécurité sérieuse, indépendance vis-à-vis du fournisseur d'IA, tests backend présents.

Il lui manque **une seule chose avant un usage réel** : une base de données durable. C'est un chantier
court, chiffré, sans reprise d'architecture.
