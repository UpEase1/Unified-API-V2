from configparser import SectionProxy
import pandas as pd
from typing import List
from typing import Dict
import re

from . import helpers

from azure.identity.aio import ClientSecretCredential
from kiota_authentication_azure.azure_identity_authentication_provider import (
    AzureIdentityAuthenticationProvider
)
from msgraph import GraphServiceClient
from msgraph.generated.applications.get_available_extension_properties import \
    get_available_extension_properties_post_request_body
from msgraph.generated.models.password_profile import PasswordProfile
from msgraph.generated.models.user import User
from msgraph.generated.users.users_request_builder import UsersRequestBuilder


class Students:
    settings: SectionProxy
    client_credential: ClientSecretCredential
    app_client: GraphServiceClient

    def __init__(self, config: SectionProxy):
        self.settings = config
        client_id = self.settings['clientId']
        tenant_id = self.settings['tenantId']
        client_secret = self.settings['clientSecret']
        scopes = ['https://graph.microsoft.com/.default']
        self.client_credential = ClientSecretCredential(tenant_id, client_id, client_secret)
        self.app_client = GraphServiceClient(self.client_credential,scopes)

    async def get_all_students(self):
        query_params = UsersRequestBuilder.UsersRequestBuilderGetQueryParameters(
            select=['displayName', 'id', 'faxNumber'],
            orderby=['displayName']
        )
        request_config = UsersRequestBuilder.UsersRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        users = await self.app_client.users.get(request_configuration=request_config)
        student_data = []
        for user in users.value:
            user_data = {}
            user_data['name'] = user.display_name
            user_data['registration_number'] = user.fax_number
            user_data['student_id'] = user.id
            job_title = user.job_title
            user_data["position"] = job_title
            student_data.append(user_data)
        return student_data

    # Update student receives the property_name and its associated edited value and changes it. Update_student
    # modifies only the directory extension properties for security. For example, if you change the 'Name' property,
    # it will not automatically change the DisplayName property. The admin will have to change the display name in
    # the Azure portal. Similarly, if you change the 'Registration Number' property, it will not change the FaxNumber
    # property (to which registration numbers are mapped)

    # The interface for update student is a form. The form consists of the student properties for a particular
    # student and their current values. Each property is editable and when submitted, edits the value for that
    # property. Currently, this function(V1) can only receive the request body for one property edit at a time.

    async def update_student_v1(self, student_id, dir_property_name: str, property_value: str):
        student_dir_app = self.settings['stu_dir_app']
        request_body = User()
        additional_data = {f"{dir_property_name}": None}
        additional_data[f"{dir_property_name}"] = property_value
        request_body.additional_data = additional_data
        result = await self.app_client.users.by_user_id(student_id).patch(request_body)
        pass

    # student_extension_properties is a dictionary which maps every student property to its associated value for a
    # particular student. The student properties themselves are created from
    # institute.student_property_builder_flow. The student properties can be fetched as a list using
    # institute.fetch_extensions_student. Name and Registration Number are two mandatory properties to be present.

    # Practically, two interfaces must be offered to create a student. One is a form interface where the form keys
    # are obtained from institute.fetch_extensions_student and values manually provided and parsed by frontend which is
    # passed into the request body of student_creation_singular
    # Another is the option to download a template CSV (Using the same fetch function) and uploading the filled CSV
    # into the frontend, after which the frontend parses it and passes into the request body to bulk create(
    # student_creation_bulk)

    async def student_creation_singular(self, student_properties):
        app_id = self.settings['stu_dir_app']
        request_body = User()
        request_body.account_enabled = True
        display_name = student_properties[f'extension_{app_id}_student_name']
        mail = re.sub(' ','_',student_properties[f"extension_{app_id}_student_name"])
        password = helpers.password_generate_msft()
        request_body.display_name = display_name
        request_body.mail_nickname = re.sub(' ','_',student_properties[f"extension_{app_id}_student_name"])
        request_body.user_principal_name = mail
        request_body.mail = f"{mail}@v2tzs.onmicrosoft.com"
        request_body.job_title = student_properties[f"extension_{app_id}_position"]
        request_body.fax_number = student_properties[f'extension_{app_id}_student_registration_number']
        password_profile = PasswordProfile()
        password_profile.force_change_password_next_sign_in = True
        password_profile.password = password
        request_body.password_profile = password_profile
        additional_data = student_properties
        request_body.additional_data = additional_data
        print(request_body)
        result = await self.app_client.users.post(request_body)
        print(result)
        student_id = result.id
        password_properties = {
            "password": password,
            "mail": mail,
            "student_id": student_id
        }
        return password_properties

    async def student_creation_bulk(self, students_data):
        data_list = []
        for student in students_data:
            password, mail, student_id = await self.student_creation_singular(student)
            new_row = {"mail": mail, "passwords": password, "id": student_id}
            data_list.append(new_row)
        df_passwords = pd.DataFrame(data_list)
        passwords_json = df_passwords.to_json(orient='records')
        return passwords_json


    # getting singular students:When get_all_students is run it fetches the details of all students provisioned in Azure
    # AD. However, it only fetches some properties in this schema: (For Adele Vance and Aditya Kalpit example)
    # [{'Name': 'Adele Vance', 'Registration number': None, 'id': '46ee922b-d881-4128-8a37-f69e3dc45a08'},
    # {'Name': 'Aditya Kalpit', 'Registration number': None, 'id': '1cf0e9fc-9eca-4f49-803f-e5dabf1dd110'}]

    # When get_all_students is run, it only fetches some properties to reduce the search requirements for the
    # property data. Hence, the get_student_by_id method is used.

    # The get student_by_id method can directly fetch ALL properties for a particular student when run, by inputting
    # their id. However, this id is a random string generated when a student is created. Hence, there must first be a
    # one-one mapping to the id and some unique property in student data which can be user entered. The unique
    # properties chosen are DisplayName(Name), FaxNumber(Registration number) and Email(UserPrincipalName) Hence to
    # run get_student_by_name you would have to provide the display_name.

    # The main problem is figuring out the map between id and display_name. These are the current methods proposed:
    # 1.) Use OData filters. This eliminates the need for id and allows to directly find the student_data by the
    # property (Like DisplayName)
    # 3.) Fetch all student_data everytime the function is called and then search through the data for the
    # matching display_name
    # 4.) Fetch all student_data once in the session, cache it and pass it everytime necessary.

    # The 4th method is currently used. The frontend can fetch all student_data using get_all_students
    # one time in the session. The data which is fetched by get_all_students can only be modified in the azure
    # portal,not AMS (For security) and the id can never be modified. Hence, this data can safely be used anytime the
    # AMS requires data of a particular set of students

    async def get_student_by_id(self, id_num:str): 
        application_id = self.settings['stu_dir_app']
        application_id = application_id.strip()
        extension_request_body = get_available_extension_properties_post_request_body.GetAvailableExtensionPropertiesPostRequestBody()
        extension_request_body.is_synced_from_on_premises = False
        result = await self.app_client.directory_objects.get_available_extension_properties.post(
            extension_request_body)
        extension_property_names_with_app = []
        extension_property_names = []

        for value in result.value:
            if value.name[10:42] == re.sub("-", "", application_id):
                extension_property_names_with_app.append(value.name)
                extension_property_names.append(helpers.convert_key(value.name))
        query_params = UsersRequestBuilder.UsersRequestBuilderGetQueryParameters(
            select=['displayName', 'id', 'faxNumber'] + [str(value) for value in extension_property_names_with_app],
            # Sort by display name
            orderby=['displayName'],
        )
        request_config = UsersRequestBuilder.UsersRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        student = await self.app_client.users.by_user_id(id_num).get(request_config)
        student_data = {}
        student_data["name"] = student.display_name
        student_data["registration_number"] = student.fax_number
        student_data['id'] = student.id
        del student.additional_data["@odata.context"]
        student_data["properties"] = student.additional_data
        return student_data

    async def deregister_student(self, student_id):
        await self.app_client.users.by_user_id(student_id).delete()
        pass

    async def get_courses_of_student(self,student_id):
        course_ids = []
        result = await self.app_client.users.by_user_id(student_id).member_of.graph_group.get()
        for val in result.value:
            course_ids.append(val.id)
        return course_ids

