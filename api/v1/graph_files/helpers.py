import random
import string
from configparser import SectionProxy
from azure.identity.aio import ClientSecretCredential
import pandas as pd
import re
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

    def __init__(self, config: SectionProxy):
        self.settings = config
        client_id = self.settings['clientId']
        tenant_id = self.settings['tenantId']
        client_secret = self.settings['clientSecret']
        # stu_dir_app = self.settings['stu_dir_app']
        # stu_dir_obj = self.settings['stu_dir_obj']
        # course_dir_app = self.settings['course_dir_app']
        # course_dir_obj = self.settings['course_dir_obj']
        self.client_credential = ClientSecretCredential(tenant_id, client_id, client_secret)
        auth_provider = AzureIdentityAuthenticationProvider(self.client_credential)  # type: ignore
        self.request_adapter = GraphRequestAdapter(auth_provider)
        self.app_client = GraphServiceClient(self.request_adapter)

    async def get_students(self):
        pass
    async def get_courses(self):
        pass
    async def get_student_extension_properties(self):
        application_id = self.settings['stu_dir_app']
        extension_request_body = get_available_extension_properties_post_request_body.GetAvailableExtensionPropertiesPostRequestBody()
        extension_request_body.is_synced_from_on_premises = False
        result = await self.app_client.directory_objects.get_available_extension_properties.post(
            extension_request_body)
        student_properties = []
        for value in result.value:
            if value.name[10:42] == re.sub("-", "", application_id):
                student_properties.append(convert_key(value.name))
        student_properties = list(reversed(student_properties))
        return student_properties
        pass


    async def get_course_extension_properties(self):
        pass
    async def verify(self,csv):
        df = pd.read_csv(csv)
        header = df.columns.tolist()


def convert_key(key):
    sliced_key = key.split('_', 2)[-1]
    converted_key = re.sub(r'_', ' ', sliced_key)
    return converted_key

def password_generate_msft():
    characters = string.digits + string.punctuation + string.ascii_uppercase + string.ascii_lowercase
    password = ''.join(random.choice(characters) for i in range(20))
    return password


def attendance_csv_to_json(df_attendance):
    json_data = []

    for _, row in df_attendance.iterrows():
        student_data = {
            'Registration number': int(row['Registration number']),
            'Name': row['Name'],
            'Dates': {}
        }
        for date in df_attendance.columns[2:]:
            student_data['Dates'][date] = row[date]

        json_data.append(student_data)

    return json_data

