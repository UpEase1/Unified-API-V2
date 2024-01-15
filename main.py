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
from api.v1.routes.routines import router as RoutinesRouter

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
logging.basicConfig(level=logging.WARNING)



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
app.include_router(RoutinesRouter, tags=["Routines"], prefix="/api/v1/routines")
    
# To secure an endpoint, add the parameter current_user:dict = Depends(get_current_user) to the requesting function.

@app.exception_handler(ODataError)
async def odata_error_handler(request: Request, exc: ODataError):
    logger.error(f"OData Error: {exc.error.code} - {exc.error.message}")
    return JSONResponse(
        status_code=400,
        content={
            "Error": f"OData Error: {exc.error.code} - {exc.error.message}"
        },
    )