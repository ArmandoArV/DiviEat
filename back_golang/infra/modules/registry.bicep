@description('Azure Container Registry that holds the API image.')
param name string
param location string
param tags object = {}

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    // The admin account is a shared username and password that cannot be
    // scoped or rotated per consumer. The container app pulls with a managed
    // identity instead, so there is no credential to leak.
    adminUserEnabled: false
  }
}

output id string = registry.id
output loginServer string = registry.properties.loginServer
output name string = registry.name
