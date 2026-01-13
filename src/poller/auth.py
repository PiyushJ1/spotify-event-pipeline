import time
import requests
from requests.auth import HTTPBasicAuth


class SpotifyAuth:
    def __init__(self, db: Session):
        self.db = db
        self.token_url = "https://accounts.spotify.com/api/token"

    def get_valid_token(self):
        token_record = self.db.query(SpotifyToken).filter_by(user_id="me").first()

        if not token_record:
            return None
