from configparser import SectionProxy
from azure.identity.aio import ClientSecretCredential
import re
from azure.cosmos import CosmosClient
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


        #Institute data models:

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

    async def course_properties_builder_flow(self,schema:list):
        object_id = self.settings['course_dir_obj']
        for property_name in schema:
            request_body = ExtensionProperty()
            request_body.name = re.sub(r'\s', '_', property_name)
            request_body.data_type = 'String'
            request_body.target_objects = (['Group', ])
            result = await self.app_client.applications.by_application_id(object_id).extension_properties.post(
                request_body)
        pass
    async def student_properties_builder_flow(self,schema:list):
        object_id = self.settings['stu_dir_obj']
        for property_name in schema:
            request_body = ExtensionProperty()
            request_body.name = re.sub(r'\s', '_', property_name)
            request_body.data_type = 'String'
            request_body.target_objects = (['User', ])
            result = await self.app_client.applications.by_application_id(object_id).extension_properties.post(
                request_body)
        pass
    # Fix: Assign numerals to each property so that it can be rendered in order in the UI
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
    
    async def delete_student_properties(self,properties):
        obj_id = self.settings['stu_dir_obj']
        for property in properties:
            await self.app_client.applications.by_application_id(obj_id).extension_properties.by_extension_property_id(property['ID']).delete()

    async def delete_course_properties(self,properties:list):
        obj_id = self.settings['course_dir_obj']
        for property in properties:
            await self.app_client.applications.by_application_id(obj_id).extension_properties.by_extension_property_id(property).delete()
 
    async def create_enum_extension(self,institute_name:str,institute_id:str):
        request_body = SchemaExtension()
        request_body.id = f"enums_{institute_name}"
        request_body.description = f"enum type definitions for {institute_name}"
        request_body.target_types = ["Organization",]
        request_body.properties = []
        result = await self.app_client.schema_extensions.post(request_body)
        enum_id = result.id
        institute_data_cosmos = self.container.read_item(partition_key = institute_id, item = institute_id)
        enum_extension_data = {
            "Name": f"enums_{institute_name}",
            "identifier": "enum_extension",
            "id" : enum_id
        }
        institute_data_cosmos['enum_definition'].append(enum_extension_data)
        self.container.upsert_item(institute_data_cosmos)
        pass



        pass
    async def institute_enums(self,enum_name,enums:list):
        pass

    async def create_institution_extension_document(self,institute_name:str):
        details = await self.app_client.organization.get()
        for val in details.value:
            institute_id = val.id
        def create_institute_document(self,institute_name,institute_id):
            institute_data = {'id': institute_id,  # using course name (In graph) as unique id
                'courses_manipal': institute_id,
                'Name':institute_name,
                }


            self.container.create_item(institute_data)
        create_institute_document(self,institute_id=institute_id,institute_name=institute_name)


    # async def student_properties_builder_flow_enum_type(self,schema):
    #     object_id = self.settings['stu_dir_obj']
    #     openextensionregistryid = "e911f6e2-2827-4293-9a28-8b3aef5363d0"
    #     for property in schema:
    #         request_body = ExtensionProperty()
    #         request_body.name = re.sub(r'\s', '_', property["Name"])
    #         request_body.data_type = 'String'
    #         request_body.target_objects = (['User', ])
    #         result = await self.app_client.applications.by_application_id(object_id).extension_properties.post(
    #             request_body)
    #         property['ID'] = result.id
    #         request_body_enum = OpenTypeExtension()
    #         request_body_enum.odata_type ="#microsoft.graph.openTypeExtension"
    #         request_body_enum.extension_name = f"enum_{property['ID']}_Name"
    #         request_body_enum.id = f"enum_{property['ID']}_ID"
    #         enum_properties_dict = {item:item for item in property["Enums"]}
    #         request_body_enum.additional_data = enum_properties_dict
    #         result_enums = await self.app_client.users.by_user_id(openextensionregistryid).extensions.post(request_body_enum)
    #         pass

    async def create_roles(roles:list):
        #TODO
        pass

    async def assign_roles(roles:list, user_id:str):
        #TODO
        pass

    async def delete_roles(roles:list):
        #TODO
        pass

    async def get_roles():
        pass
    # Announcements

    # Announcements across an organization are simulated by this methodology:
    # A private SharePoint list with the end extension "Announcements_UpEase" is created when enable_announcements
    # is called in the root site of the tenant. The list has the fields "Title", "Description" and "File upload"
    async def enable_announcements():

        pass