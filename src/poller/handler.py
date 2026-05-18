import os
import json
import logging
from typing import Dict, List

import requests
import boto3
from botocore.exceptions import ClientError

from ..common.db import SessionLocal
from ..common.models import User
from .auth import get_valid_access_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("poller.handler")


"""
- The polling lambda which is triggered by EventBridge at intervals.
- Fetches recent tracks from the Spotify API and sends them to SQS.
"""


def _get_sqs_client():
    region = os.environ.get("AWS_REGION", "ap-southeast-2")
    aws_key = os.environ.get("AWS_ACCESS_KEY_ID")
    aws_secret = os.environ.get("AWS_ACCESS_SECRET_KEY")

    params = {"region_name": region}
    if aws_key and aws_secret:
        params["aws_access_key_id"] = aws_key
        params["aws_secret_access_key"] = aws_secret

    return boto3.client("sqs", **params)


def _get_queue_url(sqs) -> str:
    # Prefer explicit URL in environment for production
    url = os.getenv("SQS_QUEUE_URL")
    if url:
        return url

    queue_name = os.environ.get("SQS_QUEUE_NAME", "recent-songs-queue")
    try:
        res = sqs.get_queue_url(QueueName=queue_name)
        return res["QueueUrl"]
    except ClientError as e:
        if (
            e.response.get("Error", {}).get("Code")
            == "AWS.SimpleQueueService.NonExistentQueue"
        ):
            logger.info("Queue not found, creating %s", queue_name)
            res = sqs.create_queue(QueueName=queue_name)
            return res["QueueUrl"]
        raise


def _message_from_item(item: Dict, user_id: int) -> Dict:
    track = item.get("track", {})
    album = track.get("album", {})

    artist_names = ", ".join(
        artist.get("name") for artist in track.get("artists", []) if artist.get("name")
    )

    return {
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


def handler(event, context):
    """Lambda-style handler to poll Spotify for all users and push events to SQS.

    Environment variables used:
    - SQS_QUEUE_URL or SQS_QUEUE_NAME
    - AWS_REGION (optional)
    """
    sqs = _get_sqs_client()
    queue_url = os.getenv("SQS_QUEUE_URL")

    db = SessionLocal()
    try:
        users: List[User] = db.query(User).all()
    finally:
        db.close()

    total_sent = 0
    per_user = {}

    for u in users:
        user_id = u.id
        try:
            access_token = get_valid_access_token(user_id)
        except Exception as e:
            logger.warning("Skipping user %s: cannot get access token: %s", user_id, e)
            continue

        headers = {"Authorization": f"Bearer {access_token}"}
        url = "https://api.spotify.com/v1/me/player/recently-played?limit=50"

        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            logger.warning("Spotify request failed for user %s: %s", user_id, e)
            continue

        data = resp.json()
        items = data.get("items", [])
        sent = 0

        for item in items:
            message = _message_from_item(item, user_id)
            try:
                sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message))
                sent += 1
            except Exception as e:
                logger.exception(
                    "Failed sending message to SQS for user %s: %s", user_id, e
                )

        total_sent += sent
        per_user[str(user_id)] = sent
        logger.info("User %s: sent %d messages", user_id, sent)

    return {"status": "ok", "total_sent": total_sent, "per_user": per_user}
