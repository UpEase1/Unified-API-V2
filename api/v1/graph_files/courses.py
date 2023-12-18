import configparser
from configparser import SectionProxy
import re

from .institute import Institute
from .students import Students
from . import helpers

from azure.identity.aio import ClientSecretCredential
from kiota_authentication_azure.azure_identity_authentication_provider import (
    AzureIdentityAuthenticationProvider
)
from msgraph import GraphRequestAdapter, GraphServiceClient
from msgraph.generated.applications.get_available_extension_properties import \
    get_available_extension_properties_post_request_body
from msgraph.generated.groups.groups_request_builder import GroupsRequestBuilder
from msgraph.generated.models.group import Group
from msgraph.generated.models.reference_create import ReferenceCreate
from msgraph.generated.users.users_request_builder import UsersRequestBuilder
from azure.cosmos import CosmosClient

config = configparser.ConfigParser()
config.read(['config.cfg', 'config.dev.cfg'])
azure_settings = config['azure']

students_instance = Students(azure_settings)
institute_instance = Institute(azure_settings)

class Courses:
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

    async def get_all_courses(self):
        query_params = GroupsRequestBuilder.GroupsRequestBuilderGetQueryParameters(
            select=['displayName', 'id'],
            orderby=['displayName']
        )
        request_config = GroupsRequestBuilder.GroupsRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        groups = await self.app_client.groups.get(request_configuration=request_config)
        courses = []
        for group in groups.value:
            course_data = {}
            course_data['name'] = group.display_name
            course_data['id'] = group.id
            courses.append(course_data)
        return courses
        
    async def get_course_by_id(self,course_id):      #TODO Show students enrolled in the course.
        application_id = self.settings['course_dir_app']
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
        query_params = GroupsRequestBuilder.GroupsRequestBuilderGetQueryParameters(
            select=['displayName', 'id'] + [str(value) for value in extension_property_names_with_app],
            # Sort by display name
            orderby=['displayName'],
        )
        request_config = GroupsRequestBuilder.GroupsRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        course = await self.app_client.groups.by_group_id(course_id).get(request_config)
        member_query_params = UsersRequestBuilder.UsersRequestBuilderGetQueryParameters(
            select = ['displayName','id'],

        )
        member_request_config = UsersRequestBuilder.UsersRequestBuilderGetRequestConfiguration(query_parameters=member_query_params,headers = {
		'ConsistencyLevel' : "eventual",
})

        members = await self.app_client.groups.by_group_id(course_id).members.get(request_configuration=member_request_config)
        #del members["@odata.context"]
        course_data = {}
        course_data["Name"] = course.display_name
        course_data['id'] = course.id
        course_data["properties"] = course.additional_data
        course_data["members"] = members.value
        return course_data

    # When a course is created, the course_details parameter is expected. 
    # This course_details parameter has a dynamic schema which is dependent on the course_extension_properties
    # chosen by the institute.
    async def create_course(self, course_details):
        app_id = self.settings['course_dir_app']
        course_name = course_details['Name']
        course_properties = course_details["Properties"]
        course_details['Properties']['Type']=course_type
        course_type = 'Course'
        request_body = Group()
        request_body.display_name = course_name
        request_body.mail_enabled = True
        request_body.mail_nickname = re.sub(' ','_',course_details['Name'])
        request_body.security_enabled = False
        request_body.group_types = ["Unified",]
        request_body.description = course_details['Description']
        def transform_key(key):
            return f"extension_{re.sub('-', '', app_id)}_{re.sub(' ', '_', key)}"

        replace_keys = lambda obj: {transform_key(k): replace_keys(v) if isinstance(v, dict) else v for k, v in
                                    obj.items()}
        additional_data = replace_keys(course_properties)
        request_body.additional_data = additional_data
        result = await self.app_client.groups.post(request_body)
        course_id = result.id
        course_properties['Mail'] = result.mail
        course_properties['SecurityEnabled'] = result.security_enabled
        print("Creation of the group in Azure AD was successful")
        def create_course_document(self,course_name):
            course_data = {'id': course_id,  # using course name (In graph) as unique id
                'courses_manipal': course_id,
                'Name':course_name,
                'students':[],
                'properties': course_properties,
                }


            self.container.create_item(course_data)
        create_course_document(self,course_name=course_name)
        print("Creation of the course in cosmos was successful")
        return course_id
    
    # async def add_students_to_course_v2(self,upsert_data):
    #     course_id = upsert_data['Course ID']
    #     course_name = upsert_data['Course Name']
    #     def add_student_to_course_document(self,course_id,course_name, student_name,registration_number):
    #         course_data_cosmos = self.container.read_item(item=course_id,partition_key = course_name)
    #         student_data = {
    #             'Registration number': registration_number,
    #             'student_name': student_name,
    #             'attendance_dates': [],
    #             'assignments': []
    #         }
    #         course_data_cosmos['students'].append(student_data)
    #         self.container.upsert_item(course_data_cosmos)
    #     for student in upsert_data['Students']:
    #         request_body = ReferenceCreate()
    #         student_name = student['Name']
    #         registration_number = student['Registration number']
    #         request_body.odata_id = f"https://graph.microsoft.com//v1.0//directoryObjects//{student['id']}"
    #         await self.app_client.groups.by_group_id(course_id).members.ref.post(request_body)
    #         add_student_to_course_document(self,course_id=course_id,student_name=student_name,registration_number=registration_number,course_name = course_name)


    # When a student is added to a course, it adds the student (Represented by the id) to an M365 group instance
    # representing the course. It also adds the student to a cosmos DB item representing the course.

    async def add_students_to_course(self,student_ids:list,course_id:str,students:Students):

        def add_student_to_course_document(self,course_id, student_name,registration_number,student_id):
            course_data_cosmos = self.container.read_item(partition_key = course_id, item = course_id)
            student_data = {
                'student_id' : student_id,
                'registration_number': registration_number,
                'student_name': student_name,
                'attendance_dates': [],
                'assignments': []
            }
            course_data_cosmos['students'].append(student_data)
            self.container.upsert_item(course_data_cosmos)


        for student_id in student_ids:
            request_body = ReferenceCreate()
            data = await students.get_student_by_id(id_num=student_id)
            student_name = data['Name']
            registration_number = data['Registration number']
            request_body.odata_id = f"https://graph.microsoft.com//v1.0//directoryObjects//{student_id}"
            await self.app_client.groups.by_group_id(course_id).members.ref.post(request_body)
            add_student_to_course_document(self,course_id=course_id,student_name=student_name,registration_number=registration_number,student_id = student_id)

    # When a student is added to a course in Console, the student is added
    # to an M365 group representing that course as well as a CosmosDB item representing the course.
    # However, when a student is removed, in order to preserve attendance data for training purposes,
    # the student will not be removed from the cosmos document. This also ensures that accidental removal can be reversed.
    # If a student is removed from a course in teams, azure portal or Console, the outcome remains same.
    # Since CosmosDB is a natural extension of MSGraph, the student who is removed from a course will not be
    # able to see his attendance for that course, even if his entry is still present in CosmosDB. However, the
    # teacher who updates attendance for that course will still be able to see his enrollment for that course.
    # The teacher may simply ignore that enrollment and not update attendance in the JavaScript Add-in.
    # Removal of a student from the course can be reversed without any high level consequences.
    async def remove_student_from_course(self, student_id,course_id):
        await self.app_client.groups.by_group_id(course_id).members.by_directory_object_id(student_id).ref.delete()

    async def update_course_by_id(self, course_id, property_name: str, property_value: str):
        course_dir_app = self.settings['course_dir_app']
        dir_property = f"extension_{re.sub('-', '', course_dir_app)}_" + property_name.replace(" ", "_")
        request_body = Group()
        additional_data = {f"{dir_property}": None}
        additional_data[f"{dir_property}"] = property_value
        request_body.additional_data = additional_data
        # Add cosmos db level update request
        result = await self.app_client.groups.by_group_id(course_id).patch(request_body)
        pass

    # Retire course will only remove the course from all Microsoft integrations. It will not remove the course from
    #the cosmos DB instance. Once a course is retired, it cannot be reversed as the course_id will change.
    # The course item along with the student enrolment details will still be available in Cosmos for training purposes.
    async def retire_course_by_id(self,course_id:str):
        await self.app_client.groups.by_group_id(course_id).delete()


    # Gets students of a course. However, currently it will fetch all members of the M365 group representing the course.
    # To filter for students, we can implement EDU model and run a filter against the ids returned. However, currently
    # We dont have access to the EDU model.
    async def get_students_of_course(self,course_id:str):     #Issue
        student_info = []
        result = await self.app_client.groups.by_group_id(course_id).members.get()
        for value in result.value:
            student_data = { "id": value.id, "name": value.display_name, "mail": value.mail}
            student_info.append(student_data)
        return student_info
    
    # student_attendance_list_schema = [{
    #  "Registration Number": int, attendance_list: [
    # 02-10-2023: "P"]}]
    async def add_attendance_to_course_student(self,course_id:str, student_id:str, attendance_list:list):
        data = self.container.read_item(item=course_id, partition_key=course_id)

    # Find the student with the given registration number
        for student in data['students']:
            if student['student_id'] == student_id:
                
                # Initialize attendance_dates if it doesn't exist
                if 'attendance_dates' not in student:
                    student['attendance_dates'] = []
                
                # Check for duplicate attendance date
                for attendance in student['attendance_dates']:
                    if list(attendance_list.keys())[0] in attendance:
                        return
                
                # Update attendance
                student['attendance_dates'].append(attendance_list)
                break
        else:
            return

        # Upsert the item
        self.container.upsert_item(body=data)
    
    async def add_faculty_to_course(self,course_id,faculty_id):
        pass

    async def get_student_attendance(self, student_id: str, course_ids: list):
        attendance_data = []

        # Original query without filtering for specific student
        query = """
        SELECT c.id, c.students 
        FROM c 
        WHERE ARRAY_CONTAINS(@course_ids, c.id)
        """

        # Execute the query and fetch results
        course_items = list(self.container.query_items(
            query=query, 
            parameters=[
                {'name': '@course_ids', 'value': course_ids}
            ],
            enable_cross_partition_query=True
        ))

        for course_item in course_items:
            student_data = next((student for student in course_item['students'] if student['student_id'] == student_id), None)
            
            if student_data:
                course_data = {"course_id": course_item['id']}

                # Improved handling of attendance data
                if 'attendance_dates' in student_data:
                    course_attendance = {}
                    for attendance_record in student_data['attendance_dates']:
                        course_attendance.update(attendance_record)

                    total_days = len(course_attendance)
                    total_present = sum(status == "P" for status in course_attendance.values())

                    attendance_percentage = (total_present / total_days) * 100 if total_days > 0 else 0

                    course_data["attendance_record"] = course_attendance
                    course_data["attendance_percentage"] = attendance_percentage
                else:
                    course_data["attendance_record"] = {}
                    course_data["attendance_percentage"] = 0

                attendance_data.append(course_data)

        return attendance_data



