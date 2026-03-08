from src.common.db import engine, Base
from src.common.models import SimpleSong, User, AuthToken, Track, ListeningHistory

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

print("Done")
