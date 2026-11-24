using 'main.bicep'

param projectName = 'divieat'
param environmentName = 'dev'
param location = 'centralus'

// Replaced by deploy.sh with the tag it just pushed. The default is a
// Microsoft sample so the first deploy succeeds before any image exists.
param image = 'mcr.microsoft.com/k8se/quickstart:latest'

// Zero while developing; raise to 1 right before a live demo so the first
// request does not pay for a cold start.
param minReplicas = 0

// Off: a free MongoDB Atlas M0 cluster costs nothing and the driver cannot
// tell the difference. Flip it to true for Cosmos DB serverless instead.
param deployDatabase = false

// Secrets never live in this file. They come from the environment at deploy
// time; see deploy.sh.
param mongodbUri = readEnvironmentVariable('MONGODB_URI', '')
param peyApiKey = readEnvironmentVariable('PEY_API_KEY', '')
param peyWebhookSecret = readEnvironmentVariable('PEY_WEBHOOK_SECRET', '')
param peyBankAccountId = readEnvironmentVariable('PEY_BANK_ACCOUNT_ID', '')

// Pey has no sandbox. Leave this on until you mean to move real money.
param testMode = true
param testMaxAmountMxn = '1'
