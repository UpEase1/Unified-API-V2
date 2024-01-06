import numpy as np
import random

import numpy as np

class GradingRule:
    def __init__(self, rule_dict):
        self.grade = rule_dict['grade']
        self.scale = rule_dict.get('scale', None)
        self.abs_rule = rule_dict.get('abs_rule', None)
        self.rel_rule = rule_dict.get('rel_rule', None)
        self.type = rule_dict['type']

    def evaluate_absolute(self, score):
        if self.abs_rule is not None:
            return eval(self.abs_rule, {'total_score': score})
        return False

    def evaluate_relative(self, score, mean, std_dev):
        if self.rel_rule is not None:
            return eval(self.rel_rule, {'total_score': score, 'mean': mean, 'std_dev': std_dev})
        return False


class GradingSystem:
    def __init__(self, rules):
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

    def calculate_grades(self, grade_type, scores):
        mean = np.mean(scores)
        std_dev = np.std(scores)

        student_grades = []
        for score in scores:
            if grade_type == 'absolute':
                grade = self.calculate_absolute_grade(score)
            elif grade_type == 'relative':
                absolute_grade = self.calculate_absolute_grade(score)
                relative_grade = self.calculate_relative_grade(score, mean, std_dev)
                absolute_scale = self.get_grade_scale(absolute_grade)
                relative_scale = self.get_grade_scale(relative_grade)
                grade = self.get_grade_by_scale(max(absolute_scale, relative_scale))
            else:
                grade = None

            student_grades.append({'score':score, 'grade':grade})

        return student_grades
grade_type = 'relative'
max_score = 100
true_scores = [64.53, 42.69, 54.53, 65.12, 40.36, 39.06, 47.23, 38.91, 60.03, 54.13, 40.97, 35.73, 45.01, 51.92, 26.79, 51.19, 33.84, 50.70, 68.03, 37.00]
rules = [
            {
                "grade": "A+",
                "scale": 10,
                "rel_rule": "100 >= total_score >= mean + 1.5*std_dev",
                "abs_rule": "90 <= total_score <= 100",
                "type": "calculated"
            },
            {
                "grade": "A",
                "scale": 9,
                "rel_rule": "mean + 1.5*std_dev > total_score >= mean + 0.5*std_dev",
                "abs_rule": "80 <= total_score < 90",
                "type": "calculated"
            },
            {
                "grade": "B",
                "scale": 8,
                "rel_rule": "mean + 0.5*std_dev > total_score >= mean - 0.5*std_dev",
                "abs_rule": "70 <= total_score < 80",
                "type": "calculated"
            },
            {
                "grade": "C",
                "scale": 7,
                "rel_rule": "mean - 0.5*std_dev > total_score >= mean - 1.0*std_dev",
                "abs_rule": "60 <= total_score < 70",
                "type": "calculated"
            },
            {
                "grade": "D",
                "scale": 6,
                "rel_rule": "mean - 1.0*std_dev > total_score >= mean - 1.5*std_dev",
                "abs_rule": "50 <= total_score < 60",
                "type": "calculated"
                
            },
            {
                "grade": "E",
                "scale": 5,
                "rel_rule": "mean - 1.5*std_dev > total_score >= mean - 2.0*std_dev",
                "abs_rule": "40 <= total_score < 50",
                "type": "calculated"
            },
            {
                "grade": "F",
                "scale": 0,
                "rel_rule": "0 <= total_score < mean - 2.0*std_dev",
                "abs_rule": "0 < total_score < 40",
                "type": "calculated"
            },
            {
                "grade": "I",
                "scale": 0,
                "type": "non_calculated"
            },
            {
                "grade": "DT",
                "scale": 0,
                "type": "non_calculated"
            }
        ]
grading_system = GradingSystem(rules)
grades = grading_system.calculate_grades(grade_type,scores=[score*100/max_score for score in true_scores])
print(grades)