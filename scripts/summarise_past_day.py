import os
import sys
from typing import List
from collections import Counter
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.orm import joinedload

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.common.db import SessionLocal
from src.common.models import ListeningHistory, User
from src.poller.handler import _send_sns_email


def main():
    db = SessionLocal()

    try:
        users: List[User] = db.query(User).all()

        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        for user in users:
            history = db.scalars(
                select(ListeningHistory)
                .options(joinedload(ListeningHistory.track))
                .where(
                    ListeningHistory.user_id == user.id,
                    ListeningHistory.played_at >= cutoff,
                )
                .order_by(ListeningHistory.played_at.desc())
            ).all()

            unique_artists = set()
            artist_counter = Counter()
            track_counter = Counter()

            total_seconds = 0
            listening_history = []

            for play in history:
                duration_seconds = play.track.duration_ms / 1000
                total_seconds += duration_seconds

                # handle multi-artist tracks
                artists = [artist.strip() for artist in str(play.artist).split(",")]

                for artist in artists:
                    unique_artists.add(artist)
                    artist_counter[artist] += 1

                track_counter[play.track_name] += 1

                listening_history.append(
                    {
                        "song_name": play.track_name,
                        "artist": play.artist,
                        "album": play.track.album,
                        "duration_in_seconds": duration_seconds,
                        "played_at": play.played_at.isoformat(),
                    }
                )

            payload = {
                "date": datetime.now(timezone.utc).date().isoformat(),
                "user": {
                    "id": user.id,
                    "display_name": user.display_name,
                },
                "summary": {
                    "total_tracks": len(history),
                    "total_minutes": round(total_seconds / 60),
                    "unique_artist_count": len(unique_artists),
                    "top_artists": [
                        {
                            "artist": artist,
                            "plays": plays,
                        }
                        for artist, plays in artist_counter.most_common(5)
                    ],
                    "top_tracks": [
                        {
                            "song": song,
                            "plays": plays,
                        }
                        for song, plays in track_counter.most_common(5)
                    ],
                },
                "listening_history": listening_history,
            }

            print(payload)
            _send_sns_email(payload)

    finally:
        db.close()


if __name__ == "__main__":
    main()
