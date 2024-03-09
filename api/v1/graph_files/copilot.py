import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from configparser import SectionProxy
from semantic_kernel.planning.basic_planner import BasicPlanner
import json
import configparser
from ..graph_files.students import Students
from ..graph_files.courses import Courses
from ..graph_files.institute import Institute
from ..graph_files.skills import StudentSkills,CourseSkills
import re
import math

config = configparser.ConfigParser()
config.read(['config.cfg', 'config.dev.cfg'])
azure_settings = config['azure']

students_instance = Students(azure_settings)
institute_instance = Institute(azure_settings)
courses_instance = Courses(azure_settings)

class UpeaseCopilot:
    settings: SectionProxy
    

    def __init__(self, config:SectionProxy):
        self.settings = config

    async def upease_copilot(self,ask:str) -> str:
        kernel = sk.Kernel()
        api_key = self.settings["openai_api_key"]
        api_base = self.settings["openai_api_base"]
        aoai_chat_service = AzureChatCompletion(
            deployment_name='UpEase-testing',
            endpoint=api_base,
            api_key=api_key
        )
        # api_version = self.settings["openai_api_version"]
        kernel.add_chat_service(
            service = aoai_chat_service,service_id ="dv")
        student_plugin = kernel.import_plugin(plugin_instance = StudentSkills(),plugin_name= "StudentSkills")
        course_plugin = kernel.import_plugin(plugin_instance = CourseSkills(), plugin_name = "CourseSkills")
        planner = BasicPlanner()
        basic_plan = await planner.create_plan(ask,kernel)
        # print(basic_plan)
        results = await planner.execute_plan(basic_plan,kernel)
        return results
        

        
        
