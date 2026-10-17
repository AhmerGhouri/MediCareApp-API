import logging
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.db.oracle import SessionLocal
from app.routers import auth_router, health_router, patient_router, web_router
from apscheduler.schedulers.background import BackgroundScheduler
from app.services.notifier import check_and_notify_new_reports
from app.services.appointment_notifier import check_and_send_appointment_reminders



# Initialize standard Python logging (Gunicorn/Systemd will catch this automatically)
logger = logging.getLogger("hospital_api_logger")
logger.setLevel(logging.ERROR)

app = FastAPI(title="Hospital Patient API")


def scheduled_report_check():
    db = SessionLocal()
    try:
        check_and_notify_new_reports(db)
    except Exception as e:
        logger.error(f"Scheduled job failed: {str(e)}")
    finally:
        db.close()

def scheduled_appointment_reminder_check():
    db = SessionLocal()
    try:
        check_and_send_appointment_reminders(db)
    except Exception as e:
        logger.error(f"Appointment reminder job failed: {str(e)}")
    finally:
        db.close()

scheduler = BackgroundScheduler()

scheduler.add_job(
    scheduled_appointment_reminder_check,
    "interval",
    minutes=15,
    id="appointment_reminder_job",
    max_instances=1
)

scheduler.add_job(scheduled_report_check, "interval", minutes=5, id="report_notify_job", max_instances=1)
scheduler.start()

# --- 2. Global Exception Handlers ---

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log the crash for systemd
    logger.error(f"CRITICAL ERROR on {request.method} {request.url.path}: {exc}")
    logger.error(traceback.format_exc())

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error_type": "InternalServerError",
            "message": "An unexpected error occurred on the server. Our team has been notified."
        },
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_type": "HTTPException",
            "message": exc.detail
        },
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error_type": "ValidationError",
            "message": "The data provided is invalid.",
            "details": exc.errors()
        },
    )

# Include the routes we are about to create
app.include_router(auth_router.router, prefix="/auth", tags=["Authentication"])
app.include_router(patient_router.router, prefix="/patients", tags=["Patient Data"])
app.include_router(web_router.router, prefix="/web", tags=["Web"])
app.include_router(health_router.router, tags=["health"])


@app.get("/")
def read_root():
    return {"message": "Hospital API is running"}