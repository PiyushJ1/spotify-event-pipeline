import sys
import os

sys.path.append(os.getcwd())

from src.common.db import engine, Base
from src.common.models import SimpleSong


def init_db():
    Base.metadata.create_all(bind=engine)
    print("table created in db")


init_db()
