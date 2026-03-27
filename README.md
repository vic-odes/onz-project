# ONZ Projet

Assistant intelligent de montage de projets de développement international.

L'utilisateur remplit un formulaire guidé (5 étapes), et l'application génère automatiquement un document Word (.docx) professionnel prêt à soumettre à des bailleurs (AFD, UE, Banque mondiale, PNUD, etc.).

---

## Stack technique

| Couche       | Technologie                        |
|--------------|------------------------------------|
| Frontend     | Next.js 14 + TypeScript + Tailwind |
| Backend      | FastAPI — Python 3.13              |
| Couche IA    | LiteLLM (abstraction multi-LLM)    |
| Export       | python-docx                        |
| Base de données | SQLite + SQLAlchemy             |

---

## Installation

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Éditer .env et renseigner la clé API du modèle choisi
uvicorn main:app --reload
```

L'API est disponible sur **http://localhost:8000**
Documentation interactive : **http://localhost:8000/docs**

### Frontend

```bash
cd frontend
npm install
npm run dev
```

L'interface est disponible sur **http://localhost:3000**

---

## Changer de modèle IA

Éditer `backend/.env` :

```env
# Anthropic (défaut)
LLM_MODEL=claude-sonnet-4-20250514
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-...

# Google Gemini
LLM_MODEL=gemini/gemini-1.5-pro
GEMINI_API_KEY=...

# Mistral
LLM_MODEL=mistral/mistral-large-latest
MISTRAL_API_KEY=...

# Ollama (local, aucune clé requise)
LLM_MODEL=ollama/llama3
```

Aucune modification du code applicatif n'est nécessaire — uniquement ce fichier `.env`.

---

## Structure du projet

```
onz-project/
├── frontend/
│   ├── app/
│   │   ├── page.tsx                  # Page d'accueil
│   │   ├── nouveau-projet/page.tsx   # Formulaire multi-étapes
│   │   ├── mes-projets/page.tsx      # Liste des projets
│   │   └── layout.tsx
│   ├── components/
│   │   ├── Stepper.tsx               # Formulaire 5 étapes
│   │   ├── ProjectCard.tsx           # Carte projet
│   │   ├── GenerationLoader.tsx      # Loader animé + téléchargement
│   │   └── Navbar.tsx
│   └── lib/api.ts                    # Client API
│
├── backend/
│   ├── main.py                       # Entrée FastAPI + CORS
│   ├── routers/
│   │   ├── projects.py               # CRUD projets (SQLite)
│   │   └── generate.py               # Génération + export Word
│   ├── services/
│   │   ├── ai_service.py             # ⭐ LiteLLM — seul fichier IA
│   │   └── docx_service.py           # Génération Word
│   ├── models/project.py
│   ├── schemas/project.py
│   ├── database.py
│   ├── .env                          # Non versionné
│   ├── .env.example                  # Template versionné
│   └── requirements.txt
│
└── README.md
```

---

## Test de démarrage

Une fois lancé, tester avec :

- **Nom** : Accès à l'eau potable en milieu rural
- **Pays** : Mali
- **Secteur** : Eau & Assainissement
- **Bailleur** : AFD
- **Durée** : 24 mois
- **Budget** : 500 000 USD
