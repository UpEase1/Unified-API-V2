from configparser import SectionProxy
import pandas as pd
from typing import List
from typing import Dict
import re

from . import helpers
from .singletons import GraphServiceClientSingleton

from azure.identity.aio import ClientSecretCredential
from msgraph import GraphServiceClient,GraphRequestAdapter
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
        self.app_client = GraphServiceClientSingleton.get_instance()

    async def get_all_students(self) -> list:
        app_id_fetched = self.settings["stu_dir_app"] 
        app_id = re.sub(r'-','',app_id_fetched)
        query_params = UsersRequestBuilder.UsersRequestBuilderGetQueryParameters(
            select=['displayName', 'id', 'faxNumber','mail','jobTitle', 'extension_0a09fe4eefd047798b49f80aaaecb550_student_program'],
            orderby=['displayName'],
            filter = "jobTitle eq 'Student' and jobTitle eq 'student'",
            count = True
        )
        
        request_config = UsersRequestBuilder.UsersRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )
        request_config.headers.add("ConsistencyLevel", "eventual")
        student_data = []
        users = await self.app_client.users.get(request_configuration=request_config)
        for user in users.value:
            user_data = {}
            user_data['name'] = user.display_name
            user_data['registration_number'] = user.fax_number
            user_data['student_id'] = user.id
            user_data['mail'] = user.mail
            job_title = user.job_title
            user_data["position"] = job_title
            if user.additional_data:
                user_data["program"] = user.additional_data[f'extension_{app_id}_student_program']
            else:
                user_data['program'] = None
            student_data.append(user_data)
        return student_data

    async def update_student_v1(self, student_id, dir_property_name: str, property_value: str):
        student_dir_app = self.settings['stu_dir_app']
        request_body = User()
        additional_data = {f"{dir_property_name}": None}
        additional_data[f"{dir_property_name}"] = property_value
        request_body.additional_data = additional_data
        result = await self.app_client.users.by_user_id(student_id).patch(request_body)
        pass

    # We don't need to input extension_{app_id}_<property> since we 
    # are just using those keys as our own reference, and they are not 
    # passed on to the backend
    # ? why is registration number being passed
    # ! generate a registration number server side, not client side
    async def student_creation_singular(self, student_properties):
        app_id_fetched = self.settings['stu_dir_app']
        app_id = re.sub(r'-','',app_id_fetched)

        request_body = User()
        request_body.account_enabled = True
        
        display_name = student_properties[f'student_name']
        mail_name = re.sub(r' ', '',student_properties[f"student_name"])
        mail_domain = "@v2tzs.onmicrosoft.com"
        mail = mail_name + mail_domain
        
        request_body.display_name = display_name
        request_body.mail_nickname = mail_name
        request_body.user_principal_name = mail
        request_body.mail = mail
        request_body.employee_type = "Student"
        request_body.job_title = "Student"
        request_body.fax_number = str(student_properties['registration_number'])

        password = helpers.password_generate_msft()
        password_profile = PasswordProfile()
        password_profile.force_change_password_next_sign_in = True
        password_profile.password = password
        request_body.password_profile = password_profile

        mandatory_keys = [
            f"student_name",
            f"position",
            f"registration_number"
        ]
        
        # TODO all keys in additional data extension_{app_id}_<property> DONE

        additional_data = {f"extension_{app_id}_{k}": v for k, v in student_properties.items() if k not in mandatory_keys}
        request_body.additional_data = additional_data

        result = await self.app_client.users.post(request_body)
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
        courses = []
        result = await self.app_client.users.by_user_id(student_id).member_of.graph_group.get()
        for val in result.value:
            course = {"course_name": val.display_name, "course_id": val.id}
            courses.append(course)
        return courses




