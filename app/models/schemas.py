# app/schemas.py
from datetime import date, timedelta
import re
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from typing import List, Optional


TIME_PATTERN = re.compile(r"^\d{2}:\d{2}$")
class AgentAppointmentBooking(BaseModel):
    """Body for the voice agent. MR number and mobile number are optional."""
    patient_name: str = Field(min_length=1, max_length=100)
    mobile_number: Optional[str] = Field(default=None, max_length=30)
    opat_id: Optional[str] = Field(default=None, max_length=50)
    appoint_date: str            # DD-MON-YYYY (e.g. 27-JUN-2026) or YYYY-MM-DD
    appoint_time: str            # HH:MM, must match a slot time
    from_time: str               # HH:MM
    to_time: str                 # HH:MM
    appointment_day: str = Field(min_length=1, max_length=20)

    @field_validator("patient_name")
    @classmethod
    def clean_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("name is empty")
        return v

    @field_validator("mobile_number")
    @classmethod
    def clean_mobile(cls, v):
        if v is None:
            return None
        digits = re.sub(r"\D", "", v)
        return digits[:15] or None   # keep digits only; empty becomes None

    @field_validator("appoint_time", "from_time", "to_time")
    @classmethod
    def check_time(cls, v):
        v = v.strip()
        if not TIME_PATTERN.match(v):
            raise ValueError("time must be HH:MM")
        return v


class ClinicAppointmentRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    phone_number: str = Field(max_length=20)
    specialty: str = Field(min_length=2, max_length=100)
    doctor_name: Optional[str] = Field(default=None, max_length=150)
    preferred_date: date
    captcha_token: str = Field(min_length=10, max_length=2048)
    website: Optional[str] = None   # honeypot: real users leave this empty

    @field_validator("full_name", "specialty", "doctor_name")
    @classmethod
    def clean_text(cls, v):
        return v.strip() if v else v

    @field_validator("phone_number")
    @classmethod
    def valid_phone(cls, v):
        digits = re.sub(r"[\s\-()]", "", v)
        if not re.fullmatch(r"\+?\d{10,15}", digits):
            raise ValueError("invalid phone")
        return digits

    @field_validator("preferred_date")
    @classmethod
    def valid_date(cls, v):
        if v < date.today() or v > date.today() + timedelta(days=90):
            raise ValueError("date out of range")
        return v

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
    
class AgentPatientRequest(BaseModel):
    mobile_number: str

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
 
