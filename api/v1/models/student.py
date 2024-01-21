from pydantic import BaseModel, Field
from datetime import datetime
from typing import Union

example_todo_list: dict = {
  "student_name": "Aaryan Dongre",
  "position": "student",
  "registration_number": 230962162,
}

# Add optional fields using Union[str, None] iirc

# --------------
# Request Models
# --------------
class AddStudentRequest(BaseModel):
    student_name: str = Field(..., max_length=200)
    position: str = Field(..., max_length=100)
    registration_number: int = Field(..., max_length=100)

# ---------------
# Response Models
# ---------------
class BaseStudentResponse(BaseModel):
    username: str
    todo_items: list[dict[str, str]] = example_todo_list