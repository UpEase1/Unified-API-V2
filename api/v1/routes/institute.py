from fastapi import APIRouter, Request, Query, status, Depends, HTTPException
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
institute_instance = Institute(azure_settings)
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


# Student Props
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

