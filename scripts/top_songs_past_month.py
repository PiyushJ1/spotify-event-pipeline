#!/usr/bin/env python3

import psycopg2, os, sys
from datetime import datetime


DATABASE_URL = os.getenv("DATABASE_URL")

db = None


def main():
    cur = db.cursor()  # type: ignore

    current_month = f"{datetime.now().year}-{datetime.now().month}-1"

    cur.execute(
        "select track_name, listening_history.artist, count(*), image_url from listening_history join tracks on tracks.id = listening_history.track_id "
        "where played_at >= %s group by track_name, listening_history.artist, image_url order by count(*) desc limit 10;",
        [current_month],
    )
    songs = cur.fetchall()

    for track, artist, plays, img in songs:
        print(f"Song: {track}, by: {artist}. Played {plays} times, {img}")


def _send_email():
    pass


if __name__ == "__main__":
    try:
        db = psycopg2.connect(DATABASE_URL)
        main()
    except psycopg2.Error as err:
        print("DB Error: ", err)
    except Exception as err:
        print("Internal Error: ", err)
        raise err
    finally:
        if db is not None:
            db.close()
    sys.exit(0)
