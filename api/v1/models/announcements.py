from pydantic import BaseModel, Field
from fastapi import UploadFile
from datetime import datetime
from typing import Union

class AddAnnouncementRequest(BaseModel):
  subject: str
  announcement_message: str
  target_group_mails: list