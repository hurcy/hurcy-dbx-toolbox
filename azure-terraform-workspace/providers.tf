terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">=4.0.0"
    }
    databricks = {
      source  = "databricks/databricks"
      version = ">=1.52.0"
    }
    random = {
      source = "hashicorp/random"
    }
  }
}

provider "azurerm" {
  subscription_id = var.subscription_id
  features {}
}

provider "random" {}

# Databricks provider using Azure CLI authentication
provider "databricks" {
  host      = azurerm_databricks_workspace.ws.workspace_url
  auth_type = "azure-cli"
}
