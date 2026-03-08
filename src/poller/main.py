from fastapi import FastAPI, Query
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
import requests
import urllib.parse
import os
import boto3
import json

from ..common.db import SessionLocal
from .auth import (
    exchange_code_for_tokens,
    save_tokens,
    get_valid_access_token,
    get_or_create_new_user,
)

load_dotenv()

sqs = boto3.client(
    "sqs",
    endpoint_url="http://localhost:4566",
    region_name="ap-southeast-2",
    aws_access_key_id="test",
    aws_secret_access_key="test",
)

res = sqs.create_queue(QueueName="recent-songs-queue")
queue_url = res["QueueUrl"]
print(f"Queue created: {queue_url}")

app = FastAPI(
    title="Spotify Poller",
    description="Service to poll the spotify api and push events to queue",
)


@app.get("/")
def read_root():
    return {"status": "online", "service": "poller"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/login")
def login():
    scope = "user-read-recently-played user-read-currently-playing"
    params = {
        "client_id": os.environ.get("SPOTIFY_CLIENT_ID"),
        "response_type": "code",
        "redirect_uri": os.environ.get("SPOTIFY_CALLBACK_URL"),
        "scope": scope,
    }

    url = f"https://accounts.spotify.com/authorize?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url)


@app.get("/callback")
def callback(code: str = Query(...)):
    data = exchange_code_for_tokens(code)

    token = data.get("access_token")
    if not token:
        return {"error": "No access_token returned", "spotify_response": data}

    user_id = get_or_create_new_user(token)

    save_tokens(
        user_id=user_id,
        access_token=token,
        refresh_token=data.get("refresh_token"),
        expires_in=data.get("expires_in"),
    )

    return RedirectResponse(url=f"/recent-songs?user_id={user_id}")


@app.get("/recent-songs")
def recent_songs(user_id: int = Query(...)):
    access_token = get_valid_access_token(user_id)

    headers = {"Authorization": f"Bearer {access_token}"}
    url = "https://api.spotify.com/v1/me/player/recently-played?limit=50"

    res = requests.get(url, headers=headers)
    process_songs(res.json(), user_id)

    return res.json()


def process_songs(songs: dict, user_id: int):
    for item in songs.get("items", []):
        track = item.get("track", {})
        album = track.get("album", {})

        artist_names = ", ".join(
            artist.get("name")
            for artist in track.get("artists", [])
            if artist.get("name")
        )

        message_body = {
            "user_id": user_id,
            "track_id": track.get("id"),
            "track_name": track.get("name"),
            "artist": artist_names,
            "album": album.get("name"),
            "image_url": (
                album.get("images", [{}])[0].get("url") if album.get("images") else None
            ),
            "duration_ms": track.get("duration_ms"),
            "popularity": track.get("popularity"),
            "played_at": item.get("played_at"),
        }

        print(f"Sending to sqs: {json.dumps(message_body)}")

        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message_body),
        )

    print("Sent songs to sqs")
