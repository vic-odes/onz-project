# Déploiement sur Azure — Container Apps

Infrastructure as Code (Bicep) pour héberger ONZ Projet sur **Azure Container Apps**.

## Architecture cible

```
                      Internet
                         │
        ┌────────────────┴─────────────────┐
        ▼                                  ▼
┌──────────────────┐             ┌──────────────────┐
│  Frontend (ACA)  │  fetch API  │  Backend (ACA)   │
│  Next.js :3000   │ ──────────► │  FastAPI :8000   │
│  ingress externe │             │  ingress externe │
└──────────────────┘             └────────┬─────────┘
                                          │ volume
                                          ▼
                                 ┌──────────────────┐
                                 │  Azure Files      │
                                 │  SQLite /app/data │
                                 └──────────────────┘

  Container Registry (images)   Key Vault (clé LLM)   Log Analytics + App Insights
  Identité managée : pull ACR + lecture des secrets Key Vault
```

| Composant Azure | Rôle |
|-----------------|------|
| **Azure Container Apps** | Hébergement des conteneurs backend et frontend (HTTPS, scaling, révisions) |
| **Azure Container Registry** | Stockage des images Docker |
| **Azure Files** (Storage Account) | Persistance de la base SQLite (`/app/data`) |
| **Azure Key Vault** | Clé d'API du modèle LLM, lue via identité managée |
| **Log Analytics + Application Insights** | Logs et observabilité |
| **Identité managée** | Pull ACR (`AcrPull`) + lecture Key Vault (`Key Vault Secrets User`) — aucun mot de passe stocké |

### Notes importantes

- **Le backend est public** : le navigateur appelle l'API directement (`NEXT_PUBLIC_API_URL`), donc son ingress est externe.
- **Backend = 1 seul réplica.** SQLite sur Azure Files n'autorise qu'un writer. Voir [Passer à PostgreSQL](#passer-à-postgresql) pour lever cette limite et scaler horizontalement.
- **URLs déterministes** : `https://<prefix>-backend.<defaultDomain>` et `https://<prefix>-frontend.<defaultDomain>`. Le CI construit l'image frontend avec la bonne `NEXT_PUBLIC_API_URL` avant de déployer.

---

## Fichiers

| Fichier | Contenu |
|---------|---------|
| `platform.bicep` | ACR, environnement ACA, stockage, Key Vault, identité, observabilité |
| `apps.bicep` | Les deux Container Apps (backend + frontend) |
| `platform.parameters.json` | Paramètres de la plateforme (préfixe, région) |
| `../.github/workflows/deploy-azure.yml` | Pipeline de déploiement complet |

---

## Prérequis

- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) ≥ 2.60
- Extension Bicep : `az bicep install`
- Une souscription Azure et les droits `Contributor` + `User Access Administrator` (pour créer les attributions de rôles) sur le groupe de ressources.

---

## Option A — Déploiement via GitHub Actions (recommandé)

### 1. Configurer l'authentification OIDC

Créez une application d'entreprise avec identité fédérée (pas de secret à stocker) :

```bash
az ad app create --display-name "onz-projet-github"
# Récupérez appId (= AZURE_CLIENT_ID) puis créez le service principal :
az ad sp create --id <appId>

# Attribuez les rôles sur la souscription (ou le groupe de ressources) :
az role assignment create --assignee <appId> --role "Contributor" \
  --scope /subscriptions/<subId>
az role assignment create --assignee <appId> --role "User Access Administrator" \
  --scope /subscriptions/<subId>
```

Ajoutez les identifiants fédérés pour la branche `main` et les déclenchements manuels :

```bash
az ad app federated-credential create --id <appId> --parameters '{
  "name": "github-main",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:vic-odes/onz-project:ref:refs/heads/main",
  "audiences": ["api://AzureADTokenExchange"]
}'
```

### 2. Renseigner les secrets et variables du dépôt

**Secrets** (`Settings > Secrets and variables > Actions > Secrets`) :

| Secret | Valeur |
|--------|--------|
| `AZURE_CLIENT_ID` | `appId` de l'étape 1 |
| `AZURE_TENANT_ID` | ID du tenant Azure AD |
| `AZURE_SUBSCRIPTION_ID` | ID de la souscription |
| `LLM_API_KEY` | Clé d'API du modèle (Anthropic, OpenAI, …) |

**Variables** (`… > Variables`) :

| Variable | Exemple |
|----------|---------|
| `AZURE_RESOURCE_GROUP` | `rg-onz-projet` |
| `AZURE_LOCATION` | `westeurope` |
| `NAME_PREFIX` | `onz` |
| `LLM_MODEL` | `claude-sonnet-4-20250514` |
| `LLM_API_KEY_ENV_VAR` | `ANTHROPIC_API_KEY` |
| `AZURE_API_BASE` | *(vide, sauf Azure OpenAI)* |
| `AZURE_API_VERSION` | *(vide, sauf Azure OpenAI)* |

### 3. Lancer le déploiement

Poussez sur `main` ou lancez le workflow manuellement (`Actions > Déploiement Azure Container Apps > Run workflow`). Les URLs finales apparaissent dans le récapitulatif du job.

---

## Option B — Déploiement manuel (Azure CLI)

```bash
az login
RG=rg-onz-projet
LOCATION=westeurope
PREFIX=onz

az group create -n $RG -l $LOCATION

# 1. Plateforme
az deployment group create -g $RG \
  --template-file infra/platform.bicep \
  --parameters infra/platform.parameters.json

# Récupérer les sorties
DEPLOY=$(az deployment group show -g $RG -n platform --query properties.outputs -o json)
ACR=$(echo $DEPLOY | jq -r '.acrLoginServer.value')
ACR_NAME=$(echo $DEPLOY | jq -r '.acrName.value')
ENV_ID=$(echo $DEPLOY | jq -r '.environmentId.value')
DOMAIN=$(echo $DEPLOY | jq -r '.environmentDefaultDomain.value')
KV=$(echo $DEPLOY | jq -r '.keyVaultName.value')
IDENTITY=$(echo $DEPLOY | jq -r '.managedIdentityId.value')

# 2. Clé LLM dans Key Vault
az keyvault secret set --vault-name $KV --name llm-api-key --value "<VOTRE_CLE>"

# 3. URLs déterministes
BACKEND_URL="https://${PREFIX}-backend.${DOMAIN}"
FRONTEND_URL="https://${PREFIX}-frontend.${DOMAIN}"

# 4. Build & push
az acr login --name $ACR_NAME
docker build -t $ACR/onz-backend:latest ./backend
docker push $ACR/onz-backend:latest
docker build --build-arg NEXT_PUBLIC_API_URL=$BACKEND_URL \
  -t $ACR/onz-frontend:latest ./frontend
docker push $ACR/onz-frontend:latest

# 5. Container Apps
az deployment group create -g $RG \
  --template-file infra/apps.bicep \
  --parameters \
    environmentId=$ENV_ID \
    acrLoginServer=$ACR \
    managedIdentityId=$IDENTITY \
    keyVaultName=$KV \
    backendImage=$ACR/onz-backend:latest \
    frontendImage=$ACR/onz-frontend:latest \
    backendUrl=$BACKEND_URL \
    frontendUrl=$FRONTEND_URL \
    llmModel=claude-sonnet-4-20250514 \
    llmApiKeyEnvVar=ANTHROPIC_API_KEY
```

---

## Changer de fournisseur de modèle

Le code applicatif ne change pas — seuls le modèle et le nom de variable d'API varient.

| Fournisseur | `LLM_MODEL` | `LLM_API_KEY_ENV_VAR` |
|-------------|-------------|------------------------|
| Anthropic | `claude-sonnet-4-20250514` | `ANTHROPIC_API_KEY` |
| OpenAI | `gpt-4o` | `OPENAI_API_KEY` |
| Google Gemini | `gemini/gemini-1.5-pro` | `GEMINI_API_KEY` |
| Mistral | `mistral/mistral-large-latest` | `MISTRAL_API_KEY` |
| **Azure OpenAI** | `azure/<nom-deploiement>` | `AZURE_API_KEY` + `AZURE_API_BASE`/`AZURE_API_VERSION` |

Pour **Azure OpenAI** (données hébergées dans votre tenant, pertinent pour les dossiers bailleurs) : renseignez `AZURE_API_BASE` (endpoint) et `AZURE_API_VERSION` dans les variables du dépôt, et mettez `LLM_API_KEY_ENV_VAR=AZURE_API_KEY`.

---

## Passer à PostgreSQL

SQLite sur Azure Files limite le backend à 1 réplica. Pour scaler horizontalement, passez à **Azure Database for PostgreSQL – Flexible Server** :

1. Ajoutez `psycopg[binary]` à `backend/requirements.txt`.
2. Rendez le `connect_args` conditionnel dans `backend/database.py` (l'option `check_same_thread` est spécifique à SQLite) :
   ```python
   connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
   engine = create_engine(DATABASE_URL, connect_args=connect_args)
   ```
3. Provisionnez le serveur et pointez `DATABASE_URL` dessus :
   ```
   postgresql+psycopg://<user>:<pwd>@<serveur>.postgres.database.azure.com/onz?sslmode=require
   ```
4. Retirez le volume Azure Files du backend et relevez `maxReplicas` dans `apps.bicep`.

---

## Nettoyage

```bash
az group delete -n rg-onz-projet --yes --no-wait
```
