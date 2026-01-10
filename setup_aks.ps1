


$RESOURCE_GROUP = "cloud-project-rg"
$LOCATION = "italynorth" # Change if needed
$ACR_NAME = "redactionacr$((Get-Random -Minimum 1000 -Maximum 9999))" # Unique name
$AKS_CLUSTER_NAME = "redaction-cluster"

# 1. Authenticate to Azure CLI
Write-Host "Logging into Azure..."
az login

# 2. Provision Azure Resource Group
Write-Host "Creating Resource Group: $RESOURCE_GROUP..."
az group create --name $RESOURCE_GROUP --location $LOCATION

# 3. Provision Azure Container Registry instance
Write-Host "Creating ACR: $ACR_NAME..."
az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic

# 4. Provision Kubernetes Cluster with ACR integration 
Write-Host "Creating AKS Cluster with 2 Nodes..."
az aks create `
    --resource-group $RESOURCE_GROUP `
    --name $AKS_CLUSTER_NAME `
    --node-count 2 `
    --generate-ssh-keys `
    --attach-acr $ACR_NAME

# 5. Retrieve cluster credentials for kubectl context
Write-Host "Getting Cluster Credentials..."
az aks get-credentials --resource-group $RESOURCE_GROUP --name $AKS_CLUSTER_NAME

Write-Host "---------------------------------------------------"
Write-Host "SETUP COMPLETE!"
Write-Host "---------------------------------------------------"
Write-Host "Now, go to your GitHub Repository > Settings > Secrets and enforce these secrets:"
Write-Host ""
Write-Host "ACR_NAME = $ACR_NAME"
Write-Host "RESOURCE_GROUP = $RESOURCE_GROUP"
Write-Host "AKS_CLUSTER_NAME = $AKS_CLUSTER_NAME"
Write-Host "AZURE_CREDENTIALS = (Output of the command below)"
Write-Host ""
Write-Host "Command to generate credentials:"
Write-Host "az ad sp create-for-rbac --name 'myApp' --role contributor --scopes /subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP --sdk-auth"
