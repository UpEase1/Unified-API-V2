
from configparser import SectionProxy
import re
from .singletons import GraphServiceClientSingleton, CosmosServiceClientSingleton
from .students import Students
from . import helpers

from msgraph import  GraphServiceClient
from msgraph.generated.applications.get_available_extension_properties import \
    get_available_extension_properties_post_request_body
from msgraph.generated.groups.groups_request_builder import GroupsRequestBuilder
from msgraph.generated.models.group import Group
from msgraph.generated.models.reference_create import ReferenceCreate
from msgraph.generated.users.users_request_builder import UsersRequestBuilder
from azure.cosmos import CosmosClient

class Courses:
    settings: SectionProxy
    app_client:GraphServiceClient


    def __init__(self, config: SectionProxy):
        self.settings = config 
        self.app_client = GraphServiceClientSingleton.get_instance()
        self.cosmos_client = CosmosServiceClientSingleton.get_instance()
        self.db = self.cosmos_client.get_database_client('courses_manipal')
        self.container = self.db.get_container_client('courses_manipal')

    async def get_all_courses(self):
        query_params = GroupsRequestBuilder.GroupsRequestBuilderGetQueryParameters(
            select=['displayName', 'id', 'mail'],
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
            course_data['mail'] = group.mail
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
        # member_query_params = UsersRequestBuilder.UsersRequestBuilderGetQueryParameters(
        #     select = ['displayName','id'],

        # )
        # member_request_config = UsersRequestBuilder.UsersRequestBuilderGetRequestConfiguration(query_parameters=member_query_params,headers = {
		# 'ConsistencyLevel' : "eventual",
        # })

        # members = await self.client.app_client.groups.by_group_id(course_id).members.get(request_configuration=member_request_config)
        #del members["@odata.context"]
        course_data = {}
        course_data["name"] = course.display_name
        course_data['course_id'] = course.id
        course_data["properties"] = course.additional_data
        # course_data["members"] = members.value                            # Issue: Member implementation in new library. Issue code commented out.
        return course_data

    # When a course is created, the course_details parameter is expected. 
    # This course_details parameter has a dynamic schema which is dependent on the course_extension_properties
    # chosen by the institute.
    async def create_course(self, course_properties):
        app_id_fetched = self.settings['course_dir_app']
        app_id = re.sub(r'-','',app_id_fetched)
        course_name = course_properties['course_name']
        request_body = Group()
        request_body.display_name = course_name
        request_body.mail_enabled = True
        request_body.mail_nickname = re.sub(' ','_',course_properties['course_name'])
        request_body.security_enabled = False
        request_body.group_types = ["Unified",]
        request_body.description = course_properties["course_description"]
        mandatory_keys = ["course_name","course_type","course_description"]
        additional_data = {f"extension_{app_id}_{k}": v for k, v in course_properties.items() if k not in mandatory_keys}
        request_body.additional_data = additional_data
        result = await self.app_client.groups.post(request_body)
        course_id = result.id
        course_properties['mail'] = result.mail
        course_properties['security_enabled'] = result.security_enabled
        print("Creation of the group in Azure AD was successful")
        def create_course_document(self,course_name):
            course_data = {'id': course_id,  # using course name (In graph) as unique id
                'courses_manipal': course_id,
                'name':course_name,
                'students':[],
                'properties': course_properties,
                }


            self.container.create_item(course_data)
        create_course_document(self,course_name=course_name)
        print("Creation of the course in cosmos was successful")
        return {
            "course_name": course_name,
            "course_id": course_id
        }

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
    #         await self.client.app_client.groups.by_group_id(course_id).members.ref.post(request_body)
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
            student_name = data['name']
            registration_number = data['registration_number']
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

    async def update_course_by_id(self, course_id, dir_property_name: str, property_value: str):
        course_dir_app = self.settings['course_dir_app']
        request_body = Group()
        additional_data = {f"{dir_property_name}": None}
        additional_data[f"{dir_property_name}"] = property_value
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
    async def get_students_of_course(self,course_id:str): 
        query_params = UsersRequestBuilder.UsersRequestBuilderGetQueryParameters(
            select=['displayName', 'id', 'faxNumber', 'mail'],
            orderby=['displayName']
        )
        request_config = UsersRequestBuilder.UsersRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )
        request_config.headers.add("ConsistencyLevel", "eventual")
        student_info = []
        result = await self.app_client.groups.by_group_id(course_id).members.graph_user.get(request_config)
        for value in result.value:
            student_data = { "id": value.id, "name": value.display_name, "mail": value.mail, "registration_number": value.fax_number}
            student_info.append(student_data)
        return student_info
    
    # student_attendance_list_schema = [{
    #  "Registration Number": int, attendance_list: [
    # 02-10-2023: "P"]}]
    async def add_attendance_to_course_students(self,course_id:str,new_attendance_data):
        data = self.container.read_item(item=course_id, partition_key=course_id)
    # Iterate through each student in the item's student list
        for student in new_attendance_data:
            # Find the matching student in the course item
            course_student = next((s for s in data['students'] if s['student_id'] == student['id']), None)
            if course_student:
                # Add new attendance dates without duplicating
                existing_dates = set()
                for attendance in course_student['attendance_dates']:
                    for date in attendance:
                        print(date)
                        existing_dates.add(str(date))  # Add only the date key, which is a string

                for new_attendance in student['attendance_dates']:
                    for date, status in new_attendance.items():
                        print(date)
                        if date not in existing_dates:
                            course_student['attendance_dates'].append({date: status})
                            existing_dates.add(str(date))
        self.container.replace_item(course_id, data)
    
    async def add_faculty_to_course(self,course_id,faculty_id):
        pass
    async def add_assignment_to_course(self, course_id: str, assignments:list):
        data = self.container.read_item(item=course_id, partition_key=course_id)
        
        # Iterate through each assignment in the assignments list
        for assignment in assignments:
            # Find the matching student in the course item
            course_student = next((s for s in data['students'] if s['student_id'] == assignment['student_id']), None)
            if course_student:
                # Check if 'assignments' key exists for the student, if not, create it
                if 'assignments' not in course_student:
                    course_student['assignments'] = []

                # Check if the assignment already exists for the student
                existing_assignment = next((a for a in course_student['assignments'] if a['name'] == assignment['name']), None)

                if existing_assignment:
                    # Update existing assignment scores
                    existing_assignment['score'] = assignment['score']
                    existing_assignment['max'] = assignment['max']
                else:
                    # Add new assignment
                    course_student['assignments'].append({
                        'name': assignment['name'],
                        'score': assignment['score'],
                        'max': assignment['max']
                    })

        self.container.replace_item(course_id, data)


    async def get_student_attendance(self, student_id: str, course_ids: list):
        attendance_data = []

        # Original query without filtering for specific student
        query = """
        SELECT c.id, c.students ,c.name
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
                course_data = {"course_id": course_item['id'],"course_name":course_item['name']}

                # Improved handling of attendance data
                if 'attendance_dates' in student_data:
                    course_attendance = {}
                    for attendance_record in student_data['attendance_dates']:
                        course_attendance.update(attendance_record)

                    total_days = len(course_attendance)
                    total_present = sum(status == "P" for status in course_attendance.values())

                    attendance_percentage = (total_present / total_days) * 100 if total_days > 0 else 0

                    course_data["attendance_record"] = course_attendance
                    course_data["attendance_percentage"] = round(attendance_percentage)
                else:
                    course_data["attendance_record"] = {}
                    course_data["attendance_percentage"] = 0

                attendance_data.append(course_data)

        return attendance_data

    async def get_course_attendance(self,course_id):
        course_data = self.container.read_item(item=course_id, partition_key=course_id)
        attendance_data = []
        for student in course_data['students']:
            student_attendance = {"student_name": student['student_name'], "student_id":student["student_id"],"attendance_dates":student["attendance_dates"]}
            attendance_data.append(student_attendance)
        return attendance_data

