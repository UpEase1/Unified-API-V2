import random
import string
from configparser import SectionProxy
import pandas as pd
import re
from .singletons import GraphServiceClientSingleton

from azure.identity.aio import ClientSecretCredential
from kiota_authentication_azure.azure_identity_authentication_provider import (
    AzureIdentityAuthenticationProvider
)
from msgraph import GraphRequestAdapter, GraphServiceClient
from msgraph.generated.applications.get_available_extension_properties import \
    get_available_extension_properties_post_request_body

class Helpers:
    settings: SectionProxy
    client_credential: ClientSecretCredential
    request_adapter: GraphRequestAdapter
    app_client: GraphServiceClient

    def __init__(self,config:SectionProxy):
        self.app_client = GraphServiceClientSingleton.get_instance()

def convert_key(key):
    sliced_key = key.split('_', 2)[-1]
    converted_key = re.sub(r'_', ' ', sliced_key)
    return converted_key

def password_generate_msft():
    characters = string.digits + string.punctuation + string.ascii_uppercase + string.ascii_lowercase
    password = ''.join(random.choice(characters) for i in range(20))
    return password

def generate_md_table(data):
    # Start the Markdown table
    md = ""

    # Generate the table headers
    headers = data[0].keys()
    md += "| " + " | ".join(headers) + " |\n"

    # Generate the separator
    md += "| " + " | ".join(["---"] * len(headers)) + " |\n"

    # Generate the table rows
    for item in data:
        row = "| " + " | ".join(str(value) for value in item.values()) + " |\n"
        md += row

    return md
