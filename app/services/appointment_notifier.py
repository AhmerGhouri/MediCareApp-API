from sqlalchemy import text
from app.services.push_service import send_bulk_push
from app.logger import logger


def check_and_send_appointment_reminders(db):
    # Acquire this job's own lock row — independent from the report notifier's lock
    try:
        lock_row = db.execute(
            text("SELECT LOCK_NAME FROM NOTIFICATION_JOB_LOCK_T WHERE LOCK_NAME = 'appointment_reminder' FOR UPDATE")
        ).fetchone()
        if not lock_row:
            logger.error("Appointment reminder: lock row missing — run the setup SQL.")
            db.rollback()
            return
    except Exception as e:
        logger.error(f"Appointment reminder: failed to acquire lock: {str(e)}")
        db.rollback()
        return

    try:
        _send_reminders(db, reminder_type="TWO_HOUR")
        _send_reminders(db, reminder_type="DAY_BEFORE")
        db.execute(
            text("UPDATE NOTIFICATION_JOB_LOCK_T SET LAST_RUN_AT = SYSTIMESTAMP WHERE LOCK_NAME = 'appointment_reminder'")
        )
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Appointment reminder: batch failed, rolled back: {str(e)}")


def _send_reminders(db, reminder_type: str):
    if reminder_type == "TWO_HOUR":
        # Appointment start time falls within the next 2 hours from now
        window_clause = """
            TO_DATE(S.APP_DATE || ' ' || D.TIME_IN, 'DD/MON/YYYY HH24:MI')
                BETWEEN SYSDATE AND SYSDATE + (2/24)
        """
        body_template = "Reminder: your appointment with {consl} is in about 2 hours, at {time} today."
    elif reminder_type == "DAY_BEFORE":
        # Appointment date is tomorrow (matches all day, dedup log prevents resend)
        window_clause = "TRUNC(TO_DATE(S.APP_DATE, 'DD/MON/YYYY')) = TRUNC(SYSDATE + 1)"
        body_template = "Reminder: you have an appointment tomorrow with {consl} at {time}."
    else:
        raise ValueError(f"Unknown reminder_type: {reminder_type}")

    query = text(f"""
        SELECT
            S.CONSL_TRAN_ID,
            S.APP_DATE,
            D.TIME_IN,
            D.PAT_MR,
            D.PAT_CELL,
            D.PAT_NAME,
            TRIM(C.CONSL_DESC) AS CONSL_DESC
        FROM aass.CONSL_APP_T S
        JOIN aass.CONSL_APPD_T D ON D.TRAN_ID = S.CONSL_TRAN_ID
        JOIN aass.CONSL_T C ON C.CONSL_ID = S.CONSL_ID
        WHERE S.CONSL_STATUS <> 'C'
          AND D.PAT_MR IS NOT NULL
          AND {window_clause}
          AND NOT EXISTS (
              SELECT 1 FROM APPOINTMENT_REMINDER_LOG_T L
              WHERE L.CONSL_TRAN_ID = S.CONSL_TRAN_ID
                AND L.REMINDER_TYPE = :reminder_type
          )
    """)

    rows = db.execute(query, {"reminder_type": reminder_type}).mappings().all()
    if not rows:
        return

    logger.info(f"Appointment reminder ({reminder_type}): {len(rows)} appointment(s) to notify")

    # Batch device token lookup — same pattern as the report notifier
    phones = tuple({row["pat_cell"] for row in rows if row["pat_cell"]})
    tokens_by_phone = {}
    if phones:
        token_rows = db.execute(
            text("SELECT MOB, DEVICE_TOKEN FROM aass.USER_DEVICES_T WHERE MOB IN :phones"),
            {"phones": phones}
        ).fetchall()
        for t in token_rows:
            tokens_by_phone.setdefault(t.MOB, []).append(t.DEVICE_TOKEN)

    messages = []
    for row in rows:
        for token in tokens_by_phone.get(row["pat_cell"], []):
            messages.append({
                "token": token,
                "title": "Appointment Reminder",
                "body": body_template.format(consl=row["consl_desc"], time=row["time_in"]),
                "data": {
                    "tran_id": str(row["consl_tran_id"]),
                    "screen": "AppointmentDetails",
                },
            })

    if messages:
        dead_tokens = send_bulk_push(messages)
        if dead_tokens:
            db.execute(
                text("DELETE FROM aass.USER_DEVICES_T WHERE DEVICE_TOKEN IN :tokens"),
                {"tokens": tuple(dead_tokens)}
            )

    for row in rows:
        try:
            db.execute(
                text("""
                    INSERT INTO aass.APPOINTMENT_REMINDER_LOG_T (CONSL_TRAN_ID, REMINDER_TYPE)
                    VALUES (:tran_id, :reminder_type)
                """),
                {"tran_id": row["consl_tran_id"], "reminder_type": reminder_type}
            )
        except Exception:
            pass  # UNIQUE constraint hit = already logged concurrently, safe to skip