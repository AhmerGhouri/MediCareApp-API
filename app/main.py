import logging
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.db.oracle import SessionLocal
from app.routers import auth_router, health_router, patient_router
from apscheduler.schedulers.background import BackgroundScheduler
from app.services.notifier import check_and_notify_new_reports
from app.services.appointment_notifier import check_and_send_appointment_reminders



# Initialize standard Python logging (Gunicorn/Systemd will catch this automatically)
logger = logging.getLogger("hospital_api_logger")
logger.setLevel(logging.ERROR)

app = FastAPI(title="Hospital Patient API")
app.include_router(health_router.router, tags=["health"])


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
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred on the server. Please try again later."
        },
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    codes = {400: "INVALID_REQUEST", 401: "AUTHENTICATION_REQUIRED",
             403: "ACCESS_DENIED", 404: "NOT_FOUND", 409: "CONFLICT",
             422: "VALIDATION_ERROR", 429: "RATE_LIMITED",
             500: "INTERNAL_ERROR", 503: "SERVICE_UNAVAILABLE"}
    detail = exc.detail if isinstance(exc.detail, dict) else {}
    message = detail.get("message") if detail else exc.detail
    if not isinstance(message, str):
        message = "Unable to complete this request."
    if exc.status_code >= 500 and not detail:
        message = "The service is temporarily unavailable. Please try again later."
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={
            "success": False,
            "error_type": "HTTPException",
            "code": detail.get("code", codes.get(exc.status_code, "REQUEST_FAILED")),
            "message": message,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Do not echo Pydantic input/context, which may contain credentials or PHI.
    fields = {"mobile_number", "mobile", "email", "password", "new_password",
              "otp", "otp_code", "full_name", "date_of_birth", "gender",
              "opat_id", "consl_id", "appoint_date", "device_token", "platform"}
    errors = {}
    for error in exc.errors():
        loc = error.get("loc", ())
        field = loc[-1] if loc else None
        if isinstance(field, str) and field in fields:
            errors[field] = "Please check this field."
    return JSONResponse(
        status_code=422,
        content={"success": False, "error_type": "ValidationError",
                 "code": "VALIDATION_ERROR", "message": "The data provided is invalid.",
                 "errors": errors},
    )


# Include the routes we are about to create
app.include_router(auth_router.router, prefix="/auth", tags=["Authentication"])
app.include_router(patient_router.router, prefix="/patients", tags=["Patient Data"])

@app.get("/")
def read_root():
    return {"message": "Hospital API is running"}
