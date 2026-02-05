from sqlalchemy import Column, Integer, String, DateTime
from src.common.db import Base


# simple song table to play around with
class SimpleSong(Base):
    __tablename__ = "simple_songs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    artist = Column(String, nullable=False)

    # prevent duplicates (idempotency)
    spotify_id = Column(String, unique=True)


# spotify OAuth2 token
class AuthToken(Base):
    __tablename__ == "auth_tokens"

    id = Column(Integer, primary_key=True)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=False)
    expires_at = Column(Integer, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# proper full details for a track
class Track(Base):
    __tablename__ == "tracks"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    artist = Column(String, nullable=False)
    album = Column(String)

    image_url = Column(String)
    duration_ms = Column(String)
    popularity = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
