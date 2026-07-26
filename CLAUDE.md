# CLAUDE.md

Ce fichier guide Claude Code lors de toute intervention sur ce dépôt. Il est lu automatiquement à chaque session.

---

## Vue d'ensemble

**ONZ Projet** est un assistant de montage de projets de développement international.
Un utilisateur remplit un formulaire guidé (5 étapes + récapitulatif), et l'application génère via IA un document Word `.docx` prêt à soumettre à des bailleurs (AFD, Union Européenne, Banque Mondiale, PNUD…).

L'utilisateur peut également joindre des PDFs (appel à projets, budget, rapports précédents) qui sont :
- soit envoyés en natif au modèle (Claude vision),
- soit extraits en texte via `pypdf` puis injectés dans le prompt (modèles non-vision).

Un PDF peut aussi servir à pré-remplir le formulaire via `/api/documents/prefill`.

---

## Stack technique

| Couche | Techno |
|---|---|
| Frontend | Next.js 14 (App Router) + TypeScript + Tailwind |
| Backend | FastAPI — Python 3.13 |
| LLM | LiteLLM (abstraction multi-providers : Anthropic / OpenAI / Gemini / Mistral / Ollama / Azure) |
| Export | python-docx |
| Persistance | SQLite + SQLAlchemy 2.x |
| Conteneurisation | docker-compose (réseau externe `dokploy-network`) |

---

## Arborescence

```
onz-project/
├── backend/
│   ├── main.py                  # Entrée FastAPI, CORS, logging, middlewares
│   ├── database.py              # Engine SQLAlchemy + save_project + init_db (migration ad-hoc)
│   ├── models/project.py        # Modèle SQLAlchemy `Project`
│   ├── schemas/project.py       # Pydantic ProjectCreate / ProjectResponse
│   ├── routers/
│   │   ├── generate.py          # POST /api/generate/      → IA + DOCX + persistance
│   │   ├── projects.py          # CRUD + /download
│   │   └── documents.py         # POST /api/documents/prefill (PDF → JSON formulaire)
│   ├── services/
│   │   ├── ai_service.py        # ⭐ Tout l'appel LLM (system+user prompts, fallback PDF→texte)
│   │   └── docx_service.py      # Mise en forme Word (couleurs, tableaux, en-tête/pied)
│   ├── documents/               # .docx générés (créé au runtime)
│   ├── onz_projects.db          # SQLite local (dev)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env                     # Non versionné — clés API LLM
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx
│   │   ├── nouveau-projet/page.tsx
│   │   ├── mes-projets/page.tsx
│   │   └── layout.tsx
│   ├── components/
│   │   ├── Stepper.tsx          # Formulaire 6 étapes — monolithe ~650 lignes
│   │   ├── PdfUpload.tsx
│   │   ├── GenerationLoader.tsx
│   │   ├── ProjectCard.tsx
│   │   └── Navbar.tsx
│   ├── lib/api.ts               # Client fetch typé (generate / list / get / delete / download / prefill)
│   ├── package.json             # Dépendances minimales (next, react uniquement)
│   ├── Dockerfile               # Multi-stage standalone
│   └── tsconfig.json
│
├── docker-compose.yml
└── README.md
```

---

## Commandes courantes

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate                # Windows (PowerShell : .\venv\Scripts\Activate.ps1)
pip install -r requirements.txt
copy .env.example .env               # puis renseigner LLM_MODEL et la clé API
uvicorn main:app --reload
```
- API : http://localhost:8000
- Swagger : http://localhost:8000/docs
- Health : http://localhost:8000/health

### Frontend
```bash
cd frontend
npm install
npm run dev
```
- UI : http://localhost:3000
- Lint : `npm run lint`
- Build prod : `npm run build && npm start`

### Docker (full stack)
```bash
docker compose up --build
```
Le réseau `dokploy-network` doit exister (`docker network create dokploy-network` si besoin).

### Tests
Backend : suite pytest dans [`backend/tests/`](backend/tests/) — couvre les modules purs
(`pdf_validation`, `prompts`, `schemas/generated`, `auth_service`). Pas de mock LLM/DB pour l'instant.

```bash
cd backend
pip install -r requirements-dev.txt   # ajoute pytest + pytest-asyncio
pytest -q                              # depuis backend/, lit pytest.ini
```

[`tests/conftest.py`](backend/tests/conftest.py) ajoute `backend/` à `sys.path` et
définit un `JWT_SECRET_KEY` déterministe pour les tests qui en ont besoin.

Frontend : aucun test (Vitest / Playwright à décider).

---

## Variables d'environnement (`backend/.env`)

```env
# Modèle (par défaut : Claude Sonnet 4)
LLM_MODEL=claude-sonnet-4-20250514

# Une seule clé selon le provider
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
MISTRAL_API_KEY=...

# Azure OpenAI (passé explicitement à litellm.acompletion)
AZURE_API_KEY=...
AZURE_API_BASE=...
AZURE_API_VERSION=...

# Override des limites (optionnel)
LLM_MAX_TOKENS=4096

# CORS — virgules
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# DB (Docker = sqlite:////app/data/onz_projects.db)
DATABASE_URL=sqlite:///./onz_projects.db

# Auth — OBLIGATOIRE
# Générer : python -c "import secrets; print(secrets.token_urlsafe(64))"
JWT_SECRET_KEY=...
JWT_EXPIRE_MINUTES=1440   # 24 h par défaut
```

Frontend : `NEXT_PUBLIC_API_URL` (par défaut `http://localhost:8000`) — passé en `ARG` au build Docker.

---

## Points d'architecture importants

### Client LLM unifié — point d'entrée unique
[`backend/services/llm_client.py`](backend/services/llm_client.py) — **tout appel LiteLLM passe par ici**. Fait une seule fois :
- `load_dotenv` + flags `litellm.drop_params` / `suppress_debug_info` / `set_verbose`
- `get_model()` lit `LLM_MODEL` à chaque appel (permet override à chaud, ex. pour tests)
- `supports_native_pdf(model)` — `True` si nom de modèle contient « claude »
- `azure_extras()` — kwargs Azure si `AZURE_API_KEY/BASE/VERSION` sont définis
- `call_llm(messages, *, max_tokens, temperature=0.3, model=None, extra=None)` async — retourne le texte nettoyé des balises markdown ; lève `ValueError` si réponse tronquée (`finish_reason="length"`) ou vide
- `parse_json_response(raw)` — `json.loads` qui logue le début du contenu en cas d'échec

Les deux callers sont :
- [`services/ai_service.py`](backend/services/ai_service.py) — `generate_project_content()` : fait toute la logique métier (prompts, fallback PDF natif → texte) et délègue l'appel à `llm_client.call_llm`.
- [`routers/documents.py`](backend/routers/documents.py) — `/prefill` : idem, avec `_PREFILL_MAX_TOKENS=2000`, `_PREFILL_TEMPERATURE=0.1`.

**Ne jamais importer `litellm` ailleurs que dans `llm_client.py`.** Tout nouvel endpoint LLM doit passer par ce module.

### Hot-swap du modèle LLM
Toutes les capacités liées au modèle sont **relues à chaque appel** (plus de gel à l'import) :
- `llm_client.get_model()` — lit `LLM_MODEL` à chaque appel.
- `llm_client.supports_native_pdf()` — recalculé à chaque appel selon le modèle courant.
- `_compute_max_tokens(supports_native_pdf)` dans [`ai_service.py`](backend/services/ai_service.py#L15-L19) — 8000 tokens si Claude, sinon `LLM_MAX_TOKENS` (défaut 4096).

Conséquence : modifier `LLM_MODEL` ou `LLM_MAX_TOKENS` dans `.env` puis recharger le process suffit ; pas besoin de modifier le code. Pour aller jusqu'au override par requête (multi-tenant), `llm_client.call_llm(..., model=..., extra=...)` accepte déjà des overrides — il suffirait de les exposer côté router.

### Format JSON attendu du LLM (validé)
Strictement défini dans [`_build_user_prompt`](backend/services/ai_service.py) ET validé par le schéma Pydantic [`schemas/generated.py`](backend/schemas/generated.py) :
- **Top-level strict** : `introduction`, `cadre_logique`, `parties_prenantes`, `activites_detaillees`, `chronogramme`, `budget`, `analyse_cout_benefice`, `risques`, `communication` sont **obligatoires**. Toute clé manquante → `ValidationError` → HTTP **502**.
- **Top-level optionnel** : `note_conceptuelle`, `resume_executif` (chaîne vide par défaut), et les sections du lot A `theorie_changement`, `arbre_problemes`, `plan_financement` (objets avec defaults), `perennisation` (chaîne vide, pilotée par le flag `inclure_perennisation`). Le prompt les demande, mais leur absence ne fait pas tomber la requête (même politique que `note_conceptuelle`).
- **Nested permissif** : les sous-objets (`PartiePrenante`, `Risque`, `BudgetLigne`…) ont des defaults — un LLM qui omet `influence` mais fournit `nom` ne fait pas tomber la requête.
- `extra="ignore"` partout : les champs supplémentaires hallucinés sont silencieusement ignorés.
- `ai_service.generate_project_content` retourne `GeneratedContent.model_dump()` — `docx_service` reçoit donc une shape **garantie**, plus de section vide silencieuse due à une clé manquante.
- Côté router [`generate.py`](backend/routers/generate.py) :
  - `JSONDecodeError` (LLM tronqué / non-JSON) → **502**
  - `ValidationError` (JSON valide mais shape incomplète) → **502** + liste des champs problématiques
  - Autre exception → **500**

### Fallback PDF natif → texte
- Si le modèle commence par `claude` → bloc `"document"` natif (Anthropic).
- Sinon → extraction texte via `pypdf`, tronquée à `_MAX_EXTRACTED_CHARS = 3000` ([`ai_service.py:23`](backend/services/ai_service.py#L23)).
- Si l'appel natif Claude échoue → fallback texte automatique.

### Migration de schéma
Pas d'Alembic. [`init_db`](backend/database.py#L57-L66) tente un `ALTER TABLE … ADD COLUMN docx_path` dans un `try/except pass`. Toute nouvelle colonne doit être ajoutée de la même façon (temporaire) ou justifier l'introduction d'Alembic.

### Persistance des `.docx`
Le fichier est sauvegardé dans `backend/documents/{id}_{slug}_ONZ.docx` ([`database.py:44-50`](backend/database.py#L44-L50)). En Docker, ce dossier est dans le volume `sqlite_data` monté sur `/app/data` — **attention** : le code écrit dans `Path(__file__).parent / "documents"` qui n'est PAS le volume. À surveiller en prod.

### CORS (durci)
[`main.py`](backend/main.py) — origins parsés depuis `CORS_ORIGINS`, allowlist explicite :
- `allow_methods=["GET", "POST", "DELETE", "OPTIONS"]`
- `allow_headers=["Authorization", "Content-Type"]`
- `expose_headers=["Content-Disposition"]` (nécessaire au téléchargement `.docx` côté browser)
- `max_age=600` (cache preflight 10 min)
- Les origines hors allowlist reçoivent **400** au preflight, sans `Access-Control-Allow-Origin`.

### Authentification JWT — backend
- Modèle [`User`](backend/models/user.py) ↔ [`Project.user_id`](backend/models/project.py) (FK, `ondelete=CASCADE`).
- Service [`services/auth_service.py`](backend/services/auth_service.py) : `hash_password` (bcrypt), `verify_password`, `create_access_token`, `decode_token`. Algorithme **HS256**, secret lu via `JWT_SECRET_KEY`, TTL via `JWT_EXPIRE_MINUTES` (défaut 1440 = 24 h).
- Dépendance [`dependencies.get_current_user`](backend/dependencies.py) — câblée sur `OAuth2PasswordBearer(tokenUrl="/api/auth/login")`. Lève 401 si token invalide/expiré ou user désactivé.
- Endpoints auth — [`routers/auth.py`](backend/routers/auth.py) :
  - `POST /api/auth/register` — JSON `{email, password, full_name?}` → renvoie `Token` (auto-login).
  - `POST /api/auth/login` — JSON `{email, password}` → `Token`.
  - `GET /api/auth/me` — renvoie l'utilisateur courant.
- **Tous les endpoints métier sont gardés** (`projects`, `generate`, `documents`). Les requêtes sur `projects` filtrent strictement sur `user_id == current_user.id` ; un projet d'un autre user renvoie **404** (pas 403, pour ne pas révéler son existence).

### Authentification — frontend
- Stockage token + user dans `localStorage` ([`lib/auth.ts`](frontend/lib/auth.ts), clés `onz_token` / `onz_user`).
- Client API [`lib/api.ts`](frontend/lib/api.ts) :
  - `apiFetch` ajoute automatiquement `Authorization: Bearer …` (sauf appels publics : `login`, `register`).
  - Sur **401**, purge `localStorage` et lève `UnauthorizedError` — le `AuthContext` le détecte et l'`AuthGuard` redirige vers `/login`.
  - Erreurs typées : `ApiError` (avec `status`) et `UnauthorizedError`.
- Contexte React [`contexts/AuthContext.tsx`](frontend/contexts/AuthContext.tsx) — `useAuth()` expose `{ user, loading, login, register, logout }`. Au montage, restaure depuis `localStorage` et valide le token via `/me` en arrière-plan.
- Composant [`AuthGuard`](frontend/components/AuthGuard.tsx) — wrap des pages privées. Redirige vers `/login?redirect=<chemin>` si non authentifié.
- Pages : [`/login`](frontend/app/login/page.tsx), [`/register`](frontend/app/register/page.tsx) — utilisent [`AuthForm`](frontend/components/AuthForm.tsx) (mode `login`/`register`). Après succès, redirige vers `redirect` query param ou `/mes-projets`.
- [`Navbar`](frontend/components/Navbar.tsx) — affiche initiales + email + menu déconnexion quand auth, boutons « Connexion / S'inscrire » sinon. Liens « Nouveau projet » / « Mes projets » masqués si non auth.
- Pages protégées : `/nouveau-projet` et `/mes-projets` (wrappées dans `<AuthGuard>`). La home `/` reste publique.
- L'`AuthProvider` est branché dans [`app/layout.tsx`](frontend/app/layout.tsx) — toute la SPA en bénéficie.

### Validation des uploads PDF
Trois lignes de défense, dans cet ordre :
1. **Middleware [`BodySizeLimitMiddleware`](backend/middleware.py)** — rejette les requêtes dont le `Content-Length` dépasse **50 MB** (HTTP 413). Évite que Starlette bufferise un payload géant en RAM avant de le passer aux routes.
2. **Validators Pydantic** sur [`schemas/project.py`](backend/schemas/project.py) (`reference_pdfs`) et [`routers/documents.py`](backend/routers/documents.py) (`PrefillRequest.pdf_b64`) — délèguent à [`services/pdf_validation.py`](backend/services/pdf_validation.py).
3. **Module [`pdf_validation.py`](backend/services/pdf_validation.py)** — limites unitaires + magic-bytes :
   - `MAX_PDF_BYTES = 10 MB` (par fichier, après décodage)
   - `MAX_TOTAL_PDFS_BYTES = 30 MB` (somme par requête)
   - `MAX_REFERENCE_PDFS_COUNT = 5` (nombre de fichiers)
   - Vérifie que le base64 est valide ET commence bien par `%PDF-`
   - Toute violation lève `PdfValidationError` → Pydantic la transforme en HTTP 422.

Les constantes sont volontairement codées en dur (pas d'env var) pour ne pas être assouplies sans review explicite.

### Migrations Alembic
- Dossier [`backend/alembic/`](backend/alembic/) — `alembic.ini` + `env.py` configuré pour lire `DATABASE_URL` depuis `.env` et utiliser `Base.metadata` de l'app.
- `env.py` active `render_as_batch=True` quand on est sur SQLite (nécessaire car SQLite ne supporte pas `ALTER COLUMN` nativement).
- Une révision initiale [`771d4ae5e488_initial_schema.py`](backend/alembic/versions/771d4ae5e488_initial_schema.py) crée les tables `users` et `projects` avec leurs index et la FK cascade.
- [`init_db`](backend/database.py) appelle désormais `alembic command.upgrade(cfg, "head")` à chaque démarrage — plus aucun `create_all` ni `ALTER TABLE` ad-hoc.

**Workflow pour une nouvelle migration :**
```powershell
cd backend
.\venv\Scripts\Activate.ps1

# 1. Modifier les modèles SQLAlchemy
# 2. Générer la migration (autodétection des diffs)
alembic revision --autogenerate -m "add_xxx_to_yyy"

# 3. Relire le fichier généré dans alembic/versions/ — autogenerate n'est pas magique
#    (vérifier les types, nullable, indexes, server_default...)

# 4. Appliquer (le startup l'aurait fait, mais pratique pour tester)
alembic upgrade head

# 5. Annuler la dernière révision si besoin
alembic downgrade -1
```

**Cas d'une DB existante sans `alembic_version`** (ex. ancien environnement de dev) :
le startup va échouer car Alembic essaiera de recréer les tables. Solutions :
- soit `del onz_projects.db` puis redémarrer (le plus simple en dev),
- soit `alembic stamp head` une fois, pour marquer la DB comme déjà à HEAD.

---

## Conventions du projet

- **Langue** : tout est en français (UI, prompts, identifiants de champs côté API : `nom`, `pays`, `secteur`, `bailleur`, `probleme_principal`…). Garder cette cohérence.
- **Pas de logs `print`** — utiliser `logger = logging.getLogger(__name__)`. Le format est configuré dans `main.py` ; les libs tierces (`httpx`, `litellm`, `openai`) sont déjà mises en `WARNING`.
- **Pas de secrets en dur** — toute clé API passe par `.env`.
- **Erreurs côté router** : `HTTPException(status_code, detail=…)` avec message en français.
- **Réponses LLM** : nettoyer systématiquement les balises markdown (`raw.removeprefix("```json")`) avant `json.loads` — pattern déjà en place, à reproduire.
- **Frontend** : composants `"use client"` quand interactifs, `lib/api.ts` est l'unique point d'appel HTTP, classes Tailwind utilitaires (couleurs custom : `bleu-marine`, `vert-sauge`, polices `playfair`/`source`).

---

## Limitations connues / état actuel

| Sujet | État |
|---|---|
| Auth | ✅ JWT (HS256, 24 h) — backend + frontend (login/register/logout, AuthGuard) |
| Limites upload PDF | ✅ 10 MB / fichier, 30 MB total, max 5 fichiers, magic-bytes vérifiées + body 50 MB max |
| Tests | 🟡 backend pytest (4 modules, 31 tests) — frontend ❌ |
| CI/CD | ❌ aucun |
| Migrations DB | ✅ Alembic, exécuté automatiquement au startup |
| CORS | ✅ origines + méthodes + headers en allowlist explicite |
| Job queue / async long | 🟡 SSE streaming en place (POST /api/generate/stream) — pas encore de queue persistante |
| Cache LLM | ❌ |
| Monitoring/Sentry | ❌ |
| i18n | ❌ français uniquement |
| Édition post-génération | ❌ document final figé |

Ces points sont à garder en tête : ne pas ajouter de dépendance ou de complexité qui suppose qu'ils existent.

---

## Quand intervenir / ne pas intervenir

- ✅ Toujours respecter le format JSON LLM existant — le `docx_service` en dépend.
- ✅ Toute modification de prompt → tester sur l'exemple du README (Mali / Eau & Assainissement / AFD).
- ✅ Préférer éditer `Stepper.tsx` plutôt que créer de nouveaux composants tant que le découpage n'est pas planifié (cohérence avec l'existant).
- ❌ Ne pas introduire d'ORM/lib lourde (Alembic, Celery, Redis, Sentry) sans validation explicite — l'app est volontairement légère.
- ❌ Ne pas committer `.env`, `onz_projects.db`, `node_modules/`, `venv/`, `__pycache__/`, `documents/`.
- ❌ Ne pas modifier la convention de nommage francophone des champs API.

---

## Roadmap — axes d'amélioration et évolutions

Ces chantiers ont été identifiés lors d'un audit. Ils ne sont **pas** à attaquer spontanément : ils servent de boussole quand une tâche connexe est demandée, ou quand l'utilisateur valide un chantier explicite.

### 🔴 Critique — bloquants pour la production

1. **Authentification & autorisation**
   Tous les endpoints sont publics (`/api/projects`, `/api/generate`, `/api/documents/prefill`). N'importe qui peut lister/supprimer les projets et faire exploser la facture LLM.
   → JWT (FastAPI Users / Authlib), modèle `User` + `Organization`, `Project.user_id`, garde sur tous les endpoints.

2. ~~**Limites sur les uploads PDF**~~ — ✅ implémenté (middleware 50 MB body + validators Pydantic 10/30 MB + magic-bytes).

3. ~~**Migrations Alembic**~~ — ✅ implémenté (révision initiale + `alembic upgrade head` au startup, plus de `create_all` ni d'`ALTER` ad-hoc).

4. ~~**CORS trop permissif**~~ — ✅ implémenté (allowlist explicite des methods/headers, expose `Content-Disposition` pour le téléchargement `.docx`).

### 🟠 Architecture & qualité

5. ~~**Factoriser l'appel LLM**~~ — ✅ implémenté ([`services/llm_client.py`](backend/services/llm_client.py) centralise init litellm, `call_llm`, `parse_json_response`, `azure_extras`). Plus aucune duplication entre `ai_service.py` et `routers/documents.py`.

6. ~~**`MODEL` lu à chaud**~~ — ✅ implémenté (`get_model()`, `supports_native_pdf()`, `_compute_max_tokens()` lus par appel ; modifier `LLM_MODEL` n'exige plus de redémarrage de code).

7. ~~**Externaliser les prompts**~~ — ✅ implémenté (`backend/prompts/*.md` chargés via [`services/prompts.py`](backend/services/prompts.py) avec cache `lru_cache`). Plus aucun prompt en dur dans `ai_service.py` ou `routers/documents.py`. Pour modifier un prompt : éditer le `.md` correspondant et redémarrer le process (cache).

8. **Tests automatisés** — 🟡 partiellement implémenté côté backend ([`tests/`](backend/tests/) — 31 tests sur `pdf_validation`, `prompts`, `schemas/generated`, `auth_service`). Restent à écrire : tests `docx_service` (avec dict `generated` figé), tests d'intégration FastAPI (TestClient), tests contractuels mockant le LLM, et toute la stack frontend (Vitest/Playwright).

9. ~~**Validation de la sortie LLM**~~ — ✅ implémenté ([`schemas/generated.py`](backend/schemas/generated.py) ; top-level strict, nested permissif ; `JSONDecodeError`/`ValidationError` → HTTP 502 avec champs incriminés). Retry/repair non implémenté — chantier à part.

10. **Découper `Stepper.tsx`** — 650 lignes, état + API + rendu mélangés. → `components/steps/Step1Identite.tsx`… + Zod pour la validation (remplace les `if/return` manuels de `validateStep`).

### 🟡 Performance & scalabilité

11. ~~**Génération non bloquante (court terme : SSE)**~~ — ✅ implémenté.
    - Backend : `POST /api/generate/stream` ([`routers/generate.py`](backend/routers/generate.py)) retourne `text/event-stream`. Pipeline `generation` (LiteLLM streamé via [`llm_client.stream_llm`](backend/services/llm_client.py)) → `docx` (via `asyncio.to_thread`) → `persistance` → `done` (avec `project_id`).
    - Events SSE : `phase` (changement), `progress` (cumul de chars LLM, throttlé à 250 ms via `_PROGRESS_TICK_SECONDS`), `error` (message localisé), `done` (`{project_id, filename, chars}`). Erreurs LLM (truncation, JSON invalide, ValidationError) émises proprement comme events `error` plutôt que comme HTTP 5xx.
    - Frontend : [`generateDocumentStream`](frontend/lib/api.ts) (fetch + ReadableStream + parser SSE manuel — `EventSource` ne supporte pas POST/Authorization). [`GenerationLoader`](frontend/components/GenerationLoader.tsx) réactif (libellé phase + compteur de caractères + barre `aria-valuenow`). Après `done`, le client télécharge via `/api/projects/{id}/download`.
    - L'endpoint bloquant `POST /api/generate/` est conservé pour rétrocompat.
    - Moyen terme (job queue ARQ/RQ) toujours en suspens : utile uniquement si la durée dépasse les timeouts proxy.

12. **Upload multipart au lieu de base64** — base64 = +33 % en transit + double mémoire. → `UploadFile`, streaming sur disque temporaire, suppression après génération.

13. **Chunking des PDFs longs** — texte tronqué à 3000 caractères ([`ai_service.py:23`](backend/services/ai_service.py#L23)) → perte d'info sur les gros documents. → Chunking + résumé hiérarchique, ou RAG léger (ChromaDB / pgvector).

14. **PostgreSQL + S3** — SQLite et filesystem local ne tiennent pas en multi-replica + pas de backup auto. → Postgres + stockage S3-compatible (MinIO en self-host).

15. **Cache LLM** — re-générations identiques relancent un appel facturé. LiteLLM supporte le cache Redis nativement → à activer.

### 🟢 UX / Frontend

16. ~~**Auto-save formulaire**~~ — ✅ implémenté ([`Stepper.tsx`](frontend/components/Stepper.tsx) — clé `onz_form_draft_v1` dans `localStorage`, restauration au montage avec bandeau « Brouillon restauré » + bouton réinitialiser, purge automatique sur génération réussie ou nouveau projet).

17. **Prévisualisation + édition** — l'utilisateur reçoit un `.docx` figé. Manque : preview HTML du contenu, régénération section par section, mini-éditeur WYSIWYG (TipTap) pour ajustements avant export.

18. ~~**Feedback temps réel pendant génération**~~ — ✅ implémenté côté UI ([`GenerationLoader`](frontend/components/GenerationLoader.tsx) consomme les events SSE : libellé de phase + caractères cumulés + barre `aria-valuenow`). À enrichir si on découpe la génération en sous-prompts (« introduction… », « cadre logique… ») : aujourd'hui le LLM renvoie un seul gros JSON, on n'a pas de granularité section par section.

19. **A11y** — aucun `aria-*`, pas de gestion de focus dans le stepper, `alert/confirm` natifs. → Toasts (sonner / react-hot-toast), modale custom, focus management.

20. ~~**Centraliser les constantes**~~ — ✅ implémenté ([`frontend/lib/constants.ts`](frontend/lib/constants.ts) — `SECTEURS`, `BAILLEURS`, `SECTOR_COLORS`, `STEP_LABELS` ; types dérivés via `as const`). Importé par `Stepper.tsx` et `ProjectCard.tsx`.

### 🔵 DevOps & observabilité

21. ~~**Healthcheck Docker**~~ — ✅ implémenté (`docker-compose.yml` : healthcheck backend via `python urllib` sur `/health`, frontend via `node http` ; `frontend.depends_on.backend` est passé en `condition: service_healthy`).

22. **Logs structurés (JSON)** — actuellement format texte. → `structlog`, parsable par Loki/Datadog.

23. **Monitoring d'erreurs et de coûts LLM** — aucun Sentry, aucune métrique tokens/latence/coût. Crucial pour une app facturée à l'usage.

24. **CI minimale** — `ruff` + `mypy` + `pytest` + `next build` dans GitHub Actions.

25. **Optimiser l'image Docker backend** — pas de multi-stage, pas de user non-root.

### 🚀 Évolutions fonctionnelles à plus haute valeur

| Évolution | Pourquoi |
|---|---|
| **Templates par bailleur** (AFD, UE, BM, PNUD) avec leur structure exacte | Cœur métier — un doc AFD ≠ doc UE. Aujourd'hui un seul prompt générique. |
| **Marqueurs OECD-DAC, genre, climat** | Critère obligatoire chez les bailleurs. |
| **Mode chat (intake conversationnel)** en plus du formulaire | Pour les ONG terrain qui ne maîtrisent pas un formulaire structuré. |
| **Bibliothèque de projets de référence + RAG** | Few-shot avec les projets passés réussis. |
| **Cadre logique en matrice 4×4 visuelle** | Standard LFA — actuellement listes à puces, non conforme. |
| **Chronogramme Gantt SVG** | Aujourd'hui simple tableau « Trimestre / activités ». |
| **Multi-langue (FR/EN/ES)** | UE/BM exigent l'anglais ; PNUD souvent espagnol. |
| **Dashboard org** (nb projets, taux soumission, budget cumulé) | Valeur côté direction d'ONG. |
| **Connecteurs appels à projets** (AFD AAP, EU Funding & Tenders) | Différenciant — l'app devient un hub. |
| **Export PDF + ODT** | Certains bailleurs exigent un PDF signé. |

### Priorisation indicative (12 semaines)

1. **S1-S2** — Auth + quotas + Alembic + limites upload (sécurité bloquante).
2. **S3-S4** — Tests pytest + validation Pydantic sortie LLM + structlog/Sentry.
3. **S5-S6** — Découpage `Stepper`, autosave, toasts, prévisualisation HTML.
4. **S7-S8** — Job queue + SSE pour la génération + cache LLM.
5. **S9-S10** — Templates par bailleur + régénération section par section.
6. **S11-S12** — i18n + export PDF + dashboard org.
