from typing import Union
from fastapi.responses import RedirectResponse
from fastapi import FastAPI
import urllib.parse
import os

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


# handle OAuth2 and user Spotify login
@app.get("/login")
def login():
    scope = "user-read-recently-played user-read-currently-playing"
    params = {
        "client_id": os.environ.get("SPOTIFY_CLIENT_ID"),
        "response_type": "code",
        "redirect_url": os.environ.get("SPOTIFY_REDIRECT_URL"),
        "scope": scope,
    }
    url = f"https://accounts.spotify.com/authorize?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url)


# @app.get("/callback")
