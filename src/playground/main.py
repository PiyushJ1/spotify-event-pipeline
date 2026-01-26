import boto3
import requests
import os
from dotenv import load_dotenv
import requests
import base64

load_dotenv()

client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
spotify_api_url = "https://accounts.spotify.com/api/token"

def get_auth_token():
    encoded = base64.b64encode((client_id + ":" + client_secret).encode("utf-8")).decode("utf-8")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": "Basic " + encoded
    }

    payload = {
        "grant_type": "client_credentials",
    }

    response = requests.post(spotify_api_url, headers=headers, data=payload)

    print(response.text)

get_auth_token()