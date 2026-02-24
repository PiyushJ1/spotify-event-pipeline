from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.common.db import Base


# simple song table to play around with
class SimpleSong(Base):
    __tablename__ = "simple_songs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    artist = Column(String, nullable=False)

    # prevent duplicates (idempotency)
    spotify_id = Column(String, unique=True)


# user info table
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    spotify_user_id = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    auth_token = relationship("AuthToken", back_populates="user", uselist=False)


# spotify OAuth2 token
class AuthToken(Base):
    __tablename__ = "auth_tokens"

    id = Column(Integer, primary_key=True)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=False)
    expires_at = Column(Integer, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship(
        "User",
    )


# proper full details for a track
class Track(Base):
    __tablename__ = "tracks"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    artist = Column(String, nullable=False)
    album = Column(String)

    image_url = Column(String)
    duration_ms = Column(String)
    popularity = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# stores ALL songs played by user
class ListeningHistory(Base):
    __tablename__ = "listening_history"

    id = Column(String, primary_key=True, index=True)
    track_id = Column(String, ForeignKey("tracks.id"), nullable=False)
    played_at = Column(DateTime(timezone=True), nullable=False)

    ingested_at = Column(DateTime(timezone=True), server_default=func.now())

    track = relationship("Track")  # link the tables

    # idempotency (prevent duplicate track events from being stored)
    __table_args__ = (
        UniqueConstraint("track_id", "played_at", name="uix_track_played_at"),
    )
