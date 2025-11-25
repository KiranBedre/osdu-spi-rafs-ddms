# ⚠️ Note

This README describes a CSP-specific implementation of a blob storage provider (`AzureBlobStorage`).  
It is **not actively used or maintained** in the main CI/CD pipelines.  

The primary data handling in **CI** environment is **cloud-agnostic**, using the core services `dataset` and `storage`.  
CSP-specific setups should only be used or modified by the teams responsible for maintaining them.

## Blob Storage  

The [`AzureBlobStorage`](../../../app/providers/dependencies/az/blob_storage.py?ref_type=heads#L45) class implements the `IBlobStorage` interface and relies on [`StoragePartitionInfo`](../../../app/providers/dependencies/az/storage_account_info.py?ref_type=heads#L33). Under the hood, it leverages the **Partition service** and **Azure Key Vault** to retrieve container credentials securely.  

### Required Environment Variables  

To configure the `AzureBlobStorage` class, the following environment variables are required:  

```bash
AZ_KEYVAULT_URL="<valid_keyvault_url>"
AZ_USE_PARTITION_SERVICE=True  # If False, key vault keys are inferred (defaults to True)
AZ_CONTAINER_NAME="rafs-ddms"  # Name of the dedicated container (defaults to 'rafs-ddms')
AZ_AAD_CLIENT_ID_KEY="aad-client-id"  # Scope for request token to Partition service (defaults to 'aad-client-id')
```

### Authentication and Local Development  

The `AzureBlobStorage` class uses [DefaultAzureCredential](https://learn.microsoft.com/en-us/python/api/azure-identity/azure.identity.aio.defaultazurecredential?view=azure-python), meaning that when deployed, the necessary authentication environment variables are automatically set within the pod via Managed Identity.  

For **local development** with `AzureBlobStorage`, authentication is required. This can be done by setting the following environment variables, which must belong to a principal with access to the Key Vault:  

```bash
AZURE_CLIENT_ID="client_id"
AZURE_TENANT_ID="tenant_id"
AZURE_CLIENT_SECRET="client_secret"
```

This ensures secure access to Azure resources while maintaining flexibility for development and deployment.  
