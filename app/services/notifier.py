# app/services/notifier.py
from datetime import datetime
from sqlalchemy import text
from app.services.push_service import send_bulk_push
from app.logger import logger


def check_and_notify_new_reports(db):
    # STEP A: acquire the lock (blocks if another instance is mid-run)
    try:
        lock_row = db.execute(
            text("SELECT LOCK_NAME FROM NOTIFICATION_JOB_LOCK_T WHERE LOCK_NAME = 'report_notifier' FOR UPDATE")
        ).fetchone()
        if not lock_row:
            logger.error("Notifier: lock row missing — did you run the setup SQL?")
            db.rollback()
            return
    except Exception as e:
        logger.error(f"Notifier: failed to acquire lock: {str(e)}")
        db.rollback()
        return

    try:
        _run_notification_batch(db)
        db.execute(
            text("UPDATE NOTIFICATION_JOB_LOCK_T SET LAST_RUN_AT = SYSTIMESTAMP WHERE LOCK_NAME = 'report_notifier'")
        )
        db.commit()  # releases the lock
    except Exception as e:
        db.rollback()  # releases the lock even on failure
        logger.error(f"Notifier: batch failed, rolled back: {str(e)}")


def _run_notification_batch(db):
    # STEP B: find reports not yet in the log, bounded to a recent window
    # so we're not scanning the entire history of a huge legacy table every run
    query = text("""
        SELECT
            D.LTESTD_UNIQUE_ID,
            M.LTESTM_OPAT_ID,
            O.OPAT_PHONE,
            O.OPAT_PNAME
        FROM aass.LTESTD_T D
        JOIN aass.LTESTM_T M ON M.LTESTM_ID = D.LTESTD_LTESTM_ID
        JOIN aass.OPAT_T O ON O.OPAT_ID = M.LTESTM_OPAT_ID
        WHERE D.LTESTD_STATUS IN (3, 4)
          AND D.LTESTD_RESULT_DATE >= SYSDATE - 1   -- only look back 24h, bounds the scan
          AND NOT EXISTS (
              SELECT 1 FROM aass.NOTIFICATION_LOG_T N
              WHERE N.LTESTD_UNIQUE_ID = D.LTESTD_UNIQUE_ID
          )
    """)
    rows = db.execute(query).mappings().all()
    if not rows:
        return

    logger.info(f"Notifier: {len(rows)} new report(s) to notify")

    # STEP C: batch-fetch device tokens for all affected patients in ONE query,
    # instead of one query per report (avoids N+1)
    phones = tuple({row["opat_phone"] for row in rows if row["opat_phone"]})
    tokens_by_phone = {}
    if phones:
        token_rows = db.execute(
            text("SELECT MOB, DEVICE_TOKEN FROM USER_DEVICES_T WHERE MOB IN :phones"),
            {"phones": phones}
        ).fetchall()
        for t in token_rows:
            tokens_by_phone.setdefault(t.MOB, []).append(t.DEVICE_TOKEN)

    # STEP D: build the full list of (token, message) pairs and send as one batch
    messages = []
    for row in rows:
        for token in tokens_by_phone.get(row["opat_phone"], []):
            messages.append({
                "token": token,
                "title": "Lab Report Ready",
                "body": f"Hi {row['opat_pname']}, your latest lab results are ready to view.",
                "data": {"report_id": str(row["ltestd_unique_id"]), "screen": "ReportDetails"},
            })

    if messages:
        dead_tokens = send_bulk_push(messages)
        if dead_tokens:
            db.execute(
                text("DELETE FROM USER_DEVICES_T WHERE DEVICE_TOKEN IN :tokens"),
                {"tokens": tuple(dead_tokens)}
            )

    # STEP E: log every report as notified, even ones with zero devices,
    # so we never re-scan them again
    for row in rows:
        try:
            db.execute(
                text("INSERT INTO NOTIFICATION_LOG_T (LTESTD_UNIQUE_ID) VALUES (:id)"),
                {"id": row["ltestd_unique_id"]}
            )
        except Exception:
            # UNIQUE constraint hit = already logged by a concurrent path, safe to skip
            pass