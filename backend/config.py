import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")

LASTFM_API_KEY = os.environ.get("LASTFM_API_KEY", "")

DATABASE_PATH = os.environ.get(
    "TIME_CAPSULE_DB", str(BACKEND_DIR / "data" / "time_capsule.db")
)
