// =============================================================================
// ONZ Projet — Container Apps (backend FastAPI + frontend Next.js)
// -----------------------------------------------------------------------------
// À déployer APRÈS platform.bicep et APRÈS que les images aient été poussées
// dans l'ACR. Les URLs backend/frontend sont déterministes (nom de l'app +
// defaultDomain de l'environnement), ce qui permet au CI de construire l'image
// frontend avec la bonne valeur de NEXT_PUBLIC_API_URL avant ce déploiement.
// =============================================================================

targetScope = 'resourceGroup'

@description('Préfixe appliqué aux noms de ressources.')
param namePrefix string = 'onz'

@description('Région Azure.')
param location string = resourceGroup().location

@description('Tags appliqués à toutes les ressources.')
param tags object = {
  application: 'onz-projet'
  managedBy: 'bicep'
}

// --- Sorties de platform.bicep ----------------------------------------------
@description('Resource ID du Container Apps Environment.')
param environmentId string

@description('Serveur de connexion de l\'ACR (ex. onzacrxxxx.azurecr.io).')
param acrLoginServer string

@description('Resource ID de l\'identité managée (pull ACR + secrets KV).')
param managedIdentityId string

@description('Nom du lien de stockage Azure Files déclaré dans l\'environnement.')
param envStorageName string = 'onzdata'

@description('Nom du Key Vault contenant le secret llm-api-key.')
param keyVaultName string

// --- Images (fournies par le CI, taggées au SHA du commit) ------------------
@description('Image backend complète, ex. onzacrxxxx.azurecr.io/onz-backend:sha.')
param backendImage string

@description('Image frontend complète, ex. onzacrxxxx.azurecr.io/onz-frontend:sha.')
param frontendImage string

// --- URLs publiques (déterministes, calculées par le CI) --------------------
@description('URL publique du backend (https://onz-backend.<defaultDomain>).')
param backendUrl string

@description('URL publique du frontend (https://onz-frontend.<defaultDomain>).')
param frontendUrl string

// --- Configuration LLM ------------------------------------------------------
@description('Identifiant du modèle LiteLLM (ex. claude-sonnet-4-20250514, gpt-4o, azure/mon-deploiement).')
param llmModel string = 'claude-sonnet-4-20250514'

@description('Nom de la variable d\'environnement recevant la clé d\'API selon le fournisseur.')
@allowed([
  'ANTHROPIC_API_KEY'
  'OPENAI_API_KEY'
  'GEMINI_API_KEY'
  'MISTRAL_API_KEY'
  'AZURE_API_KEY'
])
param llmApiKeyEnvVar string = 'ANTHROPIC_API_KEY'

@description('Endpoint Azure OpenAI (uniquement pour le fournisseur Azure). Vide sinon.')
param azureApiBase string = ''

@description('Version d\'API Azure OpenAI (uniquement pour le fournisseur Azure). Vide sinon.')
param azureApiVersion string = '2024-02-01'

// --- Ressources allouées ----------------------------------------------------
param backendCpu string = '0.5'
param backendMemory string = '1.0Gi'
param frontendCpu string = '0.5'
param frontendMemory string = '1.0Gi'
param frontendMinReplicas int = 1
param frontendMaxReplicas int = 3

// -----------------------------------------------------------------------------
var backendName = '${namePrefix}-backend'
var frontendName = '${namePrefix}-frontend'
var keyVaultSecretUri = 'https://${keyVaultName}${environment().suffixes.keyvaultDns}/secrets/llm-api-key'

// Variables Azure OpenAI ajoutées uniquement si un endpoint est fourni
var azureExtraEnv = empty(azureApiBase) ? [] : [
  {
    name: 'AZURE_API_BASE'
    value: azureApiBase
  }
  {
    name: 'AZURE_API_VERSION'
    value: azureApiVersion
  }
]

var backendBaseEnv = [
  {
    name: 'DATABASE_URL'
    value: 'sqlite:////app/data/onz_projects.db'
  }
  {
    name: 'LLM_MODEL'
    value: llmModel
  }
  {
    name: 'CORS_ORIGINS'
    value: frontendUrl
  }
  {
    name: llmApiKeyEnvVar
    secretRef: 'llm-api-key'
  }
]

var identityConfig = {
  type: 'UserAssigned'
  userAssignedIdentities: {
    '${managedIdentityId}': {}
  }
}

var registriesConfig = [
  {
    server: acrLoginServer
    identity: managedIdentityId
  }
]

// -----------------------------------------------------------------------------
// Backend — FastAPI. Ingress externe (appelé directement par le navigateur).
// SQLite sur Azure Files => strictement 1 réplica (un seul writer).
// -----------------------------------------------------------------------------
resource backend 'Microsoft.App/containerApps@2024-03-01' = {
  name: backendName
  location: location
  tags: tags
  identity: identityConfig
  properties: {
    environmentId: environmentId
    configuration: {
      activeRevisionsMode: 'Single'
      registries: registriesConfig
      secrets: [
        {
          name: 'llm-api-key'
          keyVaultUrl: keyVaultSecretUri
          identity: managedIdentityId
        }
      ]
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: backendImage
          resources: {
            cpu: json(backendCpu)
            memory: backendMemory
          }
          env: concat(backendBaseEnv, azureExtraEnv)
          volumeMounts: [
            {
              volumeName: 'data'
              mountPath: '/app/data'
            }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 10
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 5
              periodSeconds: 10
            }
          ]
        }
      ]
      volumes: [
        {
          name: 'data'
          storageType: 'AzureFile'
          storageName: envStorageName
        }
      ]
      scale: {
        // SQLite + Azure Files : un seul writer autorisé.
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
}

// -----------------------------------------------------------------------------
// Frontend — Next.js standalone. Ingress externe.
// -----------------------------------------------------------------------------
resource frontend 'Microsoft.App/containerApps@2024-03-01' = {
  name: frontendName
  location: location
  tags: tags
  identity: identityConfig
  properties: {
    environmentId: environmentId
    configuration: {
      activeRevisionsMode: 'Single'
      registries: registriesConfig
      ingress: {
        external: true
        targetPort: 3000
        transport: 'auto'
        allowInsecure: false
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: frontendImage
          resources: {
            cpu: json(frontendCpu)
            memory: frontendMemory
          }
          env: [
            {
              name: 'NEXT_PUBLIC_API_URL'
              value: backendUrl
            }
            {
              name: 'NODE_ENV'
              value: 'production'
            }
          ]
          probes: [
            {
              type: 'Readiness'
              httpGet: {
                path: '/'
                port: 3000
              }
              initialDelaySeconds: 5
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: frontendMinReplicas
        maxReplicas: frontendMaxReplicas
      }
    }
  }
}

// -----------------------------------------------------------------------------
output backendFqdn string = backend.properties.configuration.ingress.fqdn
output frontendFqdn string = frontend.properties.configuration.ingress.fqdn
output backendUrlOut string = 'https://${backend.properties.configuration.ingress.fqdn}'
output frontendUrlOut string = 'https://${frontend.properties.configuration.ingress.fqdn}'
