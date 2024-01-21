from configparser import SectionProxy
from openai import AsyncAzureOpenAI
from azure.cosmos import CosmosClient
import json
import configparser
from ..graph_files.students import Students
from ..graph_files.courses import Courses
from ..graph_files.institute import Institute
from ..graph_files.config import create_cosmos_service_client,create_graph_service_client

config = configparser.ConfigParser()
config.read(['config.cfg', 'config.dev.cfg'])
azure_settings = config['azure']

students_instance = Students(azure_settings)
institute_instance = Institute(azure_settings)
courses_instance = Courses(azure_settings)

class OpenAI:
    settings: SectionProxy
    app_client: AsyncAzureOpenAI
    cosmos_client:CosmosClient
    

    def __init__(self, config:SectionProxy):
        self.settings = config
        api_key = self.settings["openai_api_key"]
        api_base = self.settings["openai_api_base"]
        api_version = self.settings["openai_api_version"]
        self.app_client = AsyncAzureOpenAI(api_key = api_key, api_version = api_version, azure_endpoint=api_base,azure_deployment = 'UpEase-testing' )
        self.cosmos_client = create_cosmos_service_client(config)
        self.graph_client = create_graph_service_client(config)
        self.db = self.cosmos_client.get_database_client('courses_manipal')
        self.container = self.db.get_container_client('courses_manipal')


    async def make_openai_call(self,query:str):
        max_completion_tokens = 2048
        first_system_prompt = """ If the query pertains to asking for attendance of a particular student or a group of students then return 'send_all_student_details'.
         If the query pertains to asking for attendance of a group of students in a course, then return 'send_all_course_details'.
         Else, return 'unsupported request'"""
        second_system_prompt = """ If the query refers to a student name or a group of student names, and you are able to identify the students from the given data, provide the student IDs of those students mentioned in the query as a list object (With the brackets) from the data. Dont respond anything else at all except the list. Ignore anything else asked in the query and do not respond to that. Do not ask for any other information or provide additional details. Similarly, if the query pertains to a course or multiple courses and you can identify the courses from the data provided, then provide a list of only those course IDs and nothing else. """
        third_system_prompt = """ Respond to the query as requested using the data provided to your best ability. If you see attendance data(Like attendance record), assume it is relevant to the requested student/course"""
        prompt = first_system_prompt+ "\n" + query
        first_response = await self.app_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model = "gpt-3.5-turbo",
            max_tokens=max_completion_tokens,
            temperature=0,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
            )
        if first_response.choices[0].message.content == 'send_all_student_details':
            student_details = json.dumps(await students_instance.get_all_students())
            prompt = second_system_prompt + "\n" + query + student_details
            print(prompt)
            second_response = await self.app_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model = "gpt-3.5-turbo",
            max_tokens=max_completion_tokens,
            temperature=0,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
            )
            attendance_objects = []
            for object in json.loads(second_response.choices[0].message.content):
                print(object)
                courses_object = await students_instance.get_courses_of_student(student_id = object)
                course_list = [course['course_id'] for course in courses_object]
                attendance_object = await courses_instance.get_student_attendance(student_id = object,course_ids =course_list)
                attendance_objects.append(attendance_object)
            print(attendance_objects)
            prompt = third_system_prompt + "\n" + query + json.dumps(attendance_objects)
            print(prompt)
            third_response = await self.app_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model = "gpt-3.5-turbo",
            max_tokens=max_completion_tokens,
            temperature=0,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
            )
            return third_response
        
        elif first_response.choices[0].message.content == 'send_all_course_details':
            course_details = json.dumps(await courses_instance.get_all_courses())
            prompt = second_system_prompt + "\n" + query + "start_course_details" + course_details + "end_course_details"
            second_response = await self.app_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model = "gpt-3.5-turbo",
            max_tokens=max_completion_tokens,
            temperature=0,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
            )
            return second_response
        else:
            return first_response
            




