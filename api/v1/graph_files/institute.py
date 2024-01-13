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


        #Institute data models: (Deprecated in favor of Institute manifest)

        # UpEase Console offers flexibility to institutes to create their own data definition model. However, the console
        # must provide recommendations to create this model to drive our end goal of creating a common data standard.

        # Course properties builder flow implements the customizable education model for courses in UpEase Console.
        # A course created in UpEase Console creates two resources, the first is an M365 Unified Group,
        # the second is a cosmosDB item representing that course.
        # Course creation best practices:
        #In order to distinguish between regular M365 Groups (Which can be created anywhere across the M365 experience),
        # A course will be tagged with the property "Type" which is equal to "Course". This is a hardcoded directory
        # extension property in the API. When an insitute is first set up to use UpEase Console, the course property
        #'Type' will be created.
        # Beyond this mandatory tag, other tags on courses can be chosen by the Institute flexibly. However, UpEase
        # Customer Success should recommend best practices to Institutes. These practices are:
            #Ensure that the course properties defined can uniquely identify a course offered to a particular cohort
            # For example, if the same course is offered in two different sections, but correspondence regarding the course,
            # Is seperate per section, then a tag called "Section" should be created, and two courses corresponding to each
            # section should be created. In other words, focus on as many distinguishing characteristics of courses as possible
            # when defining the course model.
            # Filterability should be kept in mind. When creating properties on the console, an option is provided to define
            # the property of enum type. This allows for filterability of courses.
            # For example, if the Institute has certain number of departments, defining the department property as enum and
            # defining the enum types should be done to prevent data validation issues.  As far as possible, course types
            # should be defined as enum type.
        

    # Fix: Assign numerals to each property so that it can be rendered in order in the UI
    async def fetch_extensions_student_manifest(self,manifest):
        #TODO
        pass
        

    async def fetch_extensions_course_manifest(self,manifest):
        #TODO
        pass

    async def fetch_extensions_student(self):
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
                extension_properties.append({"Name": convert_key(value.name), "ID": value.id})
        return extension_properties
    
    async def fetch_extensions_course(self):
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
                extension_properties.append({"Name": convert_key(value.name), "ID": value.id})
        return extension_properties
    
    async def delete_student_properties(self,property_ids:list):
        obj_id = self.settings['stu_dir_obj']
        for property_id in property_ids:
            await self.app_client.applications.by_application_id(obj_id).extension_properties.by_extension_property_id(property_id).delete()

    async def delete_course_properties(self,property_ids:list):
        obj_id = self.settings['course_dir_obj']
        for property_id in property_ids:
            await self.app_client.applications.by_application_id(obj_id).extension_properties.by_extension_property_id(property_id).delete()

# The institute setup runtime is a one-time operation in Copilot Build which sets up the Microsoft Institute manifest. 
# First, the Institute answers a questionnaire in Copilot Build which generates a form manifest.
# This form manifest is received and stored in the Cosmos container for that Institute. Its structure is predefined
# in the institute setup runtime. The runtime creates the necessary Microsoft objects and broad structures using
# the form manifest and generates a new manifest with the trace of the runtime output. This new manifest is then
# rendered in Copilot build and its trace is used to define the distinct data structure of various institutes.
# The institute manifest is the core of Console's flexibility and uses the CEDS data model as its basis with some
# tweaking for Indian context.

# Hence, a single application instance is enough for any number of institutes so long as the form manifest structure
# is same across all of them.
            
    async def institute_setup_runtime(self, manifest):
        course_obj_id = self.settings['course_dir_obj']
        stu_obj_id = self.settings['stu_dir_obj']
        rendered_manifest = copy.deepcopy(manifest)
    # Roles setup TODO
        # Render primary role definition
        primary_role = manifest["Institute"]["primary_role"]
        request_body = ExtensionProperty()
        request_body.name = re.sub(r'\s', '_', primary_role["name"])
        request_body.target_objects = (['User',])
        result = await self.app_client.applications.by_application_id(stu_obj_id).extension_properties.post(request_body)
        rendered_manifest["Institute"]["primary_role"]["dir_ext_id"] = result.id
        rendered_manifest["Institute"]["primary_role"]["dir_ext_name"] = result.name

        

    # Courses
        # Check if courses render was successful
        if manifest["Courses"]["render_status"] == "complete":
            pass
        else:
        # Course property augmentation
            
            for course_identifier in rendered_manifest["Courses"]["course_identifiers"]:
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
            rendered_manifest['Courses']['course_identifiers'][4]['enum_vals'] = [dept['identifier'] for dept in manifest['Institute']['academic_department_definitions'] if 'identifier' in dept]
            rendered_manifest['Courses']['course_identifiers'][7]['enum_vals'] = [dept['name'] for dept in manifest['Institute']['academic_department_definitions'] if 'name' in dept]
            rendered_manifest['Courses']['course_identifiers'][8]['enum_vals'] = [program['name'] for department in manifest["Institute"]["academic_department_definitions"] for program in department["programs"]]
            rendered_manifest['Courses']['course_identifiers'][10]['enum_vals'] = [course_type['name'] for course_type in manifest['Courses']['course_type_definitions'] if 'name' in course_type]
            rendered_manifest['Courses']['render_status'] = 'complete'

        # Students
        
        return rendered_manifest
    
            





    