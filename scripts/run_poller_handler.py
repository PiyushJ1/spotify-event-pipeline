"""Local runner for the poller Lambda handler.

Usage:
    python3 scripts/run_poller_handler.py

This imports the handler and invokes it once. It loads the project's .env automatically.
"""

import os
from dotenv import load_dotenv
import time

import sys
import os

# ensure repo root is on sys.path so `src` is importable
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

load_dotenv()

# Local defaults for running against LocalStack during development
os.environ.setdefault("AWS_ACCESS_KEY_ID", os.environ.get("AWS_ACCESS_KEY_ID", "test"))
os.environ.setdefault(
    "AWS_SECRET_ACCESS_KEY", os.environ.get("AWS_SECRET_ACCESS_KEY", "test")
)
os.environ.setdefault(
    "SQS_ENDPOINT_URL", os.environ.get("SQS_ENDPOINT_URL", "http://localhost:4566")
)

from src.poller.handler import handler


if __name__ == "__main__":
    while True:
        print("Polling now!")
        res = handler({}, {})
        print("Result:", res)
        time.sleep(180)
