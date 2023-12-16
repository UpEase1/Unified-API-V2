import json
import configparser
import pandas as pd
from fastapi import FastAPI, Body, Depends, HTTPException, Request, Query, Security
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from graph_files.institute import Institute
from graph_files.students import Students
from graph_files.courses import Courses
from pydantic import create_model, BaseModel,ValidationError
import asyncio
from msgraph.generated.models.o_data_errors.o_data_error import ODataError
from typing import List, Optional
import logging
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
app = FastAPI()

#! CORS Setup for local testing
# Configure CORS to allow requests from your frontend domain(s)
# refer: https://ionicframework.com/docs/troubleshooting/cors
origins = [
    "http://localhost:8100",  # Your local development frontend
    "https://student.upease.biz",  # Your production frontend
    "https://console.upease.biz",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET","POST","DELETE","PUT"],  # You can specify specific HTTP methods if needed
    allow_headers=["Authorization", "Content-Type"],  # You can specify specific headers if needed
)
course_model = None
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration setup
config = configparser.ConfigParser()
config.read(['config.cfg', 'config.dev.cfg'])
azure_settings = config['azure']
students_instance = Students(azure_settings)
institute_instance = Institute(azure_settings)
courses_instance = Courses(azure_settings)
CLIENT_ID = azure_settings['clientId']
CLIENT_SECRET = azure_settings['clientSecret']
security = HTTPBearer()





def get_token_from_header(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Bearer token missing")
    
    token = auth_header.split("Bearer ")[-1]
    return token

# Verify the token
def get_current_user(authorization: HTTPAuthorizationCredentials = Depends(security),required_scopes: List[str] = []):
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
    
#Students
# @app.get("/students/")
# async def get_students_api():
#     return await get_students(students_instance)

# @app.get("/students/{student_id}/")
# async def get_student_api(student_id: str):
#     return await get_student_by_id(students_instance, student_id=student_id)

# @app.get("/students/courses/{student_id}")
# async def get_courses_a_student_is_member_of_api(student_id:str):
#     return await get_courses_a_student_is_member_of(students_instance,student_id=student_id)

# @app.get("/students/{student_id}/attendance")
# async def get_attendance_api(student_id: str, request: Request,course_ids:str=Query(None,description="Enter comma seperated course ids")):
#     if course_ids:
#         course_ids = course_ids.split(",")  # Assuming course_ids are comma-separated
#     attendance_records = await get_attendance_of_student(courses_instance, student_id=student_id, course_ids=course_ids)
#     return attendance_records

# @app.put("/students/{student_id}/")
# async def update_student_api(student_id: str, property_name: str, property_value: str):
#     return await update_student(students_instance, property_value=property_value,property_name=property_name,student_id=student_id)

# @app.post("/students/")
# async def create_students_api(students_data:list):
#     password_json = await create_students(students_instance,students_data=students_data)
#     return password_json

# @app.delete("/students/{student_id}/")
# async def deregister_student_api(student_id:str):
#     return await deregister_student(students_instance,student_id = student_id)

# @app.delete("/students/")
# async def deregister_students_bulk_api(student_ids:list):
#     return await deregister_students_bulk(students_instance,student_ids=student_ids)


#Courses
# @app.get("/courses/")
# async def get_all_courses_api():
#     return await get_all_courses(courses_instance)

# @app.get("/courses/{course_id}/")
# async def get_course_by_id_api(course_id:str):
#     return await get_course_by_id(courses_instance,course_id=course_id)

# @app.get("/courses/{course_id}/students/")
# async def get_students_of_course_api(course_id:str):
#     student_ids = await get_students_of_course(courses_instance,course_id=course_id)
#     return student_ids

# @app.put("/courses/{course_id}/")
# async def update_course_by_id_api(course_id:str,property_name:str, property_value:str):
#     await update_course_by_id(courses_instance,course_id=course_id, property_name=property_name,property_value=property_value)
#     pass

# @app.post("/courses/")
# async def create_course_api(course_details:dict):
#     course_id = await create_course(courses_instance, course_details = course_details)
#     return {'Course ID': course_id}

# @app.post("/courses/{course_id}/students/") 
# async def add_students_to_course_api(course_id:str,request:Request, student_ids:str = Query(None, description="Enter comma seperated student ids")): 
#     if student_ids:
#         student_ids = student_ids.split(',')
#     result = await add_students_to_course(courses=courses_instance,student_ids=student_ids,course_id=course_id,students=students_instance)
#     pass

# @app.delete("/courses/{course_id}/students/")
# async def remove_students_from_course_api(student_ids:list, course_id:str):
#     await remove_students_from_course(courses=courses_instance,student_ids=student_ids,course_id=course_id)
#     pass

# @app.delete("/courses/{course_id}")
# async def retire_course_api(course_id:str):
#     await retire_course_by_id(courses=courses_instance,course_id=course_id)
#     pass

# @app.delete("/courses/")
# async def retire_course_bulk_api(course_ids: list):
#     await retire_course_bulk(courses=courses_instance,course_ids=course_ids)
#     pass
# @app.put("/courses/{course_id}/attendance/")
# async def update_attendance_course_api(course_id:str, attendance_data:list):
#     await add_attendance_to_course_students(course_id = course_id, attendance_data=attendance_data)

#Institute
# @app.get("/institute/students/properties/")
# async def get_student_properties_api():
#     return await get_student_properties_of_institute(institute_instance)

# @app.get("/institute/courses/properties/")
# async def get_course_properties_add_api():
#     return await get_course_properties_of_institute(institute_instance)

# @app.post("/institute/students/properties/")
# async def create_student_properties_add_api(student_properties: list):
#     return await create_student_properties_of_institute(institute_instance, student_properties)

# @app.post("/institute/courses/properties/")
# async def create_course_properties_add_api(course_properties:list):
#     return await create_course_properties_of_institute(institute_instance,course_properties)

# @app.delete("/institute/courses/properties/")
# async def delete_course_properties_api(course_property_ids:list):
#     await delete_course_properties(institute_instance,property_ids=course_property_ids)
#     pass

# @app.delete("/institute/students/properties/")
# async def delete_student_properties_api(student_property_ids:list):
#     await delete_student_properties(institute_instance,property_ids=student_property_ids)
#     pass



    

# It is mandatory to provide all the property values. However, in reality only some mandatory properties are required.
# Currently, for the trial tenant, they are Name and Registration number.
# If you want to test the creation of student and dont have the property value (Or if the property key is frivolous),
# Call the property value "Placeholder" and submit.


# the coroutines to be executed

# async def get_students(students:Students):
#     students = await students.get_all_students()
#     return students

# async def get_student_by_id(students:Students,student_id):
#     student = await students.get_student_by_id(id_num=student_id)
#     return student

# async def get_student_properties_of_institute(institute:Institute):
#     result = await institute.fetch_extensions_student()
#     return result

# async def get_course_properties_of_institute(institute:Institute):
#     result = await institute.fetch_extensions_course()
#     return result

# async def get_attendance_of_student(courses:Courses,student_id:str,course_ids:list):
#     attendance_records = await courses.get_student_attendance(student_id=student_id,course_ids=course_ids)
#     return attendance_records

# async def create_student_properties_of_institute(institute:Institute,student_properties):
#     result = await institute.student_properties_builder_flow(student_properties)

# student_properties = ["Property1","Property2","Property3","Property4"]


# async def create_course_properties_of_institute(institute:Institute,course_properties):
#     result = await institute.course_properties_builder_flow(course_properties)
#     pass

# course_properties = ["Property1", "Property2", "Property3", "Property4"]
# async def update_student(students:Students, property_name: str, property_value: str, student_id: str):
#     await students.update_student_v1(property_value=property_value,student_id=student_id,property_name=property_name)

# async def get_all_courses(courses:Courses):
#     courses = await courses.get_all_courses()
#     return courses

# async def get_courses_a_student_is_member_of(students:Students,student_id):
#     course_ids = await students.get_courses_of_student(student_id=student_id)
#     return course_ids

async def create_enum_extension(institute:Institute,institute_name:str,institute_id:str):
    await institute.create_enum_extension(institute_name=institute_name,institute_id=institute_id)

# async def create_students(students:Students,students_data):
#     password_json = await students.student_creation_bulk(students_data=students_data)
#     return password_json


# async def create_course(courses:Courses,course_details):
#     course_id = await courses.create_course(course_details)
#     return course_id


# async def add_students_to_course(courses:Courses,student_ids:list,course_id:str,students:Students):
#     result = await courses.add_students_to_course(student_ids=student_ids,course_id=course_id,students=students)

# student_ids = [ "id_1", "id_2", "id_3"]


# async def delete_student_properties(institute:Institute,property_ids:list):
#     await institute.delete_student_properties(properties=property_ids)
# properties = [ "id_1", "id_2", "id_3"]

# async def delete_course_properties(institute:Institute,property_ids:list):
#     await institute.delete_course_properties( properties=property_ids)

# properties = [ "id_1", "id_2", "id_3"]

# async def deregister_student(students:Students,student_id:str):
#     await students.deregister_student(student_id = student_id)

# async def deregister_students_bulk(students:Students,student_ids:list):
#     for student_id in student_ids:
#         await students.deregister_student(student_id = student_id)

# async def get_course_by_id(courses:Courses,course_id:str):
#     course= await courses.get_course_by_id(course_id=course_id)
#     return course

# async def update_course_by_id(courses:Courses, course_id:str, property_name:str, property_value:str):
#     await courses.update_course_by_id( course_id=course_id,property_name=property_name,property_value=property_value)

# async def retire_course_by_id(courses:Courses, course_id:str):
#     await courses.retire_course_by_id(course_id=course_id)

# async def retire_course_bulk(courses:Courses, course_ids:list):
#     for course_id in course_ids:
#         await courses.retire_course_by_id(course_id=course_id)

# async def remove_students_from_course(courses:Courses,course_id:str,student_ids:list):
#     for student_id in student_ids:
#         await courses.remove_student_from_course(course_id=course_id,student_id=student_id)

# async def get_students_of_course(courses:Courses,course_id:str):
#     student_ids = await courses.get_students_of_course(course_id= course_id)
#     return student_ids

async def create_institute_document(institute:Institute, institute_name:str):
    await institute.create_institution_extension_document(institute_name=institute_name)

# async def add_attendance_to_course_students(courses:Courses,course_id:str,student_id:str,attendance_data:list):
#     for student in attendance_data:
#          attendance_data = student["attendance_dates"]
#          await courses.add_attendance_to_course_student(course_id = course_id,attendance_list=attendance_data,student_id = student_id)


# Synchronous functions
# </MakeGraphCallSnippet>
def csv_to_json(filepath):
    # Reading the CSV file using pandas
    df = pd.read_csv(filepath)
    df = df.applymap(str)
    # Converting all values to string

    # Returning the JSON representation of the dataframe
    return df.to_dict(orient='records')

def csv_header_to_json(csv_filename):
    df = pd.read_csv(csv_filename)
    header_list = df.columns.tolist()
    header_json = json.dumps(header_list)
    return header_json
    pass


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