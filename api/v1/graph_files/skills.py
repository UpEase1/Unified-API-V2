from semantic_kernel.plugin_definition import kernel_function            # Updated to semantic_kernel.functions import kernel_function in latest change (Not released yet)
from semantic_kernel.orchestration.kernel_context import KernelContext
from configparser import SectionProxy
from .singletons import AsyncAzureOpenAIClientSingleton
from ..graph_files.students import Students
from ..graph_files.courses import Courses
from ..graph_files.institute import Institute
import configparser
import json
from ..graph_files.openai import OpenAI
from fuzzywuzzy import process
import ast

from . import helpers
config = configparser.ConfigParser()
config.read(['config.cfg', 'config.dev.cfg'])
azure_settings = config['azure']
students_instance = Students(azure_settings)
institute_instance = Institute(azure_settings)
courses_instance = Courses(azure_settings)
openai_instance = OpenAI(azure_settings)

class StudentSkills:
    
    def __init__(self):
        self.openai_client = AsyncAzureOpenAIClientSingleton.get_azure_openai_client()

    @kernel_function(
            input_description = "Get all students of Institute",
            description = "Gets the names and unique object IDs of all the students in an Institute Do not use this function in a planner if a particular student name or a set of student names is provided. This function is only for all students",
            name = "GetAllStudents",
        )
    async def get_all_students(self) -> str:
        students = helpers.generate_md_table(await students_instance.get_all_students())
        return students
    @kernel_function(
        input_description = "count students",
        description = "Gets the number of students in the Institute. Do not use this function in a planner if a particular student name or a set of student names is provided. This function is only for all students",
        name = "GetAllStudentCount",
    )
    async def get_all_student_count(self) -> str:
        students = await students_instance.get_all_students()
        count = len(students)
        return f"There are {count} students in the Institute"
    
    
    @kernel_function(
            input_description = """unique student name extractor""",
            description = """Extracts the student names of the students as a list object from the provided query. Necessary if the query contains student names since only the full names can be used
            Any plans being made must use the student name extractor if the ask contains names of students/people. This must always be the first native function used by a planner if there are student names in the ask""",
            name = "UniqueStudentNameExtractor",
    )
    
    async def unique_student_name_extractor(self,query:str) -> str:
        max_completion_tokens = 2048
        system_prompt = f" Extract the names from the given query and output it as a list object. Example: END SYSTEM PROMPT AND START QUERY Get attendance of Karthik Prabhu and Lance Barreto QUERY ENDED Response: ['Karthik Prabhu','Lance Barreto']"
        prompt = "START SYSTEM PROMPT" +  " " + system_prompt + " " + "END SYSTEM PROMPT AND START QUERY" + " "+ query + " " +  "QUERY ENDED" +" "+ "Response: "
        response = await self.openai_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model = "gpt-3.5-turbo",
            max_tokens=max_completion_tokens,
            temperature=0,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
            )
        
        names = response.choices[0].message.content
        return names

    

    @kernel_function(
        input_description = """ Student Attendance insights generator""",
        description = """ Generates insights for the attendance of the list of students submitted to it. Here is what the planner must do. First, identify that the ask has an intent to collect attendance of students. Then, the planner must first use UniqueStudentNameExtractor to get the student name list. Then run StudentAttendanceInsightGenerator function for the insights""",
        name = "StudentAttendanceInsightGenerator",
    )
    async def student_attendance_insight_generator(self,name_list:str) -> str:
        # print(name_list)
        full_records = await students_instance.get_all_students()
        max_completion_tokens = 2048
        name_and_id_records = []
        for student in full_records:
            name_and_id_records.append({"name": student['name'], "student_id": student["student_id"]})
        # print(name_and_id_records)
        system_prompt = """ START SYSTEM PROMPT You will be given a list of names with variations. Use your intelligence to idenfity the unique records of the given names from the overall list.
            Example (Only for reference to understand the given schema):  START NAMES WITH VARIATIONS ['Karthik prabu','Lanc'] NAMES WITH VARIATIONS ENDED START OVERALL LIST [{
            "name": "Lance",
            "student_id": "6330af36-4e92-4436-a7f0-f5b7c3c27838"
        }, 
        {
            "name": "Karthik Prabhu",
            "student_id": "0358e62f-3a22-40b1-8e40-20862ec8a9bc"
        } ] END OVERALL LIST Response: [{"name": "Karthik Prabhu", "student_id": "0358e62f-3a22-40b1-8e40-20862ec8a9bc"},{"name": "Lance", "student_id":"6330af36-4e92-4436-a7f0-f5b7c3c27838" }]"""
        
        prompt = "START SYSTEM PROMPT" +  " " + str(system_prompt) + " " + " START NAMES WITH VARIATIONS" + " "+ str(name_list) + " " +  "NAMES WITH VARIATIONS ENDED" +" "+ "START OVERALL LIST" + " " + str(name_and_id_records) + " "+ "END OVERALL LIST Response: "
        response = await self.openai_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model = "gpt-3.5-turbo",
        max_tokens=max_completion_tokens,
        temperature=0,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
        )
        # print(f"the response is {response.choices[0].message.content}")
        matched_records = ast.literal_eval(response.choices[0].message.content)
        # print(f"The matched records are: {matched_records}")
        attendance_record = []
        for student in matched_records:
            course_records = await students_instance.get_courses_of_student(student["student_id"])
            course_ids = []
            for course_record in course_records:
                course_ids.append(course_record["course_id"])
            student_attendance = await courses_instance.get_student_attendance(student_id = student["student_id"], course_ids = course_ids)
            student_record = { 'student_name': student['name'], 'student_attendance': student_attendance}
            attendance_record.append(student_record)
        def generate_md_table(data:str):
            # Define the Markdown table header
            md_table = "Student Name | Course Name | Attendance Record | Attendance Percentage\n"
            md_table += "--- | --- | --- | ---\n"  # Table formatting for Markdown

            # Iterate through each student's data
            for student in data:
                student_name = student['student_name']
                for course in student['student_attendance']:
                    course_name = course['course_name']
                    attendance_percentage = course['attendance_percentage']
                    
                    # Format the attendance record as a string
                    attendance_record_str = ", ".join([f"{date}: {'Present' if status == 'P' else 'Absent'}" for date, status in course['attendance_record'].items()])
            
                    
                    # Append a new row to the Markdown table for each course
                    md_table += f"{student_name} | {course_name} | {attendance_record_str} | {attendance_percentage}%\n"

            return md_table

        return generate_md_table(data = attendance_record)

class CourseSkills:
    
    def __init__(self):
        self.openai_client = AsyncAzureOpenAIClientSingleton.get_azure_openai_client()

    @kernel_function(
        input_description = "Get all courses of Institute",
        description = "Gets the names and unique object IDs of all the courses in an Institute Do not use this function in a planner if a particular course name or a set of course names is provided. This function is only for all courses",
        name = "GetAllCourses",
    )
    async def get_all_courses(self) -> str:
        courses = helpers.generate_md_table(await courses_instance.get_all_courses())
        return courses
    @kernel_function(
        input_description = "count courses",
        description = "Gets the number of courses in the Institute. Do not use this function in a planner if a particular course name or a set of course names is provided. This function is only for all courses",
        name = "GetAllCourseCount",
    )
    async def get_all_course_count(self) -> str:
        courses = await courses_instance.get_all_courses()
        count = len(courses)
        return f"There are {count} courses in the Institute"
    
    @kernel_function(
            input_description = """unique course name extractor""",
            description = """Extracts the course names of the courses as a list object from the provided query. Necessary if the query contains course names since only the full names can be used
            Any plans being made must use the course name extractor if the ask contains names of students/people. This must always be the first native function used by a planner if there are course names in the ask""",
            name = "UniqueCourseNameExtractor",
    )

    async def unique_course_name_extractor(self,query:str) -> str:
        max_completion_tokens = 2048
        system_prompt = f" Extract the names from the given query and output it as a list object. Example: END SYSTEM PROMPT AND START QUERY Get attendance of Basic Reinforced Concrete Design and Aerospace Dynamics QUERY ENDED Response: ['Basic Reinforced Concrete Design', 'Aerospace']"
        prompt = "START SYSTEM PROMPT" +  " " + system_prompt + " " + "END SYSTEM PROMPT AND START QUERY" + " "+ query + " " +  "QUERY ENDED" +" "+ "Response: "
        response = await self.openai_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model = "gpt-3.5-turbo",
            max_tokens=max_completion_tokens,
            temperature=0,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
            )
        
        names = response.choices[0].message.content
        return names
    
    @kernel_function(
        input_description = """ Course Attendance insights generator""",
        description = """ Generates insights for the attendance of the list of courses submitted to it. Here is what the planner must do. First, identify that the ask has an intent to collect attendance of courses. Then, the planner must first use UniqueCourseNameExtractor to get the course name list. Then run CourseAttendanceInsightGenerator function for the insights""",
        name = "CourseAttendanceInsightGenerator",
    )
    async def course_attendance_insight_generator(self,name_list:str) -> str:
        # print(name_list)
        full_records = await courses_instance.get_all_courses()
        max_completion_tokens = 2048
        name_and_id_records = []
        for course in full_records:
            name_and_id_records.append({"name": course['name'], "course_id": course["id"]})
        # print(name_and_id_records)
        system_prompt = """ START SYSTEM PROMPT You will be given a list of names with variations. Use your intelligence to idenfity the unique records of the given names from the overall list.
            Example (Only for reference to understand the given schema):  START NAMES WITH VARIATIONS ['Basic Reinforced Design','Computr Network'] NAMES WITH VARIATIONS ENDED START OVERALL LIST [{
            "name": "Basic Reinforced Concrete Design",
            "course_id": "f600d310-2150-42d5-8ed9-a4cc5162fc47"
        }, 
        {
            "name": "Computer Networks",
            "course_id": "de895588-08d1-48aa-b2cd-8708679743c9"
        } ] END OVERALL LIST Response: [{
            "name": "Basic Reinforced Concrete Design",
            "course_id": "f600d310-2150-42d5-8ed9-a4cc5162fc47"
        }, 
        {
            "name": "Computer Networks",
            "course_id": "de895588-08d1-48aa-b2cd-8708679743c9"
        } ]"""
        
        prompt = "START SYSTEM PROMPT" +  " " + str(system_prompt) + " " + " START NAMES WITH VARIATIONS" + " "+ str(name_list) + " " +  "NAMES WITH VARIATIONS ENDED" +" "+ "START OVERALL LIST" + " " + str(name_and_id_records) + " "+ "END OVERALL LIST Response: "
        response = await self.openai_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model = "gpt-3.5-turbo",
        max_tokens=max_completion_tokens,
        temperature=0,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
        )
        # print(f"the response is {response.choices[0].message.content}")
        matched_records = ast.literal_eval(response.choices[0].message.content)
        # print(f"The matched records are: {matched_records}")
        attendance_record = []
        for course in matched_records:
            course_attendance = await courses_instance.get_course_attendance(course_id = course['course_id'])
            course_record = {'course_name': course['name'], 'course_attendance': course_attendance}
            attendance_record.append(course_record)
        # print(attendance_record)
        # return str(attendance_record)
        def generate_md_table(data):
            # Define the Markdown table header
            md_table = "Student Name | Course Name | Attendance Record | Attendance Percentage\n"
            md_table += "--- | --- | --- | ---\n"  # Table formatting for Markdown

            # Iterate through each course's data
            for course in data:
                course_name = course['course_name']
                # Iterate through each student's data in the course
                for student in course['course_attendance']:
                    student_name = student['student_name']
                    attendance_records = student['attendance_dates']

                    # Calculate attendance percentage
                    total_classes = len(attendance_records)
                    present_classes = sum(1 for record in attendance_records for date, status in record.items() if status == 'P')
                    attendance_percentage = (present_classes / total_classes) * 100

                    # Format the attendance record as a string
                    attendance_record_str = ", ".join([f"{list(record.keys())[0]}: {'Present' if list(record.values())[0] == 'P' else 'Absent'}" for record in attendance_records])
                    
                    # Append a new row to the Markdown table for each student in the course
                    md_table += f"{student_name} | {course_name} | {attendance_record_str} | {attendance_percentage:.2f}%\n"

            return md_table
        return generate_md_table(attendance_record)

# Assuming 'data' contains your attendance record schema as given
# print(generate_md_table(data))
