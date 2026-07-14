# app/routers/auth_router.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.oracle import get_db
from app.models.models import AppUser, HospitalPatient, EligibleUser
from app.models.schemas import RegisterRequest, LoginRequest, LoginResponse, CheckEligibilityRequest, ResetPassword
from app.api.auth.auth import get_password_hash, verify_password, create_access_token

router = APIRouter()

@router.post("/register")
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    # 1. Check if the user already exists to avoid ORA-00001 (Unique Constraint)
    existing_user = db.query(AppUser).filter(AppUser.mob == request.mobile_number).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Mobile number already registered")

    # 2. Create a new instance of your Oracle Model
    # We map the names from your Pydantic Schema to your Oracle Columns
    new_user = AppUser(
        mob=request.mobile_number,
        password=request.password,  # Storing as plain text to match your current DB setup
        email=request.email,
        pname=request.full_name,
        dob=request.date_of_birth,
        gender=request.gender,
        isactive="Yes",              # Defaulting values needed by your DB
        datafrom="MobileApp"         # Helping hospital staff know where this user came from
    )

    try:
        # 3. Add and Commit to Oracle
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return {"message": "User registered successfully", "user_id": new_user.autoid}
    
    except Exception as e:
        db.rollback()
        # raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        raise e
    
    
@router.post("/login", response_model=LoginResponse)
# @router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    # 1. Verify the app user credentials
    user = db.query(AppUser).filter(AppUser.mob == request.mobile_number).first()
    
    if not user or not verify_password(request.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid mobile number or password"
        )
    
    # 2. Fetch all MR numbers associated with this mobile number
    patients = db.query(HospitalPatient).filter(HospitalPatient.opat_phone == user.mob).all()
    
    
    # 3. Generate the JWT Token
    access_token = create_access_token(data={"sub": user.mob})
    
    # 4. Return the token and the array of MR numbers to the React Native app
    return {
        "access_token": access_token,
        "token_type": "bearer",
        # "mr_numbers": [{"mr_no": str(p.opat_id), "patient_name": p.opat_pname , "gender" : p.opat_sex , "dob" : p.opat_bdate} for p in patients]
        "mr_numbers": [{"mr_no": str(p.opat_id), "patient_name": p.opat_pname , "gender" : p.opat_sex , "dob" : p.opat_bdate} for p in patients]
    }
    
    # return access_token
    
@router.post("/check-eligibility")
def check_eligibility(request: CheckEligibilityRequest, db: Session = Depends(get_db)):
    # 1. Check if the number exists in the hospital's authorized list
    # is_eligible = db.query(EligibleUser).filter(EligibleUser.mob == request.mobile_number).first()
    
    query = text("""SELECT OPAT_PHONE FROM aass.OPAT_T WHERE OPAT_PHONE = :mobile_number
                UNION
                SELECT IPAT_SPOUSE_PHONE FROM aass.IPAT_T WHERE IPAT_SPOUSE_PHONE = :mobile_number
                UNION
                SELECT BILLM_CELL_NO FROM aass.BILLM_T WHERE BILLM_CELL_NO = :mobile_number

    """)        
    result = db.execute(query, {"mobile_number": request.mobile_number}).fetchone()
    
    if not result:
        # 403 Forbidden is the standard for "Not Authorized"
        raise HTTPException(
            status_code=403, 
            detail="Your number is not registered in our hospital records. Please contact administration."
        )

    # 2. Check if they already have an account created
    already_registered = db.query(AppUser).filter(AppUser.mob == request.mobile_number).first()
    
    if already_registered:
        return {
            "eligible": True,
            "status": "already_registered",
            "message": "You already have an account. Please log in."
        }

    # 3. Success: They are authorized to proceed to registration
    return {
        "eligible": True,
        "status": "new_user",
        # "name_on_record": result.pname, # Sending back the name is a nice UX touch
        "message": "Verification successful! Please complete your registration."
    }
    
    
    
    
@router.post("/reset-password")
def reset_password(request: ResetPassword, db: Session = Depends(get_db)):
    # 1. Check if the number exists in the hospital's authorized list
    # is_eligible = db.query(EligibleUser).filter(EligibleUser.mob == request.mobile_number).first()
    
    query = text("""UPDATE aass.MMH_USERREGDATA 
                    SET PASSWORD = :password
                    WHERE MOB = :mobile_number
    """)        
    
    # Execute update and analyze row effect
    result = db.execute(query, {"mobile_number": request.mobile_number , "password" : request.password})
    
    try:
        if result.rowcount == 0:
            # If 0 rows are updated, the slot was either already taken or the details are invalid
            db.rollback()
            raise HTTPException(
                status_code=409, 
                detail="Your number is not registered in our hospital records. Please contact administration."
            )
        else:
            db.commit()
            
    except HTTPException:
        # Re-raise our custom 409 conflict exception cleanly without dropping into generic error handler
        raise
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database execution failed: {str(e)}")

    return {
        "status": "success", 
        "message": "Password has been reset successfully."
    }
    
    
    
    
      
    # ---------------------------------------------------------------------------------------------
    
    # 1. Check if the mobile number exists in the hospital's patient database
    # hospital_records = db.query(HospitalPatient).filter(HospitalPatient.opat_phone == request.mobile_number).all()
    
    # if not hospital_records:
    #     raise HTTPException(
    #         status_code=status.HTTP_404_NOT_FOUND, 
    #         detail="Mobile number not found in hospital records."
    #     )
    
    # # 2. Check if the user has already registered for the mobile app
    # existing_user = db.query(AppUser).filter(AppUser.mob == request.mobile_number).first()
    # if existing_user:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST, 
    #         detail="User already registered. Please proceed to login."
    #     )
    
    # # 3. Create the app user with a hashed password
    # hashed_pwd = get_password_hash(request.password)
    # # new_app_user = AppUser(mobile_number=request.mobile_number, hashed_password=hashed_pwd)
    # new_app_user = AppUser(mobile_number=request.mobile_number, password=hashed_pwd)
    
    # db.add(new_app_user)
    # db.commit()
    
    # return {"message": "Registration successful. You can now log in."}
    
    # --------------------------------------------------------------------------------------------- 
