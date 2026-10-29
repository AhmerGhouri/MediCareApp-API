import re
import time
from collections import defaultdict
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError   # SQLAlchemy wraps driver errors, so import it from here, not oracledb
from sqlalchemy.orm import Session
from app.db.oracle import get_db
from app.deps import require_agent_key       # API key check (X-API-Key header)
from app.logger import logger
from app.models.schemas import AgentAppointmentBooking

# Every route in this router requires the agent API key.
router = APIRouter(dependencies=[Depends(require_agent_key)])

# IMPORTANT: "PAT_MR IS NULL" is what marks a slot as FREE. The GET filters on it and the
# booking UPDATE checks it. If the caller has no MR number, PAT_MR must still receive a
# value, otherwise the booked slot would still look free and could be booked twice.
# Confirm with reception what their system expects for callers without an MR number.
NO_MR_PLACEHOLDER = "VOICE"





def _parse_date(value: str):
    value = value.strip()
    for fmt in ("%d-%b-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise HTTPException(
        status_code=400,
        detail="Invalid date format. Use DD-MON-YYYY (e.g. 27-JUN-2026) or YYYY-MM-DD."
    )


@router.get("/{consl_id}/{app_date}/appointments")
def get_appointments(consl_id: str, app_date: str, db: Session = Depends(get_db)):

    query = text("""SELECT
                        E.TIME_FR,
                        E.TIME_TO,
                        E.TIME_DAYS,
                        E.TIME_DATE,
                        E.TIME_CONSL_ID,
                        A.CONSLD_ID,
                        A.APPD_DATE,
                        A.TIME_IN,
                        A.PAT_MR,
                        TRIM(C.CONSL_DESC) CONSL_DESC,
                        E.TIME_CONSL_DEPT,
                        TRIM(D.MDEPT_DESC) MDEPT_DESC
                    FROM 
                        aass.TIMING_T E,
                        aass.CONSL_T C,
                        aass.MDEPT_T D,
                        aass.CONSL_APPD_T A
                    WHERE
                        E.TIME_CONSL_DEPT = D.MDEPT_ID
                    AND 
                        C.CONSL_ID = E.TIME_CONSL_ID
                    AND 
                        C.CONSL_ID = '50054'
                    AND
                        C.CONSL_ID = A.CONSLD_ID
                    AND
                        A.APPD_DATE = '30-OCT-2026'
                    AND
                        A.APPD_DAY = E.TIME_DAYS
                    AND
                      (
                        (
                          A.APPD_DATE = TO_CHAR(SYSDATE, 'DD/MON/YYYY')
                          OR
                          A.APPD_DATE > TO_CHAR(SYSDATE, 'DD/MON/YYYY')
                          ) 
                        AND 
                        A.TIME_IN >= TO_CHAR(SYSDATE, 'HH24:MI')
                      )                               
                    AND
                        A.PAT_MR IS NULL
                    GROUP BY  
                        E.TIME_CONSL_DEPT,
                        E.TIME_FR,
                        E.TIME_TO,
                        E.TIME_DAYS,
                        E.TIME_DATE,
                        E.TIME_CONSL_ID,
                        C.CONSL_DESC,
                        A.CONSLD_ID,
                        A.APPD_DATE,
                        A.TIME_IN,
                        A.APPD_DATE,
                        A.PAT_MR,
                        E.TIME_CONSL_DEPT,
                        D.MDEPT_DESC
                        ORDER BY TIME_IN ASC 
                    """)

    result_rows = db.execute(query, {"consl_id": consl_id, "app_date": app_date}).mappings().all()

    if not result_rows:
        raise HTTPException(status_code=403, detail="No free appointment slots found for this doctor and date")

    first_row = result_rows[0]

    grouped_appointments = defaultdict(list)

    for row in result_rows:
        key = (row["time_days"], row["time_date"])
        grouped_appointments[key].append({
            "time_fr": row["time_fr"],
            "time_to": row["time_to"],
            "time_slot": row["time_in"]
        })

    return {
        "consl_id": first_row["time_consl_id"],
        "consl_name": first_row["consl_desc"],
        "dept_id": first_row["time_consl_dept"],
        "Dept": first_row["mdept_desc"],
        "appointments": [
            {
                "time_days": day,
                "time_date": str(app_dt),
                "time_slot": slots
            }
            for (day, app_dt), slots in grouped_appointments.items()
        ]
    }


@router.post("/{consl_id}/createappointment")
def create_appointment(
    consl_id: str,
    appointment: AgentAppointmentBooking,
    db: Session = Depends(get_db)
):
    parsed_date = _parse_date(appointment.appoint_date)

    # Whatever MR number the agent sends is stored as given. If none was sent, use the placeholder.
    # (Oracle treats an empty string as NULL, so blanks must be replaced too.)
    mr_value = (appointment.opat_id or "").strip() or NO_MR_PLACEHOLDER

    query_parent = text("""
        INSERT INTO aass.CONSL_APP_T (
            CONSL_TRAN_ID, CONSL_ID, APP_DATE, APP_FR_TIME, APP_TO_TIME, CONSL_DAYS
        ) VALUES (
            :tran_id, :consl_id, :appoint_date, :from_time, :to_time, :appointment_day
        )
    """)

    query_child = text("""
        UPDATE aass.CONSL_APPD_T
        SET
            PAT_MR = :opat_id,
            TRAN_ID = :tran_id,
            PAT_CELL = :mobile_number,
            PAT_NAME = :patient_name,
            TIME_STATUS = 1
        WHERE
            CONSLD_ID = :consl_id
        AND
            APPD_DATE = :appoint_date
        AND
            TIME_IN = :appoint_time
        AND
            PAT_MR IS NULL  -- CRITICAL: atomic check protects against double-booking
    """)

    max_attempts = 5
    attempt = 0
    generated_trans_id = None

    while attempt < max_attempts:
        try:
            # NOTE: same schema-prefix handling as the rest of your queries may be needed here.
            current_max = db.execute(text("SELECT COALESCE(MAX(CONSL_TRAN_ID), 0) FROM aass.CONSL_APP_T")).scalar()
            generated_trans_id = current_max + 1

            parameters = {
                "tran_id": generated_trans_id,
                "opat_id": mr_value,
                "consl_id": consl_id,
                "appoint_date": parsed_date,
                "mobile_number": appointment.mobile_number,   # may be None
                "from_time": appointment.from_time,
                "to_time": appointment.to_time,
                "appointment_day": appointment.appointment_day,
                "appoint_time": appointment.appoint_time,
                "patient_name": appointment.patient_name
            }

            db.execute(query_parent, parameters)
            child_result = db.execute(query_child, parameters)

            if child_result.rowcount == 0:
                db.rollback()
                raise HTTPException(
                    status_code=409,
                    detail="This appointment slot is no longer available. It may have just been booked by another patient."
                )

            db.commit()
            logger.info(f"Agent booking created: tran_id={generated_trans_id}")
            break

        except IntegrityError:
            db.rollback()
            attempt += 1
            time.sleep(0.05)
            if attempt >= max_attempts:
                logger.error("Agent booking: transaction collision limit reached")
                raise HTTPException(status_code=409, detail="Could not complete the booking. Please try again.")

        except HTTPException:
            raise

        except Exception:
            db.rollback()
            logger.exception("Agent booking failed")   # full detail goes to the log only
            raise HTTPException(status_code=500, detail="Unable to complete the booking.")

    return {
        "status": "success",
        "message": "Appointment booked and slot allocated successfully.",
        "generated_id": generated_trans_id
    }