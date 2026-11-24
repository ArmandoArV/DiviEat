// DiviEat CoDi API on Azure Container Apps.
//
// Sized for a hackathon: the only resource that bills while nothing happens
// is the container registry. The app scales to zero, the logs have a daily
// cap, and the database is off by default — a free MongoDB Atlas M0 cluster
// costs nothing and the driver cannot tell the difference.
targetScope = 'subscription'

@description('Short name that prefixes every resource. Lowercase letters and digits.')
@minLength(3)
@maxLength(12)
param projectName string = 'divieat'

@description('Deployment environment, used in names and tags.')
@allowed(['dev', 'prod'])
param environmentName string = 'dev'

@description('Azure region. Container Apps is not in every region; check before changing.')
param location string = 'centralus'

@description('Image to run, including the tag. Push it to the registry this template creates, then deploy again with the tag.')
param image string = 'mcr.microsoft.com/k8se/quickstart:latest'

@description('Zero costs nothing while idle but adds a cold start to the first request. Set it to 1 before a live demo.')
@minValue(0)
param minReplicas int = 0

@description('Create a Cosmos DB serverless account. Leave it false and pass mongodbUri to use a free Atlas M0 cluster instead.')
param deployDatabase bool = false

@description('Connection string for an existing MongoDB. Required unless deployDatabase is true.')
@secure()
param mongodbUri string = ''

@secure()
param peyApiKey string
@secure()
param peyWebhookSecret string

param peyBankAccountId string = ''
param qrExpirationSeconds int = 900

@description('Pey has no sandbox, so charges are real money. Leave this on until the demo is ready to take an actual payment.')
param testMode bool = true
param testMaxAmountMxn string = '1'

var prefix = '${projectName}-${environmentName}'
var tags = {
  project: projectName
  environment: environmentName
  managedBy: 'bicep'
}

// Registry names allow neither hyphens nor uppercase, and must be unique
// across all of Azure; the subscription id keeps it from colliding.
var registryName = toLower('${projectName}${environmentName}acr${substring(uniqueString(subscription().subscriptionId), 0, 6)}')

resource group 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: 'rg-${prefix}'
  location: location
  tags: tags
}

module registry 'modules/registry.bicep' = {
  scope: group
  name: 'registry'
  params: {
    name: registryName
    location: location
    tags: tags
  }
}

module environment 'modules/environment.bicep' = {
  scope: group
  name: 'environment'
  params: {
    name: 'cae-${prefix}'
    location: location
    tags: tags
  }
}

module database 'modules/database.bicep' = if (deployDatabase) {
  scope: group
  name: 'database'
  params: {
    name: toLower('${prefix}-cosmos-${substring(uniqueString(subscription().subscriptionId), 0, 6)}')
    location: location
    databaseName: projectName
    tags: tags
  }
}

module api 'modules/app.bicep' = {
  scope: group
  name: 'api'
  params: {
    name: 'ca-${prefix}-codi'
    location: location
    tags: tags
    environmentId: environment.outputs.id
    registryName: registry.outputs.name
    image: image
    minReplicas: minReplicas
    databaseName: projectName
    qrExpirationSeconds: qrExpirationSeconds
    testMode: testMode
    testMaxAmountMxn: testMaxAmountMxn
    peyApiKey: peyApiKey
    peyWebhookSecret: peyWebhookSecret
    peyBankAccountId: peyBankAccountId
    // `!` because the module only exists when deployDatabase is true, which is
    // exactly the branch that reads it.
    mongodbUri: deployDatabase ? database!.outputs.connectionString : mongodbUri
  }
}

output resourceGroup string = group.name
output registryLoginServer string = registry.outputs.loginServer
output apiUrl string = 'https://${api.outputs.fqdn}'

@description('Register this in the Pey portal, under the gear next to the API key.')
output webhookUrl string = api.outputs.webhookUrl
