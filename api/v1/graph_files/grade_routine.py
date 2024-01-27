import configparser
from configparser import SectionProxy
import numpy as np
from .institute import Institute
from .students import Students
from azure.identity.aio import ClientSecretCredential
from msgraph import GraphServiceClient
from azure.cosmos import CosmosClient, DatabaseProxy
from .singletons import GraphServiceClientSingleton,CosmosServiceClientSingleton


config = configparser.ConfigParser()
config.read(['config.cfg', 'config.dev.cfg'])
azure_settings = config['azure']

students_instance = Students(azure_settings)
institute_instance = Institute(azure_settings)


class GradeRoutine:
    settings: SectionProxy
    client_credential: ClientSecretCredential
    app_client: GraphServiceClient
    client: CosmosClient
    db: DatabaseProxy


    def __init__(self, config: SectionProxy): 
        self.settings = config
        self.cosmos_client = CosmosServiceClientSingleton.get_instance()
        self.db = self.cosmos_client.get_database_client('courses_manipal')
        self.container = self.db.get_container_client('courses_manipal')
        self.app_client = GraphServiceClientSingleton.get_instance()

    async def evaluate_grades_for_course(self, course_id, grade_type):
        query = """
            SELECT c.courses.grade_type_definitions
            FROM c
            WHERE c.id = @tenant_id
        """
    
        # Setting the query parameters
        parameters = [{"name": "@tenant_id", "value": self.settings['tenantId']}]
        query_result = list(self.container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))

        #? What if not query result
        if query_result:
            rules = query_result[0]['grade_type_definitions']

        grading_system = GradingSystem(rules)

        # Get the scores for the course from the course document
        course_data = self.container.read_item(partition_key = course_id, item = course_id)

        scores = []
        for student in course_data['students']:
            if student['assignments'] == []:
                return "No assignment data, Error"

            total_score = 0
            max_score = 0
            
            for assignment in student['assignments']:
                total_score = total_score + assignment['score']
                max_score = max_score + assignment['max']
            
            scores.append({
                'student_id': student['student_id'], 
                'student_name': student['student_name'],
                'total_score': total_score*100/max_score,
            })
        
        return grading_system.calculate_grades(grade_type, scores=scores)


class GradingRule:
    def __init__(self, rule_dict:dict):
        self.grade = rule_dict['grade']
        self.scale = rule_dict.get('scale', None)
        self.abs_rule = rule_dict.get('abs_rule', None)
        self.rel_rule = rule_dict.get('rel_rule', None)
        self.type = rule_dict['type']

    def evaluate_absolute(self, score) -> bool:
        if self.abs_rule is not None:
            return eval(self.abs_rule, {'total_score': score})
        return False

    def evaluate_relative(self, score, mean, std_dev) -> bool:
        if self.rel_rule is not None:
            return eval(self.rel_rule, {'total_score': score, 'mean': mean, 'std_dev': std_dev})
        return False


class GradingSystem:
    def __init__(self, rules: list):
        self.rules = [GradingRule(rule) for rule in rules]

    def get_grade_scale(self, grade):
        for rule in self.rules:
            if grade == rule.grade:
                return rule.scale
        return None

    def get_grade_by_scale(self, scale):
        for rule in self.rules:
            if scale == rule.scale:
                return rule.grade
        return None

    def calculate_absolute_grade(self, score):
        for rule in self.rules:
            if rule.evaluate_absolute(score):
                return rule.grade
        return None

    def calculate_relative_grade(self, score, mean, std_dev):
        for rule in self.rules:
            if rule.evaluate_relative(score, mean, std_dev):
                return rule.grade
        return None

    def calculate_grades(self, grade_type: str, scores: list[dict]):
        score_vals = [score['total_score'] for score in scores]
        mean = np.mean(score_vals)
        std_dev = np.std(score_vals)

        student_grades = []

        for score in scores:
            if grade_type == 'absolute':
                grade = self.calculate_absolute_grade(score['total_score'])

            elif grade_type == 'relative':
                absolute_grade = self.calculate_absolute_grade(score['total_score'])
                relative_grade = self.calculate_relative_grade(score['total_score'], mean, std_dev)
                absolute_scale = self.get_grade_scale(absolute_grade)
                relative_scale = self.get_grade_scale(relative_grade)
                grade = self.get_grade_by_scale(max(absolute_scale, relative_scale))

            else:
                grade = None

            student_grades.append({
                'score':score['total_score'], 
                'grade':grade, 
                'student_id':score['student_id'], 
                'student_name':score['student_name']
            })

        return student_grades