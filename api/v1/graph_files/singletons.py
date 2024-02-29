from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient
from .config import read_azure_config
from azure.cosmos import CosmosClient
from openai import AsyncAzureOpenAI

import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion, AzureChatCompletion

azure_config = read_azure_config()

class ClientSecretCredentialSingleton:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ClientSecretCredential(
                tenant_id=azure_config.get('tenantId'),
                client_id=azure_config.get('clientId'),
                client_secret=azure_config.get('clientSecret')
            )
        return cls._instance

class GraphServiceClientSingleton:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            credential = ClientSecretCredentialSingleton.get_instance()
            cls._instance = GraphServiceClient(credentials=credential, scopes = ['https://graph.microsoft.com/.default'])
        return cls._instance

class CosmosServiceClientSingleton:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            url = azure_config.get('YOUR_COSMOS_DB_URL')
            key = azure_config.get('YOUR_COSMOS_DB_KEY')
            cls._instance = CosmosClient(url,key)
        return cls._instance

class AsyncAzureOpenAIClientSingleton:
    _instance = None

    @classmethod
    def get_azure_openai_client(cls):
        if cls._instance is None:
            api_key = azure_config.get('openai_api_key')
            api_base = azure_config.get('openai_api_base')
            api_version = azure_config.get('openai_api_version')
            cls._instance = AsyncAzureOpenAI(api_key = api_key, api_version = api_version, azure_endpoint=api_base,azure_deployment = 'UpEase-testing')
        return cls._instance
