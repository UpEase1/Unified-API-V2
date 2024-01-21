from configparser import SectionProxy
from azure.identity.aio import ClientSecretCredential
import re
import copy
from azure.cosmos import CosmosClient
import numpy as np
from msgraph import GraphServiceClient
from msgraph.generated.applications.get_available_extension_properties import \
    get_available_extension_properties_post_request_body
from msgraph.generated.models.extension_property import ExtensionProperty
from msgraph.generated.models.schema_extension import SchemaExtension

class Institute:
    settings: SectionProxy
    client_credential: ClientSecretCredential
    app_client: GraphServiceClient
    client:CosmosClient

    def __init__(self, config: SectionProxy):
        self.settings = config
        client_id = self.settings['clientId']
        tenant_id = self.settings['tenantId']
        client_secret = self.settings['clientSecret']
        scopes = ['https://graph.microsoft.com/.default']
        url = self.settings['YOUR_COSMOS_DB_URL']
        key = self.settings['YOUR_COSMOS_DB_KEY']
        self.client = CosmosClient(url,credential=key)
        self.db = self.client.get_database_client('courses_manipal')
        self.container = self.db.get_container_client('courses_manipal')
        self.client_credential = ClientSecretCredential(tenant_id, client_id, client_secret)
        self.app_client = GraphServiceClient(self.client_credential,scopes)

    async def fetch_extensions_student_graph(self):
        application_id = self.settings['stu_dir_app']
        def convert_key(key):
            sliced_key = key.split('_', 2)[-1]
            converted_key = re.sub(r'_', ' ', sliced_key)
            return converted_key
        extension_request_body = get_available_extension_properties_post_request_body.GetAvailableExtensionPropertiesPostRequestBody()
        extension_request_body.is_synced_from_on_premises = False
        result = await self.app_client.directory_objects.get_available_extension_properties.post(
            extension_request_body)
        extension_properties =[]
        for value in result.value:
            if value.name[10:42] == re.sub("-", "", application_id):
                extension_properties.append({"Name": convert_key(value.name), "ID": value.id, "data_type": value.data_type})
        return extension_properties
    
    async def fetch_extensions_student_manifest(self):
        query = """
            SELECT c.students.student_identifiers
            FROM c
            WHERE c.id = @tenant_id
        """
        parameters = [{"name": "@tenant_id", "value": self.settings['tenantId']}]
        query_result = list(self.container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))
        return query_result[0]["student_identifiers"]
        

    async def fetch_extensions_course_manifest(self):
        query = """
            SELECT c.courses.course_identifiers
            FROM c
            WHERE c.id = @tenant_id
        """
    
        # Setting the query parameters
        parameters = [{"name": "@tenant_id", "value": self.settings['tenantId']}]
        query_result = list(self.container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))
        return query_result[0]["course_identifiers"]

    async def fetch_extensions_course_graph(self):
        application_id = self.settings['course_dir_app']
        def convert_key(key):
            sliced_key = key.split('_', 2)[-1]
            converted_key = re.sub(r'_', ' ', sliced_key)
            return converted_key
        extension_request_body = get_available_extension_properties_post_request_body.GetAvailableExtensionPropertiesPostRequestBody()
        extension_request_body.is_synced_from_on_premises = False
        result = await self.app_client.directory_objects.get_available_extension_properties.post(
            extension_request_body)
        extension_properties =[]
        for value in result.value:
            if value.name[10:42] == re.sub("-", "", application_id):
                extension_properties.append({"Name": convert_key(value.name), "ID": value.id, "data_type": value.data_type})
        return extension_properties

    async def create_course_property(self,property_name):
        object_id = self.settings['course_dir_obj']
        request_body = ExtensionProperty()
        request_body.name = re.sub(r'\s', '_', property_name)
        request_body.data_type = 'String'
        request_body.target_objects = (['Group', ])
        result = await self.app_client.applications.by_application_id(object_id).extension_properties.post(
            request_body)
        pass

    async def create_student_property(self,property_name):
        object_id = self.settings['stu_dir_obj']
        request_body = ExtensionProperty()
        request_body.name = re.sub(r'\s', '_', property_name)
        request_body.data_type = 'String'
        request_body.target_objects = (['User', ])
        result = await self.app_client.applications.by_application_id(object_id).extension_properties.post(
            request_body)
        pass
    
    async def delete_student_properties(self,property_ids:list):
        obj_id = self.settings['stu_dir_obj']
        for property_id in property_ids:
            await self.app_client.applications.by_application_id(obj_id).extension_properties.by_extension_property_id(property_id).delete()

    async def delete_course_properties(self,property_ids:list):
        obj_id = self.settings['course_dir_obj']
        for property_id in property_ids:
            await self.app_client.applications.by_application_id(obj_id).extension_properties.by_extension_property_id(property_id).delete()
            
    async def institute_setup_runtime(self):
        manifest  = self.container.read_item(partition_key = self.settings['tenantId'], item = self.settings['tenantId'])
        course_obj_id = self.settings['course_dir_obj']
        stu_obj_id = self.settings['stu_dir_obj']
        rendered_manifest = copy.deepcopy(manifest)
    # Roles setup TODO
        # Render primary role definition
        if manifest['institute']['primary_role']['dir_ext_id'] is None:
            primary_role = manifest["institute"]["primary_role"]
            request_body = ExtensionProperty()
            request_body.name = re.sub(r'\s', '_', primary_role["name"])
            request_body.target_objects = (['User',])
            result = await self.app_client.applications.by_application_id(stu_obj_id).extension_properties.post(request_body)
            rendered_manifest["institute"]["primary_role"]["dir_ext_id"] = result.id
            rendered_manifest["institute"]["primary_role"]["dir_ext_name"] = result.name

        

    # Courses
        # Check if courses render was successful
        if manifest["courses"]["render_status"] == "complete":
            pass
        else:
        # Course property augmentation
            
            for course_identifier in rendered_manifest["courses"]["course_identifiers"]:
                if course_identifier["data_type"] in ["String", "enum", "struct"]:
                    data_type = 'String'
                elif course_identifier["data_type"] in ["Boolean", "DateTime", "Integer"]:
                    data_type = course_identifier['data_type']
                else:
                    data_type = 'String'
                request_body = ExtensionProperty()
                request_body.name = re.sub(r'\s', '_', course_identifier["name"])
                request_body.target_objects = (['Group', ])
                request_body.data_type = data_type
                result = await self.app_client.applications.by_application_id(course_obj_id).extension_properties.post(request_body)
                course_identifier["dir_ext_id"] = result.id
                course_identifier["dir_ext_name"] = result.name

            # Enum rendering
            rendered_manifest['courses']['course_identifiers'][4]['enum_vals'] = [dept['identifier'] for dept in manifest['Institute']['academic_department_definitions'] if 'identifier' in dept]
            rendered_manifest['courses']['course_identifiers'][7]['enum_vals'] = [dept['name'] for dept in manifest['Institute']['academic_department_definitions'] if 'name' in dept]
            rendered_manifest['courses']['course_identifiers'][8]['enum_vals'] = [program['name'] for department in manifest["Institute"]["academic_department_definitions"] for program in department["programs"]]
            rendered_manifest['courses']['course_identifiers'][10]['enum_vals'] = [course_type['name'] for course_type in manifest['Courses']['course_type_definitions'] if 'name' in course_type]
            rendered_manifest['courses']['render_status'] = 'complete'

        # Students
        # Check if courses render was successful
        if manifest["students"]["render_status"] == "complete":
            pass
        else:
        # Student property augmentation
            
            for student_identifier in rendered_manifest["students"]["student_identifiers"]:
                if student_identifier["data_type"] in ["String", "enum", "struct"]:
                    data_type = 'String'
                elif student_identifier["data_type"] in ["Boolean", "DateTime", "Integer"]:
                    data_type = student_identifier['data_type']
                else:
                    data_type = 'String'
                request_body = ExtensionProperty()
                request_body.name = re.sub(r'\s', '_', student_identifier["name"])
                request_body.target_objects = (['User', ])
                request_body.data_type = data_type
                result = await self.app_client.applications.by_application_id(stu_obj_id).extension_properties.post(request_body)
                student_identifier["dir_ext_id"] = result.id
                student_identifier["dir_ext_name"] = result.name

            # Enum rendering
            rendered_manifest['students']['student_identifiers'][1]['enum_vals'] = [dept['name'] for dept in manifest['institute']['academic_department_definitions'] if 'name' in dept]
            rendered_manifest['students']['student_identifiers'][0]['enum_vals'] = [program['name'] for department in manifest["institute"]["academic_department_definitions"] for program in department["programs"]]
            rendered_manifest['students']['render_status'] = 'complete'
        self.container.upsert_item(rendered_manifest)
        return rendered_manifest
    
            





    