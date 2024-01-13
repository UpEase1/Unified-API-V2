from fastapi import APIRouter, Request, Query, status, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwcrypto import jwk
import os

from ..graph_files.students import Students
from ..graph_files.courses import Courses
from ..graph_files.institute import Institute
from public_key_gen import initialize_jwks_cache

from configparser import ConfigParser
from jose import JWTError, jwt
from typing import List
import json

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



# Student Props
@router.get("/students/properties")
async def get_student_properties():
    result = await institute_instance.fetch_extensions_student()
    return result

@router.post("/students/properties")
async def create_student_properties(student_properties: list[dict]):
    result = await institute_instance.student_properties_builder_flow(student_properties)

@router.delete("/students/properties")
async def delete_student_properties(student_property_ids: list[str]):
    await institute_instance.delete_student_properties(property_ids=student_property_ids)


# Course Props
@router.get("/courses/properties")
async def get_course_properties():
    result = await institute_instance.fetch_extensions_course()
    return result

@router.post("/courses/properties")
async def create_course_properties(course_properties: list[dict]):
    result = await institute_instance.course_properties_builder_flow(course_properties)

@router.delete("/courses/properties")
async def delete_course_properties(course_property_ids: list[str]):
    await institute_instance.delete_course_properties( property_ids=course_property_ids)

@router.post("/setup")
async def institute_setup_runtime(manifest:dict):
    rendered_manifest = await institute_instance.institute_setup_runtime(manifest=manifest)
    return rendered_manifest