from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from sqlalchemy.sql import func
from src.common.db import Base


# simple song table to play around with
class SimpleSong(Base):
    __tablename__ = "simple_songs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str]
    artist: Mapped[str]

    # prevent duplicates (idempotency)
    spotify_id: Mapped[str] = mapped_column(unique=True)


# user info table
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    spotify_user_id: Mapped[str] = mapped_column(unique=True, index=True)
    display_name: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    auth_token: Mapped["AuthToken"] = relationship(back_populates="user", uselist=False)


# spotify OAuth2 token
class AuthToken(Base):
    __tablename__ = "auth_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    access_token: Mapped[str]
    refresh_token: Mapped[str]
    expires_at: Mapped[int]
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="auth_token")


# proper full details for a track
class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    artist: Mapped[str]
    album: Mapped[str]
    image_url: Mapped[str]
    duration_ms: Mapped[int]
    popularity: Mapped[int]

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# stores ALL songs played by user
class ListeningHistory(Base):
    __tablename__ = "listening_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    track_id: Mapped[str] = mapped_column(ForeignKey("tracks.id"))
    track_name: Mapped[str | None]
    artist: Mapped[str | None]
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # link the tables
    track: Mapped["Track"] = relationship()
    user: Mapped["User"] = relationship()

    # idempotency (prevent duplicate track events from being stored)
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "track_id",
            "played_at",
            name="uix_track_played_at",  # uix = unique index/constraint
        ),
    )
