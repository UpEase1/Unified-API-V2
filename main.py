import json
import configparser
import pandas as pd
from msgraph.generated.models.o_data_errors.o_data_error import ODataError
from typing import List, Optional
from jose import JWTError, jwt
import logging

from fastapi import FastAPI, Body, Depends, HTTPException, Request, Query, Security
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware

from api.v1.routes.courses import router as CoursesRouter
from api.v1.routes.institute import router as InstituteRouter
from api.v1.routes.students import router as StudentsRouter

app = FastAPI()
security = HTTPBearer()

# CORS
origins = [
    "http://localhost:8100",
    "https://student.upease.biz",
    "https://console.upease.biz",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET","POST","DELETE","PUT"],  # You can specify specific HTTP methods if needed
    allow_headers=["Authorization", "Content-Type"],  # You can specify specific headers if needed
)


# Debugger
course_model = None
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ! Still have to figure out config for routers
# Setup
config = configparser.ConfigParser()
config.read(['config.cfg', 'config.dev.cfg'])
azure_settings = config['azure']
CLIENT_ID = azure_settings['clientId']
CLIENT_SECRET = azure_settings['clientSecret']


# Routers
app.include_router(StudentsRouter, tags=["Students"], prefix="/api/v1/students")
app.include_router(CoursesRouter, tags=["Courses"], prefix="/api/v1/courses")
app.include_router(InstituteRouter, tags=["Institute"], prefix="/api/v1/institute")

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
    
# To secure an endpoint, add the parameter current_user:dict = Depends(get_current_user) to the requesting function.

# Exception handler
@app.exception_handler(ODataError)
async def odata_error_handler(request: Request, exc: ODataError):
    logger.error(f"OData Error: {exc.error.code} - {exc.error.message}")
    return JSONResponse(
        status_code=400,
        content={
            "Error": f"OData Error: {exc.error.code} - {exc.error.message}"
        },
    )

# # modifying the openapi schema to reflect our dynamic models
# original_openapi = app.openapi
# def custom_openapi_course():
#     if app.openapi_schema:
#         return app.openapi_schema
#     openapi_schema = original_openapi()
#     # if course_model:
#     #     # Inject our dynamic model into the OpenAPI schema
#     #     openapi_schema["components"]["schemas"]["CourseModel"] = course_model.schema()
#     #     # openapi_schema["components"]["schemas"]["StudentModel"] = student_model.schema()
#     #     # Reference the dynamic model in the desired path and method
#     #     openapi_schema["paths"]["/courses/create/"]["post"]["requestBody"]["content"]["application/json"]["schema"] = {
#     #         "$ref": "#/components/schemas/CourseModel"
#     #     }
#         # openapi_schema["paths"]["/students/create/"]["post"]["requestBody"]["content"]["application/json"]["schema"] = {
#         #     "$ref": "#/components/schemas/StudentModel"
#         #}
        
#     app.openapi_schema = openapi_schema
#     return app.openapi_schema

# app.openapi = custom_openapi_course