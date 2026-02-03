from sqlalchemy import Column, Integer, String
from src.common.db import Base


class SimpleSong(Base):
    __tablename__ = "simple_songs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    artist = Column(String, nullable=False)

    # prevent duplicates (idempotency)
    spotify_id = Column(String, unique=True)
