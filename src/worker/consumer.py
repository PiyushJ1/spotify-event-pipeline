import boto3
import json
import time
from sqlalchemy.exc import IntegrityError
from ..common.db import SessionLocal
from ..common.models import Track, ListeningHistory

sqs = boto3.client(
    "sqs",
    endpoint_url="http://localhost:4566",
    region_name="ap-southeast-2",
    aws_access_key_id="test",
    aws_secret_access_key="test",
)

queue_url = sqs.get_queue_url(QueueName="recent-songs-queue")["QueueUrl"]


def consume():
    print("Consumer starting...")

    while True:
        res = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=5,
        )

        if "Messages" not in res:
            print("No messages in queue")
            continue

        for message in res["Messages"]:
            body = json.loads(message["Body"])
            print(f"Consumed: {body['track_name']} by {body['artist']}")

            db = SessionLocal()
            try:
                # Upsert Track (insert if not exists)
                existing_track = db.query(Track).filter_by(id=body["track_id"]).first()
                if not existing_track:
                    track = Track(
                        id=body["track_id"],
                        name=body["track_name"],
                        artist=body["artist"],
                        album=body["album"],
                        image_url=body["image_url"],
                        duration_ms=body["duration_ms"],
                        popularity=body["popularity"],
                    )
                    db.add(track)

                # Insert ListeningHistory
                history = ListeningHistory(
                    track_id=body["track_id"],
                    played_at=body["played_at"],
                )
                db.add(history)
                db.commit()
                print(f"Saved: {body['track_name']}")

                # Delete message after processing
                sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=message["ReceiptHandle"],
                )

            except IntegrityError:
                db.rollback()
                print(
                    f"Duplicate, skipping: {body['track_name']} at {body['played_at']}"
                )

                # delete duplicates so they dont need to reprocessed
                sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=message["ReceiptHandle"],
                )
            except Exception as e:
                db.rollback()
                print(f"DB error: {e}")
            finally:
                db.close()

        time.sleep(1)

    exit(1)


consume()
