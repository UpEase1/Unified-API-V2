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


    async def match_student_records(self,names_with_variations, full_records):
        max_completion_tokens = 2048
        name_and_id_records = []
        for student in full_records:
            name_and_id_records.append({"name": student['name'], "student_id": student["id"]})
        system_prompt = """ You will be given a list of names with variations. Use your intelligence to idenfity the unique IDs of the given names from the overall list.
            Example: END SYSTEM PROMPT AND START NAMES WITH VARIATIONS ['Karthik prabu','Lanc'] NAMES WITH VARIATIONS ENDED START OVERALL LIST [{
            "name": "Lance",
            "registration_number": "210914049",
            "student_id": "6330af36-4e92-4436-a7f0-f5b7c3c27838",
            "mail": "Lance@v2tzs.onmicrosoft.com",
            "position": "Student",
            "program": "None"
        }, 
        {
            "name": "Karthik Prabhu",
            "registration_number": "210904048",
            "student_id": "0358e62f-3a22-40b1-8e40-20862ec8a9bc",
            "mail": "KarthikPrabhu@v2tzs.onmicrosoft.com",
            "position": "Student",
            "program": "Civil"
        } ] END OVERALL LIST Response: [{"name": "Karthik Prabhu", "student_id": "0358e62f-3a22-40b1-8e40-20862ec8a9bc"},{"name": "Lance", "student_id":"6330af36-4e92-4436-a7f0-f5b7c3c27838" }]"""
        
        prompt = "START SYSTEM PROMPT" +  " " + system_prompt + " " + "END SYSTEM PROMPT AND START NAMES WITH VARIATIONS" + " "+ str(names_with_variations) + " " +  "NAMES WITH VARIATIONS ENDED" +" "+ "START OVERALL LIST" + " " + str(name_and_id_records) + " "+ "END OVERALL LIST Response: "
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
            




