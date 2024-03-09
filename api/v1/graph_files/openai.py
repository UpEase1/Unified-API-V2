from configparser import SectionProxy
from .singletons import CosmosServiceClientSingleton,AsyncAzureOpenAIClientSingleton
import json
import configparser
from ..graph_files.students import Students
from ..graph_files.courses import Courses
from ..graph_files.institute import Institute
import re
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
        self.openai_client = AsyncAzureOpenAIClientSingleton.get_azure_openai_client()
    
    async def get_attendance_commentary(self, attendance):
        max_completion_tokens = 2048
        system_prompt = """ You will be given an attendance dataset. This dataset can either be relevant to a particular student (or set of students) or a particular course (or set of courses).
        You need to offer particular insights on the performance of the students/course based on this data. Here are some assumptions you have to make:
        Assume that the dataset is complete. Dont give a response like "I cannot comment due to the data being incomplete or not having a full range
        Assume that the dataset contains all enrolled students (In case of course related attendance data)
        Assume that the dataset is relevant to Indian attendance standards, where repeated truancy is considered a violation of rules, and less than 75 percent attendance can mean being detained
        in the course
        Assume that this data is the only factor relevant to the performance of the student or group of students
        Never use the words however, but or similar words which might lead to doubt in your response.
        Dont claim that any of your output is based on assumptions. These are hardcoded assumptions which are relevant always.
        
        You need to offer insights to answer the following questions?
        1) How is the student/students performing in the courses enrolled for each student asked
        
        format your response using markdown to look good with a single title header."""
        
        prompt = "START SYSTEM PROMPT" +  " " + system_prompt + " " + "END SYSTEM PROMPT AND START ATTENDANCE DATA" + " "+ str(attendance) + " " +  "ATTENDANCE DATA ENDED" +" "+  "Response: "
        print(system_prompt)
        response = await self.openai_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model = "gpt-3.5-turbo",
        max_tokens=max_completion_tokens,
        temperature=0,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
        )

        return response.choices[0].message.content
        
            




