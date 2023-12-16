from fastapi import APIRouter, Request, Query, status
from fastapi.responses import JSONResponse
from graph_files.students import Students
from graph_files.courses import Courses
import configparser

router = APIRouter()
config = configparser.ConfigParser()
config.read(['config.cfg', 'config.dev.cfg'])
azure_settings = config['azure']
students_instance = Students(azure_settings)
courses_instance = Courses(azure_settings)


@router.get("/")
async def get_all_students():
    students = await students_instance.get_all_students()
    return students

@router.get("/{student_id}")
async def get_student_by_id(student_id: str):
    student = students_instance.get_student_by_id(id_num=student_id)
    return student

@router.get("/{student_id}/courses")
async def get_courses_of_student(student_id:str):
    course_ids = await students_instance.get_courses_of_student(student_id=student_id)
    return course_ids

# ? Why are we accessing attendance records using courses instance
@router.get("/{student_id}/attendance")
async def get_attendance(student_id: str, request: Request, course_ids: str = Query(None, description="Enter comma seperated course ids")):
    if course_ids:
        course_ids = course_ids.split(",")  

    attendance_records = await courses_instance.get_student_attendance(student_id=student_id,course_ids=course_ids)
    return attendance_records

@router.put("/update/{student_id}")
async def update_student(student_id: str, property_name: str, property_value: str):
    await students_instance.update_student_v1(property_value=property_value,student_id=student_id,property_name=property_name)
    return JSONResponse({"updated": "ok"}, status.HTTP_200_OK)

@router.post("/add")
async def create_students(students_data:list):
    password_json = await students_instance.student_creation_bulk(students_data=students_data)
    return password_json

@router.delete("/remove/{student_id}")
async def deregister_student(student_id:str):
    await students_instance.deregister_student(student_id = student_id)

@router.delete("/remove")
async def deregister_students_bulk(student_ids:list):
    for student_id in student_ids:
        await students_instance.deregister_student(student_id = student_id)