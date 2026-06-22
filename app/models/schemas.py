# app/schemas.py
from datetime import date
from pydantic import BaseModel, ConfigDict
from typing import List, Optional

class RegisterRequest(BaseModel):
    mobile_number: str
    password: str  # Add this field
    email: str  # Optional email field
    full_name: str  
    date_of_birth: str
    password: str
    gender: str

class LoginRequest(BaseModel):
    mobile_number: str
    password: str

class MRNumberResponse(BaseModel):
    mr_no: str
    patient_name: str
    gender: str
    dob: date
    

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    mr_numbers: List[MRNumberResponse]
    
class CheckEligibilityRequest(BaseModel):
    mobile_number: str
    
# class ConsultantOut(BaseModel):
    
#     model_config = ConfigDict(
#         from_attributes=True,
#         alias_generator=lambda field_name: field_name.lower(),
#         populate_by_name=True
#     )
    
#     CONSL_ID: str | int
#     CONSL_DESC: Optional[str] = None
#     CONSL_DEGR: Optional[str] = None
#     CONSL_SPEC_ID: Optional[str] = None
#     CONSL_STATUS: int
#     CONSL_MDEPT_ID: Optional[str] = None
#     D_MDEPT_DESC: Optional[str] = None # Renamed to match query or aliases

#     class Config:
#         from_attributes = True
    
