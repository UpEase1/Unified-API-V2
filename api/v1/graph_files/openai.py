from configparser import SectionProxy
from .singletons import CosmosServiceClientSingleton,AsyncAzureOpenAIClientSingleton
import json
import configparser
from ..graph_files.students import Students
from ..graph_files.courses import Courses
from ..graph_files.institute import Institute

config = configparser.ConfigParser()
config.read(['config.cfg', 'config.dev.cfg'])
azure_settings = config['azure']

students_instance = Students(azure_settings)
institute_instance = Institute(azure_settings)
courses_instance = Courses(azure_settings)

class OpenAI:
    settings: SectionProxy
    

    def __init__(self, config:SectionProxy):
        self.settings = config
        self.cosmos_client = CosmosServiceClientSingleton.get_instance()
        self.db = self.cosmos_client.get_database_client('courses_manipal')
        self.container = self.db.get_container_client('courses_manipal')
        self.app_client = AsyncAzureOpenAIClientSingleton.get_azure_openai_client()


    async def make_openai_call(self,query:str):
        max_completion_tokens = 2048
        first_system_prompt = """ If the query pertains to asking/analyzing for attendance of a particular student or a group of students then return 'send_all_student_details'. Example: "Query: Analyse the attendance of Raghav Mishra" Response: "send_all_student_details"
         If the query pertains to asking/analyzing for attendance of a group of students in a course, then return 'send_all_course_details'. Example: "Query: Analyse the attendance of Spacecraft Principles Course and Generic Aeronautical Course" Response from GPT should be only "send_all_course_details"
         Else, return 'unsupported request'"""
        second_system_prompt = """ If the query refers to a student name or a group of student names, and you are able to identify the students from the given data, provide the student IDs of those students mentioned in the query as a list object (With the brackets) from the data. Dont respond anything else at all except the list. Ignore anything else asked in the query and do not respond to that. Do not ask for any other information or provide additional details. Similarly, if the query pertains to a course or multiple courses and you can identify the courses from the data provided, then provide a list of only those course IDs as a list object (With the brackets) from the data. Dont respond anything else at all except the list.. """
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
        if "send_all_student_details" in first_response.choices[0].message.content:
            student_details = json.dumps(await students_instance.get_all_students())
            prompt = second_system_prompt + "\n" + query + student_details
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
                courses_object = await students_instance.get_courses_of_student(student_id = object)
                course_list = [course['course_id'] for course in courses_object]
                attendance_object = await courses_instance.get_student_attendance(student_id = object,course_ids =course_list)
                attendance_objects.append(attendance_object)
            prompt = third_system_prompt + "\n" + query + json.dumps(attendance_objects)
            third_response = await self.app_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model = "gpt-3.5-turbo",
            max_tokens=max_completion_tokens,
            temperature=0,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
            )
            return third_response.choices[0].message.content
        
        elif "send_all_course_details" in first_response.choices[0].message.content:
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
            attendance_objects = []
            for object in json.loads(second_response.choices[0].message.content):
                attendance_object = await courses_instance.get_course_attendance(course_id = object)
                attendance_objects.append(attendance_object)
            prompt = third_system_prompt + "\n" + query + json.dumps(attendance_objects)
            third_response = await self.app_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model = "gpt-3.5-turbo",
            max_tokens=max_completion_tokens,
            temperature=0,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
            )
            return third_response.choices[0].message.content
        else:
            return first_response.choices[0].message.content
            




