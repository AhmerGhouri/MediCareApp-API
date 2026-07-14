from sqlalchemy import Column, Integer, String, Date
from app.db.oracle import Base

# 1. The App User (For login credentials)
class AppUser(Base):
    __tablename__ = "MMH_USERREGDATA"
    __table_args__ = {"schema": "aass"} 
    
    autoid = Column(Integer, primary_key=True, index=True)
    # mob = Column(String(15), unique=True, index=True)
    mob = Column(String(15), index=True , unique=True)
    password = Column(String(255))

# 2. The Existing Hospital Patient Table (Read-Only map)
# Add these columns so SQLAlchemy knows how to handle them
    email = Column(String)
    pname = Column(String)
    dob = Column(String)     # Or Column(Date) depending on your DB
    gender = Column(String)
    isactive = Column(String)
    datafrom = Column(String)
    
class HospitalPatient(Base):
    __tablename__ = "OPAT_T"
    __table_args__ = {"schema": "aass"} 
    
    opat_id = Column(String(50), primary_key=True, index=True)
    opat_phone = Column(String(15), index=True)
    opat_pname = Column(String(100))
    opat_bdate = Column(Date)
    opat_sex = Column(String(2))
    # Add other columns as needed (gender, blood_group, etc.)
    
class EligibleUser(Base):
    __tablename__ = "MMH_USERREGDATA" # The pre-authorized list
    __table_args__ = {'extend_existing': True , "schema" : "aass"} # This allows us to reuse the same table for both AppUser and EligibleUser
    
    mob = Column(String, primary_key=True)
    pname = Column(String)
