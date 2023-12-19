from fastapi import APIRouter, Request, Query, status, Depends, HTTPException,Security
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


from ..graph_files.students import Students
from ..graph_files.courses import Courses
from ..graph_files.institute import Institute

from configparser import ConfigParser
from jose import JWTError, jwt
from typing import List,Optional
import logging

router = APIRouter()
config = ConfigParser()
config.read(['config.cfg', 'config.dev.cfg'])
azure_settings = config['azure']
students_instance = Students(azure_settings)
courses_instance = Courses(azure_settings)
CLIENT_ID = azure_settings['clientId']

security = HTTPBearer()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Auth
def get_token_from_header(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Bearer token missing")
    
    token = auth_header.split("Bearer ")[-1]
    return token


# Verify the token
def get_current_user(authorization: HTTPAuthorizationCredentials = Depends(security)):
    required_scopes = 'UpeaseUnified.ReadWrite.All'
    token = authorization.credentials
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        logger.debug(f"Token received: {token}")
        # Decode the token
        public_key_path = 'public_key.pem'
        with open(public_key_path, 'r') as key_file:
            public_key = key_file.read()
        payload = jwt.decode(token, public_key, algorithms=["RS256"], audience=CLIENT_ID)
        logger.debug(f"Decoded payload: {payload}")
        if payload.get("aud") != CLIENT_ID or payload.get("scp") != required_scopes:
            raise credentials_exception
        return payload
    except JWTError as e:
        logger.error(f"JWT error occured: {e}")
        raise credentials_exception


@router.get("/")
async def get_all_students(current_user:dict = Depends(get_current_user)):
    students = await students_instance.get_all_students()
    return students

@router.get("/{student_id}")
async def get_student_by_id(student_id: str):
    student = await students_instance.get_student_by_id(id_num=student_id)
    return student

@router.get("/{student_id}/courses")
async def get_courses_of_student(student_id:str):
    course_ids = await students_instance.get_courses_of_student(student_id=student_id)
    return cou --rse_ids

@router.get("/{student_id}/attendance")
async def get_attendance(student_id: str, request:Request, course_ids: str = Query(None, description="Enter comma seperated course ids"),current_user:dict =Depends(get_current_user)):
    course_ids = request.query_params.get("course_ids")
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