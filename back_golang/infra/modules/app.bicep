@description('The CoDi API as a container app, pulling from ACR with a managed identity.')
param name string
param location string
param tags object = {}

param environmentId string
param registryName string
param image string

@description('Smallest combination Container Apps allows. A static Go binary on scratch does not need more.')
param cpu string = '0.25'
param memory string = '0.5Gi'

@description('Zero means no cost while idle, at the price of a cold start on the first request. Raise it to 1 before a live demo.')
@minValue(0)
param minReplicas int = 0

@minValue(1)
param maxReplicas int = 1

param databaseName string
param qrExpirationSeconds int
param testMode bool
param testMaxAmountMxn string

@secure()
param peyApiKey string
@secure()
param peyWebhookSecret string
@secure()
param mongodbUri string

param peyBankAccountId string = ''

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: registryName
}

// A user-assigned identity so the pull permission survives the app being
// recreated, instead of being tied to its lifetime.
resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${name}-id'
  location: location
  tags: tags
}

var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

resource pullPermission 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: registry
  name: guid(registry.id, identity.id, acrPullRoleId)
  properties: {
    principalId: identity.properties.principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalType: 'ServicePrincipal'
  }
}

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identity.id}': {}
    }
  }
  properties: {
    environmentId: environmentId
    configuration: {
      // External ingress is not a convenience here: Pey posts its webhook to
      // a public HTTPS URL, and Container Apps terminates TLS for free. That
      // is the whole reason this has to live somewhere reachable.
      ingress: {
        external: true
        targetPort: 8080
        transport: 'auto'
        allowInsecure: false
      }
      registries: [
        {
          server: registry.properties.loginServer
          identity: identity.id
        }
      ]
      secrets: [
        { name: 'pey-api-key', value: peyApiKey }
        { name: 'pey-webhook-secret', value: peyWebhookSecret }
        { name: 'mongodb-uri', value: mongodbUri }
      ]
    }
    template: {
      containers: [
        {
          name: 'api'
          image: image
          resources: {
            cpu: json(cpu)
            memory: memory
          }
          env: [
            { name: 'PORT', value: '8080' }
            { name: 'DATABASE_NAME', value: databaseName }
            { name: 'PEY_QR_EXPIRATION_SECONDS', value: string(qrExpirationSeconds) }
            { name: 'PEY_TEST_MODE', value: testMode ? 'true' : 'false' }
            { name: 'PEY_TEST_MAX_AMOUNT_MXN', value: testMaxAmountMxn }
            { name: 'PEY_BANK_ACCOUNT_ID', value: peyBankAccountId }
            { name: 'PEY_API_KEY', secretRef: 'pey-api-key' }
            { name: 'PEY_WEBHOOK_SECRET', secretRef: 'pey-webhook-secret' }
            { name: 'MONGODB_URI', secretRef: 'mongodb-uri' }
          ]
          probes: [
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: 8080
              }
              initialDelaySeconds: 2
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
      }
    }
  }
  dependsOn: [
    pullPermission
  ]
}

output fqdn string = app.properties.configuration.ingress.fqdn
output webhookUrl string = 'https://${app.properties.configuration.ingress.fqdn}/webhooks/pey/codi'
