from sqlalchemy.exc import DBAPIError
from oracle import SessionLocal  # Adjust import to your project

def execute_with_retry(operation):
    """
    Executes a database operation and retries once if the connection
    was invalidated.
    """

    db = SessionLocal()

    try:
        return operation(db)

    except DBAPIError as e:
        if getattr(e, "connection_invalidated", False):
            print("Database connection was invalidated. Retrying once...")

            try:
                db.rollback()
            except Exception:
                pass

            db.close()

            db = SessionLocal()

            return operation(db)

        raise

    finally:
        db.close()
