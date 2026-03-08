import base64
import os
import time
import requests

from ..common.db import SessionLocal
from ..common.models import AuthToken, User

SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"


def get_spotify_auth_headers() -> dict:
    """Basic auth header for Spotify token requests."""
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    encoded = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    return {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/x-www-form-urlencoded",
    }


def exchange_code_for_tokens(code: str) -> dict:
    """Exchange an authorization code for access + refresh tokens."""
    res = requests.post(
        SPOTIFY_TOKEN_URL,
        headers=get_spotify_auth_headers(),
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": os.environ.get("SPOTIFY_CALLBACK_URL"),
        },
    )

    return res.json()


def save_tokens(user_id: int, access_token: str, refresh_token: str, expires_in: int):
    """Insert or update auth tokens for a user."""
    db = SessionLocal()
    try:
        auth = db.query(AuthToken).filter_by(user_id=user_id).first()
        if auth:
            auth.access_token = access_token
            if refresh_token:
                auth.refresh_token = refresh_token
            auth.expires_at = int(time.time()) + expires_in
        else:
            auth = AuthToken(
                user_id=user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=int(time.time()) + expires_in,
            )
            db.add(auth)
        db.commit()
        print(f"Saved tokens for user_id={user_id}")
    except Exception as err:
        db.rollback()
        print(f"Error saving auth tokens: {err}")
        raise
    finally:
        db.close()


def refresh_access_token(user_id: int) -> str:
    """Use the refresh token to get a new access token."""
    db = SessionLocal()
    try:
        auth = db.query(AuthToken).filter_by(user_id=user_id).first()
        if not auth or not auth.refresh_token:
            raise ValueError(f"No refresh token found for user_id={user_id}")

        res = requests.post(
            SPOTIFY_TOKEN_URL,
            headers=get_spotify_auth_headers(),
            data={
                "grant_type": "refresh_token",
                "refresh_token": auth.refresh_token,
            },
        )
        res.raise_for_status()
        data = res.json()

        save_tokens(
            user_id=user_id,
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", auth.refresh_token),
            expires_in=data.get("expires_in", 3600),
        )

        return data["access_token"]
    finally:
        db.close()


def get_valid_access_token(user_id: int) -> str:
    """Return a valid access token, refreshing if expired or expiring within 5 min."""
    db = SessionLocal()
    try:
        auth = db.query(AuthToken).filter_by(user_id=user_id).first()
        if not auth:
            raise ValueError(f"No auth record for user_id={user_id}. Login first.")

        if time.time() >= auth.expires_at - 300:
            return refresh_access_token(user_id)

        return auth.access_token
    finally:
        db.close()


def get_or_create_new_user(access_token: str):
    res = requests.get(
        "https://api.spotify.com/v1/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    user_profile = res.json()

    spotify_user_id = user_profile["id"]
    display_name = user_profile["display_name"]

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(spotify_user_id=spotify_user_id).first()

        if not user:
            user = User(spotify_user_id=spotify_user_id, display_name=display_name)
            db.add(user)
            db.commit()
            print(f"Created new user, id: {spotify_user_id}, name: {display_name}")

        return user.id
    finally:
        db.close()
