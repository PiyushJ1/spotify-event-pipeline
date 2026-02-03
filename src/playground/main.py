import boto3
import requests
import os
from dotenv import load_dotenv
import json
import base64
from sqlalchemy.orm import Session
from ..common.db import engine, SessionLocal, Base
from ..common.models import SimpleSong

load_dotenv()

client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
spotify_api_url = "https://accounts.spotify.com/api/token"
spotify_artist_url = "https://api.spotify.com/v1/artists"
QUEUE_NAME = "sample-queue"
_access_token = None

artist_uri = "1RyvyyTE3xzB2ZywiAwp0i" # future

sqs = boto3.client(
    "sqs",
    endpoint_url="http://localhost:4566",
    region_name="ap-southeast-2",
    aws_access_key_id="test",
    aws_secret_access_key="test",
)

response = sqs.create_queue(QueueName=QUEUE_NAME)
queue_url = response["QueueUrl"]
print(f"Queue created: {queue_url}")


def process_message(track_num: int):
    # send message into queue
    travis_top_track = get_artist_top_tracks(track_num)
    sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(travis_top_track))
    print("message sent")

    # process message
    response = sqs.receive_message(
        QueueUrl=queue_url, MaxNumberOfMessages=1, WaitTimeSeconds=2
    )

    if "Messages" not in response:
        print("No messages in queue")
        return
    message = response["Messages"][0]
    # print(f"received message: {message['Body']}")
    body = json.loads(message["Body"])

    db = SessionLocal()

    try:
        exists = db.query(SimpleSong).filter_by(spotify_id=body["spotify_id"]).first()
        if not exists:
            new_track = SimpleSong(
                name=body["name"], artist=body["artist"], spotify_id=body["spotify_id"]
            )
            db.add(new_track)
            db.commit()
            print("--- song saved to db! ---")
        else:
            print("=== song already exists in the db ===")
    except Exception as e:
        print(f"error in db: {e}")
    finally:
        db.close()

    sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"])

    print("message deleted\n")


def get_access_token():
    encoded = base64.b64encode(
        (client_id + ":" + client_secret).encode("utf-8")
    ).decode("utf-8")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": "Basic " + encoded,
    }

    payload = {
        "grant_type": "client_credentials",
    }

    res = requests.post(spotify_api_url, headers=headers, data=payload)

    return res.json()["access_token"]


def get_artist_top_tracks(track_num: int):
    global _access_token
    if _access_token is None:
        _access_token = get_access_token()

    headers = {"Authorization": "Bearer " + _access_token}

    res = requests.get(
        f"{spotify_artist_url}/{artist_uri}/top-tracks", headers=headers
    )

    track_data = res.json()["tracks"][track_num]

    return {
        "spotify_id": track_data["id"],
        "name": track_data["name"],
        "artist": track_data["artists"][0]["name"],
    }


i = 0
while i < 10:
    process_message(i)
    i += 1
