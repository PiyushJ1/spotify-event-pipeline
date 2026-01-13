from typing import Union

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
