# app/schemas.py
from datetime import date
from pydantic import BaseModel, ConfigDict, EmailStr
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

class DeviceTokenRequest(BaseModel):
    device_token: str
    platform: str  # 'android' or 'ios'

class MRNumberResponse(BaseModel):
    mr_no: str
    patient_name: Optional[str] = None
    gender: Optional[str] = None
    # Wrap date with Optional to allow NULL / None from Oracle
    dob: Optional[date] = None  

    # Enable ORM mode so SQLAlchemy objects convert automatically
    model_config = {"from_attributes": True}  # Pydantic v2
    # class Config: orm_mode = True            # Use this instead if on Pydantic v1
    
class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    mr_numbers: List[MRNumberResponse]
    
class CheckEligibilityRequest(BaseModel):
    mobile_number: str

class ResetPassword(BaseModel):
    mobile_number: str
    password: str
    
class AppointmentBooking(BaseModel):
    tran_id : int
    consl_id : str
    appoint_date : str
    mobile_number : str
    from_time : str
    to_time : str
    appointment_day : str
    appoint_time : str
    opat_id : str
    patient_name : str
    # appoint_confirm_date : str    
    
class OTPRequest(BaseModel):
    email: EmailStr
    mobile: str

class PasswordResetConfirm(BaseModel):
    mobile: str
    email: EmailStr
    otp_code: str
    new_password: str
 
