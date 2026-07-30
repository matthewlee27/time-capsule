from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

#import functions from storage.py
from backend import storage
from backend.config import DATABASE_PATH, LASTFM_API_KEY
from backend.lastfm_client import HistoryHidden, LastFmClient, LastFmError, UserNotFound

app = FastAPI(title="Time Capsule")

lastfm = LastFmClient(api_key=LASTFM_API_KEY)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


def get_db():
    conn = storage.connect(Path(DATABASE_PATH))
    try:
        yield conn
    finally:
        conn.close()

class ConnectRequest(BaseModel):
    username: str

class PullRequest(BaseModel):
    username: str
    from_date: Optional[str] = None  # "YYYY-MM-DD"
    to_date: Optional[str] = None

def _to_unix(date_str: Optional[str]) -> Optional[int]:
    if not date_str:
        return None
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp())

@app.post("/api/connect")
def connect(req: ConnectRequest, conn=Depends(get_db)):
    try:
        lastfm.validate_user(req.username)
    except UserNotFound:
        raise HTTPException(404, "No Last.fm user with that username")
    except HistoryHidden:
        raise HTTPException(403, "This user's recent listening history is private")
    except LastFmError as e:
        raise HTTPException(502, str(e))

    user_id = storage.upsert_user(conn, req.username)
    return {"status": "connected", "user_id": user_id, "username": req.username}


@app.post("/api/pull")
def pull(req: PullRequest, conn=Depends(get_db)):
    user_id = storage.upsert_user(conn, req.username)
    from_ts = _to_unix(req.from_date)
    to_ts = _to_unix(req.to_date)

    try:
        tracks = list(lastfm.fetch_recent_tracks(req.username, from_ts, to_ts))
    except UserNotFound:
        raise HTTPException(404, "No Last.fm user with that username")
    except HistoryHidden:
        raise HTTPException(403, "This user's recent listening history is private")
    except LastFmError as e:
        raise HTTPException(502, str(e))

    result = storage.save_scrobbles(conn, user_id, tracks)
    return {
        "pulled_from_lastfm": len(tracks),
        "saved": result["saved"],
        "duplicates": result["duplicates"],
        "total_stored": storage.scrobble_count(conn, user_id),
    }

@app.get("/api/scrobbles/{username}")
def list_scrobbles(username: str, limit: int = 50, conn=Depends(get_db)):
    user_id = storage.upsert_user(conn, username)
    return {"scrobbles": storage.get_scrobbles(conn, user_id, limit)}


@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/analyze")
def analyze():
    return FileResponse(FRONTEND_DIR / "analyze.html")


app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="frontend")
