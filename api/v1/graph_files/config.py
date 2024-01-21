from configparser import SectionProxy
from azure.identity.aio import ClientSecretCredential
from msgraph import GraphServiceClient
from azure.cosmos import CosmosClient


def create_graph_service_client(config:SectionProxy):
    client_id = config['clientId']
    tenant_id = config['tenantId']
    client_secret = config['clientSecret']
    scopes = ['https://graph.microsoft.com/.default']
    client_credential = ClientSecretCredential(tenant_id, client_id, client_secret)
    app_client = GraphServiceClient(client_credential, scopes)
    return app_client

def create_cosmos_service_client(config):
    url = config['YOUR_COSMOS_DB_URL']
    key = config['YOUR_COSMOS_DB_KEY']
    cosmos_client = CosmosClient(url,credential=key)
    return cosmos_client

