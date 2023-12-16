from fastapi import APIRouter, Request, Query, status
from fastapi.responses import JSONResponse
from graph_files.students import Students
from graph_files.courses import Courses
from configparser import ConfigParser

router = APIRouter()
config = ConfigParser()
config.read(['config.cfg', 'config.dev.cfg'])
azure_settings = config['azure']
students_instance = Students(azure_settings)
courses_instance = Courses(azure_settings)


# Get Info
@router.get("/courses/")
async def get_all_courses():
    courses = await courses_instance.get_all_courses()
    return courses

@router.get("/courses/{course_id}/")
async def get_course_by_id(course_id:str):
    course = await courses_instance.get_course_by_id(course_id=course_id)
    return course

@router.get("/courses/{course_id}/students/")
async def get_students_of_course(course_id:str):
    student_ids = await courses_instance.get_students_of_course(course_id = course_id)
    return student_ids

# Update Info
@router.put("/courses/update/{course_id}/")
async def update_course_by_id(course_id:str,property_name:str, property_value:str):
    await courses_instance.update_course_by_id( course_id=course_id,property_name=property_name,property_value=property_value)
    return JSONResponse({"updated": "ok"}, status.HTTP_200_OK)

@router.post("/courses/update")
async def create_course(course_details:dict):
    course_id = await courses_instance.create_course(course_details)
    return course_id

# Students
# ! Return 201 when an entity is added/created
@router.post("/courses/{course_id}/students/add") 
async def add_students_to_course(course_id:str, request:Request, student_ids:str = Query(None, description="Enter comma seperated student ids")): 
    if student_ids:
        student_ids = student_ids.split(',')
  
    result = await courses_instance.add_students_to_course(student_ids=student_ids,course_id=course_id,students=students_instance)
    return JSONResponse({"created": "ok"}, status.HTTP_201_CREATED)

@router.delete("/courses/{course_id}/students/remove")
async def remove_students_from_course_api(student_ids:list, course_id:str):
    for student_id in student_ids:
        await courses_instance.remove_student_from_course(course_id=course_id,student_id=student_id)
    return JSONResponse({"deleted": "ok"}, status.HTTP_200_OK)

# Delete
# ? This seems redundant, as you can 
# ? remove one course with the same endpoint as the bulk remove
@router.delete("/courses/delete/{course_id}")
async def retire_course_api(course_id:str):
    await courses_instance.retire_course_by_id(course_id=course_id)
    return JSONResponse({"deleted": "ok"}, status.HTTP_200_OK)

# ? How does course_ids: list translate to the url?
@router.delete("/courses/delete")
async def retire_course_bulk(course_ids: list):
    for course_id in course_ids:
        await courses_instance.retire_course_by_id(course_id=course_id)
    pass

# Attendance
# ? This seems pretty incomplete.
# @router.put("/courses/{course_id}/attendance/update")
# async def update_attendance_course(course_id:str, attendance_data:list):
    
    # await add_attendance_to_course_students(course_id = course_id, attendance_data=attendance_data)

# async def add_attendance_to_course_students(courses:Courses,course_id:str,student_id:str,attendance_data:list):
#     for student in attendance_data:
#          attendance_data = student["attendance_dates"]
#          await courses.add_attendance_to_course_student(course_id = course_id,attendance_list=attendance_data,student_id = student_id)