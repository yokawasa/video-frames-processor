#!/bin/sh

COSMOSDB_ACCOUNT_NAME="<CUSOMOS DB ACCOUNT NAME>"
RESOURCE_GROUP="<RESOURCE GROUP NAME>"
DATABASE_NAME="<COSMOSDB DB NAME>"
VECTORS_COLLECTION_NAME="<COSMOSDB COLLECTION NAME FOR VECTORS>"
RNNINPUT_COLLECTION_NAME="<COSMOSDB COLLECTION NAME FOR RNNINPUT>"
LEAVES_COLLECTION_NAME="leaves"   # FIXED

echo "Create CosmosDB Account"
az cosmosdb create \
    --name $COSMOSDB_ACCOUNT_NAME \
    --kind GlobalDocumentDB \
    --resource-group $RESOURCE_GROUP

echo "Get Key"
#@az cosmosdb list-keys --name $COSMOSDB_ACCOUNT_NAME --resource-group $RESOURCE_GROUP |grep primaryMasterKey
az cosmosdb list-keys --name $COSMOSDB_ACCOUNT_NAME --resource-group $RESOURCE_GROUP

echo "Create Database"
az cosmosdb database create \
    --name $COSMOSDB_ACCOUNT_NAME \
    --db-name $DATABASE_NAME \
    --resource-group $RESOURCE_GROUP

echo "Create Container"
# Create a container with a partition key and provision 1000 RU/s throughput.
az cosmosdb collection create \
    --resource-group $RESOURCE_GROUP \
    --collection-name $VECTORS_COLLECTION_NAME \
    --name $COSMOSDB_ACCOUNT_NAME \
    --db-name $DATABASE_NAME \
    --partition-key-path /video \
    --throughput 400

# Create a container with a partition key and provision 1000 RU/s throughput.
az cosmosdb collection create \
    --resource-group $RESOURCE_GROUP \
    --collection-name $RNNINPUT_COLLECTION_NAME \
    --name $COSMOSDB_ACCOUNT_NAME \
    --db-name $DATABASE_NAME \
    --partition-key-path /video \
    --throughput 400

# 'leaves' need to be a single collection partition    
# Please see https://github.com/Azure/azure-functions-core-tools/issues/930
az cosmosdb collection create \
    --resource-group $RESOURCE_GROUP \
    --collection-name $LEAVES_COLLECTION_NAME \
    --name $COSMOSDB_ACCOUNT_NAME \
    --db-name $DATABASE_NAME \
    --throughput 400
