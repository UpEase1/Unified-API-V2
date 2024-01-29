from fastapi import APIRouter, Request, Query, status, Depends, HTTPException,Security
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwcrypto import jwk
import os
from public_key_gen import initialize_jwks_cache
import json

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

# Get the unverified header and the kid from the token

def get_unverified_header(token):
    unverified_header = jwt.get_unverified_header(token)
    return unverified_header.get('kid')


# Verify the token
def get_current_user(authorization: HTTPAuthorizationCredentials = Depends(security)):
    required_scopes = "UpeaseUnified.ReadWrite.All"
    token = authorization.credentials
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Verify the signature
        public_key_path = 'jwks_cache.json'
        if not os.path.exists(public_key_path):
            jwks_data = initialize_jwks_cache(public_key_path)
        else:
            with open(public_key_path, 'r') as key_file:
                jwks_data = json.load(key_file)

        kid = get_unverified_header(token)

        # Try to find the key in the cache
        matching_key_data = next((key for key in jwks_data["keys"] if key["kid"] == kid), None)
        if matching_key_data:
            matching_key = jwk.JWK(**matching_key_data)
            public_key_pem = matching_key.export_to_pem()
            payload = jwt.decode(token, public_key_pem, algorithms=["RS256"], audience=CLIENT_ID)
            if payload.get("aud") != CLIENT_ID or payload.get("scp") != required_scopes:
                raise HTTPException(status_code=401, detail="Invalid audience or scope")
            return payload

        # Refresh the cache and try again
        jwks_data = initialize_jwks_cache(public_key_path)
        matching_key_data = next((key for key in jwks_data["keys"] if key["kid"] == kid), None)
        if matching_key_data:
            matching_key = jwk.JWK(**matching_key_data)
            public_key_pem = matching_key.export_to_pem()
            payload = jwt.decode(token, public_key_pem, algorithms=["RS256"], audience=CLIENT_ID)
            if payload.get("aud") != CLIENT_ID or payload.get("scp") != required_scopes:
                raise HTTPException(status_code=401, detail="Invalid audience or scope")
            return payload

        raise credentials_exception
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"JWT Error: {str(e)}")

# To scope the endpoint add current_user:dict = Depends(get_current_user) to the endpoint funtion
@router.get("/")
async def get_all_students(current_user: dict = Depends(get_current_user)):
    students = await students_instance.get_all_students()
    return students

@router.get("/{student_id}")
async def get_student_by_id(student_id: str,current_user: dict = Depends(get_current_user)):
    student = await students_instance.get_student_by_id(id_num=student_id)
    return student

@router.get("/{student_id}/courses")
async def get_courses_of_student(student_id:str,current_user: dict = Depends(get_current_user)):
    courses = await students_instance.get_courses_of_student(student_id=student_id)
    return courses

@router.get("/{student_id}/attendance")
async def get_attendance(student_id: str, request:Request, course_ids: str = Query(None, description="Enter comma seperated course ids"),current_user: dict = Depends(get_current_user)):
    course_ids = request.query_params.get("course_ids")
    if course_ids:
        course_ids = course_ids.split(",")  

    attendance_records = await courses_instance.get_student_attendance(student_id=student_id,course_ids=course_ids)
    return attendance_records

@router.put("/update/{student_id}")
async def update_student(student_id: str, property_name: str, property_value: str,current_user: dict = Depends(get_current_user)):
    await students_instance.update_student_v1(property_value=property_value,student_id=student_id,property_name=property_name)
    return JSONResponse({"updated": "ok"}, status.HTTP_200_OK)

@router.post("/")
async def create_student(student_properties:dict,current_user: dict = Depends(get_current_user)):
    password_properties = await students_instance.student_creation_singular(student_properties=student_properties)
    return password_properties

@router.post("/bulk")
async def create_student_bulk(student_properties_collection:list,current_user: dict = Depends(get_current_user)):
    password_properties_collection = []
    for student_properties in student_properties_collection:
        password_properties = await students_instance.student_creation_singular(student_properties = student_properties)
        password_properties_collection.append(password_properties)
    return password_properties_collection

@router.delete("/remove/{student_id}")
async def deregister_student(student_id:str,current_user: dict = Depends(get_current_user)):
    await students_instance.deregister_student(student_id = student_id)

@router.delete("/")
async def deregister_students_bulk(student_ids:list,current_user: dict = Depends(get_current_user)):
    for student_id in student_ids:
        await students_instance.deregister_student(student_id = student_id)