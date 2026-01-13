from typing import Union
from fastapi.responses import RedirectResponse
from fastapi import FastAPI

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
    # params = {
    #     "client_id": settings.spotify_client_id,

    # }
    url = f"https://google.com"
    return RedirectResponse(url)
