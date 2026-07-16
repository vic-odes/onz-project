// =============================================================================
// ONZ Projet — Infrastructure plateforme (Azure Container Apps)
// -----------------------------------------------------------------------------
// Provisionne tout ce qui ne dépend PAS des images applicatives :
//   - Log Analytics + Application Insights (observabilité)
//   - Azure Container Registry (stockage des images)
//   - Storage Account + partage Azure Files (persistance SQLite)
//   - Container Apps Environment + lien de stockage Azure Files
//   - Key Vault (clés d'API des modèles LLM)
//   - Identité managée + rôles (AcrPull, Key Vault Secrets User)
//
// À déployer AVANT de construire/pousser les images, puis à enchaîner avec
// apps.bicep une fois les images présentes dans l'ACR.
// =============================================================================

targetScope = 'resourceGroup'

@description('Préfixe appliqué aux noms de ressources (minuscules, alphanumérique).')
@minLength(2)
@maxLength(10)
param namePrefix string = 'onz'

@description('Région Azure. Par défaut, celle du groupe de ressources.')
param location string = resourceGroup().location

@description('Tags appliqués à toutes les ressources.')
param tags object = {
  application: 'onz-projet'
  managedBy: 'bicep'
}

// -----------------------------------------------------------------------------
// Noms de ressources (les ressources globalement uniques utilisent uniqueString)
// -----------------------------------------------------------------------------
var suffix = uniqueString(resourceGroup().id)
var acrName = toLower('${namePrefix}acr${suffix}')
var storageName = toLower('${namePrefix}st${suffix}')
var keyVaultName = toLower('${namePrefix}-kv-${suffix}')
var logAnalyticsName = '${namePrefix}-logs'
var appInsightsName = '${namePrefix}-ai'
var environmentName = '${namePrefix}-env'
var identityName = '${namePrefix}-id'
var fileShareName = 'data'
var envStorageName = 'onzdata'

// Identifiants de rôles intégrés Azure
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
var kvSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'

// -----------------------------------------------------------------------------
// Identité managée partagée (pull ACR + lecture des secrets Key Vault)
// -----------------------------------------------------------------------------
resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
  tags: tags
}

// -----------------------------------------------------------------------------
// Observabilité
// -----------------------------------------------------------------------------
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsName
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

// -----------------------------------------------------------------------------
// Container Registry
// -----------------------------------------------------------------------------
resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    // Pas d'utilisateur admin : l'accès se fait via l'identité managée (AcrPull)
    adminUserEnabled: false
  }
}

resource acrPullAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, identity.id, acrPullRoleId)
  scope: registry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// -----------------------------------------------------------------------------
// Stockage — partage Azure Files pour la base SQLite persistante
// -----------------------------------------------------------------------------
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

resource fileServices 'Microsoft.Storage/storageAccounts/fileServices@2023-05-01' = {
  parent: storage
  name: 'default'
}

resource fileShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01' = {
  parent: fileServices
  name: fileShareName
  properties: {
    accessTier: 'TransactionOptimized'
    shareQuota: 5
  }
}

// -----------------------------------------------------------------------------
// Key Vault (RBAC) — stocke la clé d'API du modèle LLM
// -----------------------------------------------------------------------------
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: tags
  properties: {
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    publicNetworkAccess: 'Enabled'
  }
}

resource kvSecretsUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, identity.id, kvSecretsUserRoleId)
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', kvSecretsUserRoleId)
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// -----------------------------------------------------------------------------
// Container Apps Environment + lien de stockage Azure Files
// -----------------------------------------------------------------------------
resource acaEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: environmentName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

resource envStorage 'Microsoft.App/managedEnvironments/storages@2024-03-01' = {
  parent: acaEnvironment
  name: envStorageName
  properties: {
    azureFile: {
      accountName: storage.name
      accountKey: storage.listKeys().keys[0].value
      shareName: fileShareName
      accessMode: 'ReadWrite'
    }
  }
}

// -----------------------------------------------------------------------------
// Sorties consommées par le workflow CI et apps.bicep
// -----------------------------------------------------------------------------
output acrName string = registry.name
output acrLoginServer string = registry.properties.loginServer
output environmentId string = acaEnvironment.id
output environmentDefaultDomain string = acaEnvironment.properties.defaultDomain
output keyVaultName string = keyVault.name
output storageName string = storageName
output envStorageName string = envStorageName
output managedIdentityId string = identity.id
output managedIdentityClientId string = identity.properties.clientId
output logAnalyticsWorkspaceId string = logAnalytics.id
output appInsightsConnectionString string = appInsights.properties.ConnectionString
