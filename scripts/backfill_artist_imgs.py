#!/usr/bin/env python3

import psycopg2, os, sys
import requests, time
from psycopg2.extras import execute_values

# ensure repo root is on sys.path so `src` is importable
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.poller.auth import get_valid_access_token

db = None


def main():
    db = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = db.cursor()

    cur.execute("select id from artists;")
    ids = cur.fetchall()

    access_token = get_valid_access_token(1)
    headers = {"Authorization": f"Bearer {access_token}"}

    artists = []
    for i, id in enumerate(ids):
        id = id[0]
        res = requests.get(f"https://api.spotify.com/v1/artists/{id}", headers=headers)

        img_url = res.json()["images"][0]["url"]
        print(i, id, img_url)

        cur.execute(
            """
            update artists
            set image_url = %s
            where id = %s
            """,
            [img_url, id],
        )

        db.commit()

        time.sleep(1)

    db.commit()


if __name__ == "__main__":
    main()
