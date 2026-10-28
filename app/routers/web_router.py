# app/routers/web_router.py
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.oracle import get_db
from app.models.schemas import ClinicAppointmentRequest
from app.logger import logger

router = APIRouter()
TURNSTILE_SECRET = os.getenv("TURNSTILE_SECRET_KEY")

def verify_turnstile(token: str, ip: str) -> bool:
    try:
        r = httpx.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={"secret": TURNSTILE_SECRET, "response": token, "remoteip": ip},
            timeout=5,
        )
        return r.json().get("success", False)
    except Exception as e:
        logger.error(f"Turnstile verification error: {e}")
        return False

@router.post("/appointment-request", status_code=201)
def create_appointment_request(
    payload: ClinicAppointmentRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    # Honeypot: bots fill hidden fields. Pretend success, store nothing.
    if payload.website:
        logger.error(f"DEBUG appointment: dropped by honeypot, value={payload.website!r}")
        return {"success": True, "message": "Request received."}

    client_ip = request.headers.get("x-real-ip") or request.client.host
    if not verify_turnstile(payload.captcha_token, client_ip):
        logger.error(f"DEBUG appointment: captcha failed")
        raise HTTPException(status_code=400, detail="Verification failed. Please try again.")

    # Duplicate guard: same phone + same date already pending
    dup = db.execute(
        text("""SELECT 1 FROM aass.clinic_appointment_requests
                WHERE phone_number = :phone AND preferred_date = :pdate AND status = 'Pending'"""),
        {"phone": payload.phone_number, "pdate": payload.preferred_date},
    ).fetchone()
    if dup:
        logger.error(f"DEBUG appointment: skipped as duplicate")
        return {"success": True, "message": "Request received."}

    try:
        db.execute(
            text("""INSERT INTO aass.clinic_appointment_requests
                    (full_name, phone_number, specialty, doctor_name, preferred_date)
                    VALUES (:name, :phone, :spec, :doctor, :pdate)"""),
            {"name": payload.full_name, "phone": payload.phone_number,
             "spec": payload.specialty, "doctor": payload.doctor_name,
             "pdate": payload.preferred_date },
        )
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Appointment request insert failed: {e}")
        raise HTTPException(status_code=500, detail="Unable to submit request.")

    return {"success": True, "message": "Request received. We will contact you shortly."}
