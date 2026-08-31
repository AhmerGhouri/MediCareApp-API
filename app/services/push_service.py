# app/services/push_service.py
import os
import firebase_admin
from firebase_admin import credentials, messaging
from ..logger import logger

cred_path = os.getenv(
    "FIREBASE_CREDENTIALS_PATH",
    "medicare-mobile-app-49d52-firebase-adminsdk-fbsvc-8124045db9.json"
)

if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)


def send_bulk_push(messages: list[dict]) -> list[str]:
    """
    messages: list of {"token", "title", "body", "data"}
    Returns list of device tokens that are dead and should be removed.
    """
    dead_tokens = []

    # FCM caps batches at 500 messages
    for i in range(0, len(messages), 500):
        chunk = messages[i:i + 500]
        fcm_messages = [
            messaging.Message(
                notification=messaging.Notification(title=m["title"], body=m["body"]),
                data={k: str(v) for k, v in m.get("data", {}).items()},
                token=m["token"],
            )
            for m in chunk
        ]

        try:
            response = messaging.send_each(fcm_messages)
        except Exception as e:
            logger.error(f"Bulk push send failed entirely: {str(e)}")
            continue

        for msg, result in zip(chunk, response.responses):
            if not result.success:
                err = result.exception
                logger.warning(f"Push failed for ...{msg['token'][-6:]}: {err}")
                if isinstance(err, messaging.UnregisteredError):
                    dead_tokens.append(msg["token"])

        logger.info(f"Bulk push: {response.success_count}/{len(chunk)} sent")

    return dead_tokens


def send_topic_notification(topic: str, title: str, body: str, data_payload: dict = None):
    """For promotional / broadcast notifications."""
    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        data={k: str(v) for k, v in (data_payload or {}).items()},
        topic=topic,
    )
    try:
        return messaging.send(message)
    except Exception as e:
        logger.error(f"Topic push failed: {str(e)}")
        return None
