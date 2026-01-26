import boto3
import requests
import os
from dotenv import load_dotenv
import json
import base64

load_dotenv()

client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
spotify_api_url = "https://accounts.spotify.com/api/token"
spotify_artist_url = "https://api.spotify.com/v1/artists"


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


def get_artist_info():
    access_token = get_access_token()
    headers = {"Authorization": "Bearer " + access_token}

    res = requests.get(f"{spotify_artist_url}/2HPaUgqeutzr3jx5a9WyDV", headers=headers)

    # print(json.dumps(res.json(), indent=2))

get_artist_info()
