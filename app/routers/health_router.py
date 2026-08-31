# app/routers/health_router.py
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.oracle import get_db

router = APIRouter()

@router.get("/health/notifier")
def notifier_health(db: Session = Depends(get_db)):
    row = db.execute(
        text("SELECT LAST_RUN_AT FROM aass.NOTIFICATION_JOB_LOCK_T WHERE LOCK_NAME = 'report_notifier'")
    ).fetchone()

    if not row or row.LAST_RUN_AT is None:
        return {"status": "never_run", "last_run_at": None}

    last_run = row.LAST_RUN_AT
    age = datetime.now() - last_run
    # If it's been more than ~3x the scheduler interval since the last run, flag it as stale
    is_healthy = age < timedelta(minutes=15)

    return {
        "status": "healthy" if is_healthy else "stale",
        "last_run_at": last_run.isoformat(),
        "seconds_since_last_run": int(age.total_seconds())
    }