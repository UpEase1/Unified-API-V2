from fastapi import APIRouter, Request, Query, status
from fastapi.responses import JSONResponse

from ..graph_files.students import Students
from ..graph_files.courses import Courses
from ..graph_files.institute import Institute

from configparser import ConfigParser

router = APIRouter()
config = ConfigParser()
config.read(['config.cfg', 'config.dev.cfg'])
azure_settings = config['azure']
students_instance = Students(azure_settings)
courses_instance = Courses(azure_settings)
institute_instance = Institute(azure_settings)

# Student Props
# ? What are properties
@router.get("/students/properties/")
async def get_student_properties():
    result = await institute_instance.fetch_extensions_student()

@router.post("/students/properties/create")
async def create_student_properties(student_properties: list[dict]):
    result = await institute_instance.student_properties_builder_flow(student_properties)

@router.delete("/students/properties/delete")
async def delete_student_properties(student_property_ids: list[str]):
    await institute_instance.delete_student_properties(properties=student_property_ids)


# Course Props
@router.get("/courses/properties/")
async def get_course_properties():
    result = await institute_instance.fetch_extensions_course()
    return result

@router.post("/courses/properties/create")
async def create_course_properties(course_properties: list[dict]):
    result = await institute_instance.course_properties_builder_flow(course_properties)

@router.delete("/courses/properties/delete")
async def delete_course_properties(course_property_ids: list[str]):
    await institute_instance.delete_course_properties( properties=course_property_ids)

