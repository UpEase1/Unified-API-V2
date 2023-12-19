from fastapi import APIRouter, Request, Query, status,HTTPException,Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..graph_files.students import Students
from ..graph_files.courses import Courses
from ..graph_files.institute import Institute

from configparser import ConfigParser
from jose import JWTError, jwt
from typing import List

router = APIRouter()
config = ConfigParser()
config.read(['config.cfg', 'config.dev.cfg'])
azure_settings = config['azure']
students_instance = Students(azure_settings)
courses_instance = Courses(azure_settings)
CLIENT_ID = azure_settings['clientId']
security = HTTPBearer()



# Auth
def get_token_from_header(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Bearer token missing")
    
    token = auth_header.split("Bearer ")[-1]
    return token


# Verify the token
def get_current_user(authorization: HTTPAuthorizationCredentials = Depends(security), required_scopes: List[str] = []):
    token = authorization.credentials
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decode the token
        public_key_path = 'public_key.pem'
        with open(public_key_path, 'r') as key_file:
            public_key = key_file.read()
        payload = jwt.decode(token, public_key, algorithms=["RS256"], audience=CLIENT_ID)
        if payload.get("aud") != CLIENT_ID and payload.get("scp") != required_scopes:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception

# Get Info
@router.get("/")
async def get_all_courses():
    courses = await courses_instance.get_all_courses()
    return courses

@router.get("/{course_id}/")
async def get_course_by_id(course_id:str):
    course = await courses_instance.get_course_by_id(course_id=course_id)
    return course

@router.get("/{course_id}/students/")
async def get_students_of_course(course_id:str):
    student_ids = await courses_instance.get_students_of_course(course_id = course_id)
    return student_ids

# Update Info
@router.put("/update/{course_id}")
async def update_course_by_id(course_id:str,property_name:str, property_value:str):
    await courses_instance.update_course_by_id( course_id=course_id,property_name=property_name,property_value=property_value)
    return JSONResponse({"updated": "ok"}, status.HTTP_200_OK)

# Create Course
@router.post("/create")
async def create_course(course_details:dict):
    course_id = await courses_instance.create_course(course_details)
    return course_id

# Students
# ! Return 201 when an entity is added/created
@router.post("/{course_id}/students/add") 
async def add_students_to_course(course_id:str, request:Request, student_ids:str = Query(None, description="Enter comma seperated student ids")): 
    if student_ids:
        student_ids = student_ids.split(',')
  
    result = await courses_instance.add_students_to_course(student_ids=student_ids,course_id=course_id,students=students_instance)
    return JSONResponse({"created": "ok"}, status.HTTP_201_CREATED)

@router.delete("/{course_id}/students/remove")
async def remove_students_from_course_api(student_ids:list, course_id:str):
    for student_id in student_ids:
        await courses_instance.remove_student_from_course(course_id=course_id,student_id=student_id)
    return JSONResponse({"deleted": "ok"}, status.HTTP_200_OK)


@router.delete("/delete")
async def retire_course_bulk(course_ids: list):
    for course_id in course_ids:
        await courses_instance.retire_course_by_id(course_id=course_id)
    pass


@router.put("/courses/{course_id}/attendance/update")
async def update_attendance_course(course_id:str, attendance_data:list):
    await courses_instance.add_attendance_to_course_students(course_id = course_id, new_attendance_data = attendance_data)