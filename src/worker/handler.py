import os
import json
import logging
from typing import List, Dict

from sqlalchemy.exc import IntegrityError, OperationalError

from ..common.db import SessionLocal
from ..common.models import Track, ListeningHistory


"""
- Lambda triggered when messages arrive in SQS
- Reads the messages from the queue, writing any new events to Neon
"""


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker.handler")


def _process_record(body: Dict):
    db = SessionLocal()
    try:
        # Upsert Track
        existing = db.query(Track).filter_by(id=body["track_id"]).first()
        if not existing:
            track = Track(
                id=body["track_id"],
                name=body["track_name"],
                artist=body.get("artist"),
                album=body.get("album"),
                image_url=body.get("image_url"),
                duration_ms=body.get("duration_ms"),
                popularity=body.get("popularity"),
            )
            db.add(track)

        history = ListeningHistory(
            track_id=body["track_id"],
            user_id=body.get("user_id", 1),
            played_at=body["played_at"],
        )
        db.add(history)
        db.commit()
        logger.info("Saved: %s by %s", body.get("track_name"), body.get("artist"))
    except IntegrityError:
        # duplicate play event (idempotency) - treat as processed and delete message
        db.rollback()
        logger.info(
            "Duplicate track, skipped: %s at %s",
            body.get("track_name"),
            body.get("played_at"),
        )
    except OperationalError as e:
        db.rollback()
        logger.exception("DB operational error: %s", e)
        # Re-raise so Lambda/SQS can retry the batch
        raise
    except Exception as e:
        db.rollback()
        logger.exception("DB error processing record: %s", e)
        raise
    finally:
        db.close()


def handler(event, context):
    """SQS-triggered Lambda handler.

    Expects `event` to be the AWS Lambda SQS event structure:
    {"Records": [{"body": "...json..."}, ...]}
    """
    records = event.get("Records", [])
    processed = 0
    for r in records:
        try:
            body = json.loads(r.get("body", "{}"))
        except json.JSONDecodeError:
            logger.warning("Skipping record with invalid JSON")
            continue

        try:
            _process_record(body)
            processed += 1
        except Exception:
            # Let the exception bubble so Lambda/SQS can retry or send to DLQ
            logger.exception("Failed processing record, rethrowing to trigger retry")
            raise

    return {"status": "ok", "processed": processed}
