@description('Cosmos DB with the MongoDB API, serverless. Optional: skip it and point MONGODB_URI at an existing cluster instead.')
param name string
param location string
param databaseName string
param tags object = {}

resource account 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: name
  location: location
  tags: tags
  kind: 'MongoDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    // Serverless bills per request rather than per provisioned hour, which is
    // the right shape for a bill that is idle between services.
    capabilities: [
      { name: 'EnableServerless' }
      { name: 'EnableMongo' }
    ]
    apiProperties: {
      serverVersion: '7.0'
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
      }
    ]
    minimalTlsVersion: 'Tls12'
  }
}

resource database 'Microsoft.DocumentDB/databaseAccounts/mongodbDatabases@2024-05-15' = {
  parent: account
  name: databaseName
  properties: {
    resource: {
      id: databaseName
    }
  }
}

// The key never leaves the deployment: it is read here and handed straight to
// the container app's secret store, so it is not printed or kept anywhere.
#disable-next-line outputs-should-not-contain-secrets
output connectionString string = account.listConnectionStrings().connectionStrings[0].connectionString
