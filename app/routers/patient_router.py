# app/routers/patient_router.py
import base64
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.oracle import get_db
from app.deps import get_current_user
from app.models.models import AppUser, HospitalPatient
# from app.models.schemas import ConsultantOut

router = APIRouter()

@router.get("/{opat_id}/reports")
def get_dashboard(opat_id: str, db: Session = Depends(get_db), current_user: AppUser = Depends(get_current_user)):
    
    # SECURITY CHECK: Verify that the logged-in user actually owns this MR Number!
    # patient_record = db.query(HospitalPatient).filter(
    #     HospitalPatient.opat_id == opat_id,
    #     HospitalPatient.opat_phone == current_user.mob
    # ).first()
    
    
    # TODO: Perform your Oracle queries here to get today's clinic, etc. using mr_no
    
    
    query = text("""SELECT 
                        M.LTESTM_ID,
                        M.LTESTM_SYS_DATE,
                        M.LTESTM_OPAT_ID,
                        D.LTESTD_LTESTM_ID, 
                        TRIM(D.LTESTD_LTEST_ID) AS  LTESTD_LTEST_ID,
                        D.LTESTD_RESULT_DATE,
                        D.LTESTD_STATUS, 
                        L.LTEST_ID, 
                        TRIM(L.LTEST_DESC) AS LTEST_DESC,
                        O.OPAT_ID,
                        O.OPAT_PNAME,
                        O.OPAT_PHONE
                    FROM 
                        LTESTM_T M, 
                        LTESTD_T D, 
                        LTEST_T L, 
                        OPAT_T O
                    WHERE 
                        M.LTESTM_OPAT_ID = O.OPAT_ID
                    AND 
                        M.LTESTM_ID = D.LTESTD_LTESTM_ID
                    AND 
                        O.OPAT_ID = :opat_id
                    AND 
                        D.LTESTD_LTEST_ID = L.LTEST_ID
                    AND 
                        O.OPAT_PHONE = :mobile_number""")
    
    
    # .mappings() makes it easy to access columns by their names
    result_rows = db.execute(query, {"opat_id": opat_id, "mobile_number": current_user.mob}).mappings().all()
    
    if not result_rows:
        raise HTTPException(status_code=403, detail="No Report found for this MR Number")
    
    # Since the patient details (name, id) are the same in every row, 
    # we take them from the first row.
    first_row = result_rows[0]
    
    return {
        "opat_id" : first_row["opat_id"],
        "patient_name" : first_row["opat_pname"],
        "mobile" : first_row["opat_phone"],
        "reports" : [
            {
                "test_id": row["ltest_id"],
                "testm_id": row["ltestd_ltestm_id"],
                "testd_id": row["ltestd_ltest_id"],
                "test_desc": row["ltest_desc"],
                "test_date": row["ltestd_result_date"],
                "status": row["ltestd_status"]
            } for row in result_rows
        ]
    }
  
  
# @router.get("/{opat_id}/radiology")
# def get_dashboard(opat_id: str, db: Session = Depends(get_db), current_user: AppUser = Depends(get_current_user)):
        
    
#     query = text("""SELECT
#                         M.BILLM_OPAT_ID , 
#                         M.BILLM_ID,
#                         TRIM(M.BILLM_NAME) AS BILLM_NAME ,
#                         TRIM(M.BILLM_SYS_DATE) AS BILLM_SYS_DATE, 
#                         TRIM(M.BILLM_SER_DEPT) AS BILLM_SER_DEPT , 
#                         TRIM(M.BILLM_SSUBDEPT_ID) AS BILLM_SSUBDEPT_ID ,
#                         M.BILLM_CELL_NO ,
#                         TRIM(D.BILLD_SDETAIL_COM_ID) AS BILLD_SDETAIL_COM_ID , 
#                         TRIM(S.SDETAIL_DESC) AS SDETAIL_DESC , 
#                         O.OPAT_PHONE
#                     FROM 
#                         BILLM_T M , BILLD_T D , SDETAIL_T S, OPAT_T O
#                     WHERE 
#                         M.BILLM_SER_DEPT = 'XR'
#                     AND 
#                         M.BILLM_OPAT_ID = :opat_id
#                     AND 
#                         M.BILLM_OPAT_ID = O.OPAT_ID
#                     AND 
#                         D.BILLD_SCLASS_ID NOT IN 'CM'
#                     AND 
#                         D.BILLD_SDETAIL_COM_ID = S.SDETAIL_COM_ID
#                     AND 
#                         M.BILLM_SER_DEPT = D.BILLD_SER_DEPT
#                     AND 
#                         M.BILLM_ID = D.BILLD_BILLM_ID 
#                     """)
    
    
#     # .mappings() makes it easy to access columns by their names
#     result_rows = db.execute(query, {"opat_id": opat_id, "mobile_number": current_user.mob}).mappings().all()
    
#     if not result_rows:
#         raise HTTPException(status_code=403, detail="No Radiology Report found for this MR Number")
    
#     # Since the patient details (name, id) are the same in every row, 
#     # we take them from the first row.
#     first_row = result_rows[0]
        
#     return {
#         "opat_id" : first_row["billm_opat_id"],
#         "patient_name" : first_row["billm_name"],
#         "mobile" : first_row["opat_phone"],
#         "reports" : [
#             {
#                 "test_id": row["billm_id"],
#                 "test_desc": row["sdetail_desc"],
#                 "test_date": row["billm_sys_date"],
#                 "billm_id": row["billd_sdetail_com_id"]
#             } for row in result_rows
#         ]
#     }
    
    
  
@router.get("/{opat_id}/radiology")
def get_dashboard(opat_id: str, db: Session = Depends(get_db), current_user: AppUser = Depends(get_current_user)):
        
    
    query = text("""SELECT DISTINCT
                        T.REPTM_NO,
                        T.REPTM_BILLM_ID,
                        TRIM(T.DEPT_DESC) DEPT_DESC,
                        TRIM(T.SDETAIL_DESC) SDETAIL_DESC,
                        T.BILLM_SEX,
                        T.REPTM_PAT_ID,
                        T.REPTM_OPAT_ID,
                        T.PAT_NAME,
                        (SELECT O.OPAT_PHONE FROM OPAT_T O WHERE LTRIM(RTRIM(O.OPAT_ID)) = LTRIM(RTRIM(REPTM_OPAT_ID))) PHONE_NO,
                        T.PANEL_NAME,
                        T.BILLM_REF_CONSL_ID,
                        TRIM((SELECT C.CONSL_DESC FROM CONSL_T C WHERE LTRIM(RTRIM(C.CONSL_ID)) = LTRIM(RTRIM(T.BILLM_REF_CONSL_ID)))) REPORT_REF_BY_CONSL,
                        T.BILLM_SYS_DATE,
                        DECODE(T.BILLM_SEX,'M','MALE','F','FEMALE')billm_gender,
                        T.REPTM_NO,
                        REPTM_CONSL_ID REPORT_CREATED_BY_CONSL_ID,
                        TRIM((SELECT C.CONSL_DESC FROM CONSL_T C WHERE LTRIM(RTRIM(C.CONSL_ID)) = LTRIM(RTRIM(REPTM_CONSL_ID)))) REPORT_CREATED_BY_CONSL,
                        (SELECT C.CONSL_DEGR FROM CONSL_T C WHERE LTRIM(RTRIM(C.CONSL_ID)) = LTRIM(RTRIM(REPTM_CONSL_ID))) CONSL_DEGR,
                        (SELECT A.spec_desc FROM CONSL_T C, spec_t A WHERE C.CONSL_SPEC_ID = A.SPEC_ID AND LTRIM(RTRIM(C.CONSL_ID)) = LTRIM(RTRIM(REPTM_CONSL_ID))) CONSL_DESIG,
                        DECODE(T.reptm_pat_type,'I','In-Patient','O','Out_patient','W','Walk-In','M','Miscellenous',T.reptm_pat_type) REPTM_PAT_TYPE,
                        DECODE(T.reptm_status,'1','Not Approved','2','Cancel','3','Approved',T.reptm_status) REPTM_STATUS,
                        --T.REPTD_STATUS,
                        T.BILLM_SYS_DATE REQ_DATE,
                        T.REPTM_ENTRY_DATE REPORTING_DATE
                    FROM 
                        RADIOLOGY_REPT_VIEW T
                    WHERE 
                        (SUBSTR(T.reptm_no, 1, 2)) = (SUBSTR(T.reptm_no, 1, 2))
                    AND 
                        T.REPTM_OPAT_ID = :opat_id
                     """)
    
    
    # .mappings() makes it easy to access columns by their names
    result_rows = db.execute(query, {"opat_id": opat_id, "mobile_number": current_user.mob}).mappings().all()
    
    if not result_rows:
        raise HTTPException(status_code=403, detail="No Radiology Report found for this MR Number")
    
    # Since the patient details (name, id) are the same in every row, 
    # we take them from the first row.
    first_row = result_rows[0]
    
    # return result_rows
        
    return {
        "opat_id" : first_row["reptm_opat_id"],
        "patient_name" : first_row["pat_name"],
        "mobile" : first_row["phone_no"],
        "reports" : [
            {
                "test_id": row["reptm_billm_id"],
                "test_desc": row["sdetail_desc"],
                "test_dept_desc" : row["dept_desc"],
                "test_req_date": row["req_date"],
                "reprting_date": row["reporting_date"],
                "test_refer_by" : row["report_ref_by_consl"],
                "test_done_by" : row["report_created_by_consl"],
                "report_status" : row["reptm_status"]
                # "billm_id": row["billd_sdetail_com_id"]
            } for row in result_rows
        ]
    }
    
    
@router.get("/{opat_id}/inpatienthistory")
def get_dashboard(opat_id: str, db: Session = Depends(get_db), current_user: AppUser = Depends(get_current_user)):
        
    
    query = text("""SELECT 
                        I.IPAT_ID , 
                        I.IPAT_OPAT_ID , 
                        I.IPAT_ADATE , 
                        I.IPAT_DDATE , 
                        I.IPAT_CONSL_ID , 
                        TRIM(C.CONSL_DESC) AS CONSL_DESC , 
                        I.IPAT_A_DIAG_ID , 
                        TRIM(D.DIAG_DESC) AS DIAG_DESC , 
                        I.IPAT_MDEPT_ID,
                        I.IPAT_SPOUSE_PHONE 
                    FROM 
                        IPAT_T I , 
                        DIAG_T D , 
                        CONSL_T C
                    WHERE 
                        I.IPAT_OPAT_ID  = :opat_id
                    AND 
                        I.IPAT_CONSL_ID = C.CONSL_ID
                    AND 
                        I.IPAT_A_DIAG_ID = D.DIAG_ID 
                    """)
    
    
    # .mappings() makes it easy to access columns by their names
    result_rows = db.execute(query, {"opat_id": opat_id, "mobile_number": current_user.mob}).mappings().all()
    
    if not result_rows:
        raise HTTPException(status_code=403, detail="No Report found for this MR Number")
    
    # Since the patient details (name, id) are the same in every row, 
    # we take them from the first row.
    first_row = result_rows[0]
        
    return {
        "opat_id" : first_row["ipat_opat_id"],
        "patient_name" : first_row["ipat_opat_id"],
        "mobile" : first_row["ipat_spouse_phone"],
        "inpatienthistory" : [
            {
                "test_id": row["ipat_id"],
                "consultation": row["consl_desc"],
                "diagnosis": row["diag_desc"],
                "adm_date": row["ipat_adate"],
                "dis_date": row["ipat_ddate"],
                "dept_id": row["ipat_mdept_id"]
            } for row in result_rows
        ]
    }
    
@router.get("/{opat_id}/consultationhistory")
def get_dashboard(opat_id: str, db: Session = Depends(get_db), current_user: AppUser = Depends(get_current_user)):
        
    
    query = text("""SELECT 
                        M.BILLM_ID , 
                        M.BILLM_SER_DATE , 
                        M.BILLM_OPAT_ID , 
                        TRIM(M.BILLM_NAME) AS BILLM_NAME , 
                        TRIM(M.BILLM_CELL_NO) AS BILLM_CELL_NO , 
                        TRIM(C.CONSL_DESC) AS CONSL_DESC , 
                        TRIM(M.BILLM_MDEPT_ID) AS BILLM_MDEPT_ID , 
                        M.BILLM_AMT
                    FROM 
                        BILLM_T M , 
                        CONSL_T C
                    WHERE 
                        M.BILLM_OPAT_ID = :opat_id
                    AND 
                        M.BILLM_SER_DEPT <> 'BL'
                    --AND M.BILLM_SER_DEPT = 'MC'
                    AND 
                        M.BILLM_CONSL_ID = C.CONSL_ID
                    """)
    
    
    # .mappings() makes it easy to access columns by their names
    result_rows = db.execute(query, {"opat_id": opat_id, "mobile_number": current_user.mob}).mappings().all()
    
    if not result_rows:
        raise HTTPException(status_code=403, detail="No CONSULTATIONS Report found for this MR Number")
    
    # Since the patient details (name, id) are the same in every row, 
    # we take them from the first row.
    first_row = result_rows[0]
            
    return {
        "opat_id" : first_row["billm_opat_id"],
        "patient_name" : first_row["billm_name"],
        "mobile" : first_row["billm_cell_no"],
        "consultationshistory" : [
            {
                "test_id": row["billm_id"],
                "consultation": row["consl_desc"],
                "ser_date": row["billm_ser_date"],
                "dept_id": row["billm_mdept_id"],
                "amount": row["billm_amt"],
                
            } for row in result_rows
        ]
    }
    
    
@router.get("/{opat_id}/upcomingappointments")
def get_dashboard(opat_id: str, db: Session = Depends(get_db), current_user: AppUser = Depends(get_current_user)):
        
    
    query = text("""SELECT
                        S.CONSL_TRAN_ID,
                        APP_DATE,
                        TIME_IN ,
                        TRIM(S.CONSL_ID) AS CONSL_ID,
                        TRIM(CN.CONSL_DESC) AS CONSL_DESC,
                        M.MDEPT_ID,
                        TRIM(M.MDEPT_DESC) AS MDEPT_DESC,
                        D.PAT_MR,
                        TRIM(D.PAT_CELL) AS PAT_CELL,
                        TRIM(D.PAT_TITLE||' '|| D.PAT_NAME) AS PAT_NAME
                    FROM
                        CONSL_APP_T S,
                        CONSL_APPD_T D,
                        CONSL_T CN,
                        MDEPT_T M
                    WHERE
                        D.TRAN_ID = S.CONSL_TRAN_ID
                    AND
                        S.CONSL_ID = CN.CONSL_ID
                    AND
                        D.PAT_MR = :opat_id
                    AND
                        M.MDEPT_ID = CN.CONSL_MDEPT_ID
                    AND
                        S.CONSL_STATUS <> 'C'
                    """)
    
    
    # .mappings() makes it easy to access columns by their names
    result_rows = db.execute(query, {"opat_id": opat_id, "mobile_number": current_user.mob}).mappings().all()
    
    if not result_rows:
        raise HTTPException(status_code=403, detail="No Upcoming Appointments found for this MR Number")
    
    # Since the patient details (name, id) are the same in every row, 
    # we take them from the first row.
    first_row = result_rows[0]
        
    return {
        "opat_id" : first_row["pat_mr"],
        "patient_name" : first_row["pat_name"],
        "mobile" : first_row["pat_cell"],
        "appointments" : [
            {
                "trans_id": row["consl_tran_id"],
                "consultant": row["consl_desc"],
                "app_date": row["app_date"],
                "time_in": row["time_in"],
                "dept_id": row["mdept_id"],
                "dept": row["mdept_desc"],
                
            } for row in result_rows
        ]
    }
    
    
    
@router.get("/todaysclinic")
def get_dashboard(db: Session = Depends(get_db)):
        
    query = text(""" SELECT
                        TO_CHAR(TO_DATE(E.TIME_FR, 'HH24:MI'), 'HH12:MI AM') AS TIME_FR_12,
                        TO_CHAR(TO_DATE(E.TIME_TO, 'HH24:MI'), 'HH12:MI AM') AS TIME_TO_12,
                        TRIM(E.TIME_DAYS) AS TIME_DAYS,
                        E.TIME_DATE,
                        TRIM(E.TIME_CONSL_ID) AS TIME_CONSL_ID,
                        TRIM(C.CONSL_DESC) AS CONSL_DESC,
                        TRIM(E.TIME_CONSL_DEPT) AS TIME_CONSL_DEPT,
                        TRIM(D.MDEPT_DESC) AS MDEPT_DESC,
                        E.ROSTER_STATUS,
                        TO_CHAR(SYSDATE, 'YYYY-MM-DD') AS CURRENT_DATE_VAL,
                        UPPER(TO_CHAR(SYSDATE, 'Day')) AS CURRENT_DAY_VAL
                    FROM 
                        TIMING_T E,
                        CONSL_T C,
                        MDEPT_T D
                    WHERE 
                        E.TIME_CONSL_DEPT = D.MDEPT_ID
                    AND 
                        C.CONSL_ID = E.TIME_CONSL_ID
                    AND
                        TRIM(UPPER(TO_CHAR(SYSDATE, 'Day'))) IN TRIM(E.TIME_DAYS)
                        -- AND C.CONSL_ID = '50533'
                        --AND D.MDEPT_ID = 'NEPH'
                    GROUP BY 
                        E.TIME_CONSL_DEPT,
                        E.TIME_FR,
                        E.TIME_TO,
                        E.TIME_DAYS,
                        E.TIME_DATE,
                        E.TIME_CONSL_ID,
                        C.CONSL_DESC,
                        E.TIME_CONSL_DEPT,
                        D.MDEPT_DESC,
                        E.ROSTER_STATUS,
                        SYSDATE,
                        TO_CHAR(SYSDATE, 'Day')
                    """)
    
    
    # .mappings() makes it easy to access columns by their names
    result_rows = db.execute(query).mappings().all()
    
    if not result_rows:
        raise HTTPException(status_code=403, detail="No Clinics found for today")
    
    # we take them from the first row.
    first_row = result_rows[0]
    
    # return result_rows
    
    return {
        "day" : first_row["current_day_val"],
        "current_date" : first_row["current_date_val"],
        "consultations" : [
            {
                "consl_id": row["time_consl_id"],
                "consultant": row["consl_desc"],
                "from": row["time_fr_12"],
                "to": row["time_to_12"],
                "dept_id": row["time_consl_dept"],
                "dept": row["mdept_desc"],
                "scheduled_days": row["time_days"],
                
            } for row in result_rows
        ]
    }
    
    
    
    
@router.get("/consultants" )
def get_dashboard(db: Session = Depends(get_db)):
        
    
    query = text("""SELECT 
                        TRIM(E.CONSL_ID) AS CONSL_ID , 
                        TRIM(E.CONSL_DESC) AS CONSL_DESC , 
                        TRIM(E.CONSL_DEGR) AS CONSL_DEGR , 
                        TRIM(E.CONSL_SPEC_ID) AS CONSL_SPEC_ID , 
                        E.CONSL_STATUS , 
                        TRIM(E.CONSL_MDEPT_ID) AS CONSL_MDEPT_ID , 
                        TRIM(D.MDEPT_DESC) AS MDEPT_DESC,
                        E.CONSL_IMG
                    FROM 
                        CONSL_T E , MDEPT_T D
                    WHERE 
                        E.CONSL_STATUS = 1
                    AND
                        E.CONSL_MDEPT_ID = D.MDEPT_ID
                    AND
                        E.CONSL_MDEPT_ID NOT IN ('ANES' , 'ALLD' , 'EMER' , 'RADI' , '5000' , 'SONO' , 'MHH' , 'JMCH' , 'ER' , 'CASU' , 'NA' , 'HE')
                    AND 
                        E.CONSL_SPEC_ID NOT IN ('TECH' , 'ALL')
                    ORDER BY 
                        D.MDEPT_DESC,
                        E.CONSL_DESC
                    """)
    
    
    # .mappings() makes it easy to access columns by their names
    result_rows = db.execute(query).mappings().all()
    
    if not result_rows:
        raise HTTPException(status_code=403, detail="No Upcoming Appointments found for this MR Number")

    
    clean_data = []
    for row in result_rows:
        row_dict = {}
        for key, value in row.items():
            # If value is raw bytes (like the image or a binary id), convert to string safely
            if isinstance(value, bytes):
                try:
                    row_dict[key] = value.decode('utf-8')
                except UnicodeDecodeError:
                    # If it's image data or encrypted bytes, encode as base64 string
                    row_dict[key] = base64.b64encode(value).decode('utf-8')
            else:
                row_dict[key] = value
        clean_data.append(row_dict)
        
    # JSONResponse bypasses FastAPI's internal serialisation pipeline
    return JSONResponse(content=clean_data)

    # return {
    #     "opat_id" : first_row["pat_mr"],
    #     "patient_name" : first_row["pat_name"],
    #     "mobile" : first_row["pat_cell"],
    #     "appointments" : [
    #         {
    #             "trans_id": row["consl_tran_id"],
    #             "consultant": row["consl_desc"],
    #             "app_date": row["app_date"],
    #             "time_in": row["time_in"],
    #             "dept_id": row["mdept_id"],
    #             "dept": row["mdept_desc"],
                
    #         } for row in result_rows
    #     ]
    # }
    
