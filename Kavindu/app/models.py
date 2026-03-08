from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ReportCreate(BaseModel):
    region: str
    location: str
    offence_type: str
    incident_datetime: Optional[str] = None
    description: str
    image_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class ReportOut(ReportCreate):
    id: str = Field(alias="_id")
    status: str
    source: str
    created_at: datetime

class UserBase(BaseModel):
    name: str
    email: str
    role: str = "officer"
    region: Optional[str] = None
    badge_number: Optional[str] = None
    phone: Optional[str] = None

class UserInDB(UserBase):
    id: str = Field(alias="_id")
    password_hash: str
    is_active: bool = True
    created_at: datetime

class UserOut(UserBase):
    name: str
    email: str
    role: str

class Token(BaseModel):
    token: str
    user: UserOut

class LoginRequest(BaseModel):
    email: str
    password: str

class AssignTeamRequest(BaseModel):
    assigned_team: List[str]  # list of officer emails
    team_lead: Optional[str] = None

class CreateOfficerRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str = "officer"
    region: Optional[str] = None
    badge_number: Optional[str] = None
    phone: Optional[str] = None

class UpdateOfficerRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    region: Optional[str] = None
    badge_number: Optional[str] = None
    phone: Optional[str] = None
