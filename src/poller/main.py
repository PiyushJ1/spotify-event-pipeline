from typing import Union
from fastapi.responses import RedirectResponse
import base64
from fastapi import FastAPI, Query
from dotenv import load_dotenv
import requests
import urllib.parse
import os
import secrets

load_dotenv()

request_access_token_url = "https://accounts.spotify.com/api/token"

# init app
app = FastAPI(
    title="Spotify Poller",
    description="Service to poll the spotify api and push events to queue",
)


# define a basic route
@app.get("/")
def read_root():
    return {"status": "online", "service": "poller"}


# health check for AWS services
@app.get("/health")
def health_check():
    return {"status": "healthy"}


# handle OAuth2 user Spotify login
@app.get("/login")
def login():
    scope = "user-read-recently-played user-read-currently-playing"
    # state = secrets.token_urlsafe(12)  # for security purposes

    params = {
        "client_id": os.environ.get("SPOTIFY_CLIENT_ID"),
        "response_type": "code",
        "redirect_uri": os.environ.get("SPOTIFY_CALLBACK_URL"),
        "scope": scope,
        # "state": state,
    }

    url = f"https://accounts.spotify.com/authorize?{urllib.parse.urlencode(params)}"

    print(url)
    return RedirectResponse(url)


@app.get("/callback")
def callback(code: str = Query(...)):
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    redirect_uri = os.environ.get("SPOTIFY_CALLBACK_URL")

    payload = {
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    encoded = base64.b64encode(
        (client_id + ":" + client_secret).encode("utf-8")
    ).decode("utf-8")

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": "Basic " + encoded,
    }

    res = requests.post(request_access_token_url, headers=headers, data=payload)

    data = res.json()

    # recent_songs(data["access_token"])

    token = data["access_token"]

    # return {
    #     "access_token": data["access_token"],
    #     "refresh_token": data["refresh_token"],
    #     "expires_in": data["expires_in"],
    # }

    # TODO IMPORTANT: save the info to db

    return RedirectResponse(url=f"/recent-songs?access_token={token}")


@app.get("/recent-songs")
def recent_songs(access_token: str):
    headers = {"Authorization": "Bearer " + access_token}

    url = "https://api.spotify.com/v1/me/player/recently-played"

    res = requests.get(url, headers=headers)

    return res.json()
