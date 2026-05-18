import boto3
import json
import time
import os
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError, OperationalError
from ..common.db import SessionLocal
from ..common.models import Track, ListeningHistory

load_dotenv()

sqs = boto3.client(
    "sqs",
    region_name="ap-southeast-2",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_ACCESS_SECRET_KEY"),
)

# queue_url = sqs.get_queue_url(QueueName="recent-songs-queue")["QueueUrl"]
queue_url = "https://sqs.ap-southeast-2.amazonaws.com/555379836133/spotify-queue"


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

            db = SessionLocal()
            try:
                # Upsert Track (update + insert track if it doesnt exist)
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
                    track_name=body["track_name"],
                    artist=body["artist"],
                    user_id=body.get("user_id", 1),  # fallback to user_id = 1
                    played_at=body["played_at"],
                )
                db.add(history)
                db.commit()
                print(f"Saved: {body['track_name']} by {body['artist']}")

                # Delete message after processing
                sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=message["ReceiptHandle"],
                )

            except IntegrityError:
                db.rollback()
                print(
                    f"Duplicate track, skipped: {body['track_name']} at {body['played_at']}"
                )

                # delete duplicates so they dont need to reprocessed
                sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=message["ReceiptHandle"],
                )
            except OperationalError as e:
                db.rollback()
                print(f"DB connection error: {e}")
                print("Skipping rest of batch — messages will be retried")
                break
            except Exception as e:
                db.rollback()
                print(f"DB error: {e}")
            finally:
                db.close()

        time.sleep(1)


if __name__ == "__main__":
    consume()
