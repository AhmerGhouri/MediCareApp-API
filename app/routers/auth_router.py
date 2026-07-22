# app/routers/auth_router.py
from multiprocessing import get_context
import random
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.oracle import get_db
from app.models.models import AppUser, HospitalPatient, EligibleUser
from app.models.schemas import OTPRequest, PasswordResetConfirm, RegisterRequest, LoginRequest, LoginResponse, CheckEligibilityRequest, ResetPassword
from app.api.auth.auth import get_password_hash, verify_password, create_access_token
from app.routers.emailservice import send_otp_email
from app.logger import logger

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
    
    
    
@router.post("/request-otp")
def request_otp(payload: OTPRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    
    # 1. Verify user exists 
    # (Replace APP_USERS_T with your actual users table)
    check_user = text("SELECT 1 FROM MMH_USERREGDATA WHERE mob = :mobile")
    if not db.execute(check_user, {"mobile" : payload.mobile}).fetchone():
        logger.warning(f"OTP requested for unregistered email: {payload.mobile}")
        return {"status": "success", "message": "If that email is registered, an OTP has been sent."}

    # 2. Generate a secure 6-digit code
    otp_code = str(random.randint(100000, 999999))
    
    # 3. Store in database with a 10-minute Oracle SYSDATE expiration
    merge_query = text("""
       MERGE INTO USER_PASS_OTP_T tgt
        USING (SELECT :mobile AS MOBILE_NO, :email as EMAIL, :otp AS OTP_CODE FROM DUAL) src
        ON (tgt.MOBILE_NO = src.MOBILE_NO)
        WHEN MATCHED THEN 
            UPDATE SET tgt.OTP_CODE = src.OTP_CODE, tgt.OTP_EXPIRY = SYSTIMESTAMP + INTERVAL '1' MINUTE
        WHEN NOT MATCHED THEN 
            INSERT (MOBILE_NO ,EMAIL, OTP_CODE, OTP_EXPIRY) 
            VALUES (src.MOBILE_NO , src.EMAIL, src.OTP_CODE, SYSTIMESTAMP + INTERVAL '1' MINUTE)
        """)
    
    try:
        db.execute(merge_query, {"email" : payload.email ,"mobile": payload.mobile, "otp": otp_code})
        db.commit()
        logger.info(f"OTP generated and stored for: {payload.mobile}")
        
        # 4. Offload the SMTP request to the background so the API returns instantly
        # background_tasks.add_task(send_otp_email, payload.email ,otp_code)
        send_otp_email(payload.email, otp_code)
        return {"status": "success", "message": "Email sent successfully!"}
        
        
    except Exception as e:
        db.rollback()
        logger.error(f"DB Error while generating OTP for {payload.email}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
    # return {"status": "success", "message": "If that email is registered, an OTP has been sent." ,"otp" : otp_code}


@router.post("/verify-otp-and-reset")
def verify_and_reset(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    
    # 1. Verify OTP validity and expiration directly via Oracle SYSDATE
    verify_query = text("""
        SELECT 1 FROM USER_PASS_OTP_T 
        WHERE MOBILE_NO = :mobile 
          AND OTP_CODE = :otp 
          AND OTP_EXPIRY > SYSTIMESTAMP
    """)
    
    is_valid = db.execute(verify_query, {"mobile": payload.mobile, "otp": payload.otp_code}).fetchone()
    
    if not is_valid:
        logger.warning(f"Failed OTP reset attempt for: {payload.email}")
        raise HTTPException(status_code=400, detail="Invalid or expired OTP.")

    # 2. Hash the newly provided password
    # hashed_password = get_context.hash(payload.new_password)

    # 3. Update the password and clear the used OTP atomically
    update_pwd_query = text("UPDATE MMH_USERREGDATA SET PASSWORD = :password WHERE MOB = :mobile")
    delete_otp_query = text("DELETE FROM USER_PASS_OTP_T WHERE MOBILE_NO = :mobile")
    
    try:
        db.execute(update_pwd_query, {"password": payload.new_password , "mobile": payload.mobile})
        db.execute(delete_otp_query, {"mobile": payload.mobile})
        db.commit()
        logger.info(f"Password successfully reset for: {payload.mobile}")
    except Exception as e:
        db.rollback()
        logger.error(f"DB Error during password reset for {payload.mobile}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"status": "success", "message": "Password reset successfully. You can now log in."}
    
    
    
    
      
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
