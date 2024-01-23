from fastapi import APIRouter, Request, Query, status, HTTPException, Depends, File, Form
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..graph_files.students import Students
from ..graph_files.courses import Courses
from ..graph_files.institute import Institute
from ..graph_files.grade_routine import GradeRoutine
from ..graph_files.openai import OpenAI
from ..graph_files.announcement_routine import AnnouncementRoutine

from ..models.announcements import *

from configparser import ConfigParser
from jose import JWTError, jwt
from typing import List
from jwcrypto import jwk
import os
from public_key_gen import initialize_jwks_cache
import json

router = APIRouter()
config = ConfigParser()
config.read(['config.cfg', 'config.dev.cfg'])
azure_settings = config['azure']
grade_routines_instance = GradeRoutine(azure_settings)
announcement_routines_instance = AnnouncementRoutine(azure_settings)
openai_api_instance = OpenAI(azure_settings)
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

@router.get("/{course_id}/{calculated_type}/grades")
async def get_grades_for_course(course_id, calculated_type):
    grades = await grade_routines_instance.evaluate_grades_for_course(course_id=course_id,grade_type=calculated_type)
    return JSONResponse({"grades": grades}, 200)

@router.get("/announcements")
async def get_all_announcements(current_user: dict = Depends(get_current_user)):
    announcements = await announcement_routines_instance.get_all_announcements(user_id = current_user["oid"])
    return announcements


@router.post("/announcements")  
async def make_announcement(
    subject: str = Form(...),
    announcement_message: str = Form(...),
    target_group_mails: list[str] = Form(...),
    file_attachments: list[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user)
):
    # return {"file_attachments": file_attachments[0, "announcements": subject}
    return await announcement_routines_instance.make_announcement_admin_dev(
        user_id = current_user["oid"], 
        subject=subject,
        announcement_message=announcement_message,
        file_attachments=file_attachments,
        target_group_mails=target_group_mails
    )

    
