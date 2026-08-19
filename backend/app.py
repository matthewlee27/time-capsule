from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

#import functions from storage.py
from backend import storage
from backend.config import DATABASE_PATH, LASTFM_API_KEY
from backend.engines import propLiftEngine
from backend.lastfm_client import HistoryHidden, LastFmClient, LastFmError, UserNotFound

app = FastAPI(title="Time Capsule")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

lastfm = LastFmClient(api_key=LASTFM_API_KEY)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "out"


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
def list_scrobbles(
    username: str,
    limit: int = 50,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    artist: Optional[str] = None,
    conn=Depends(get_db),
):
    user_id = storage.upsert_user(conn, username)
    from_ts = _to_unix(from_date)
    to_ts = _to_unix(to_date)
    return {"scrobbles": storage.get_scrobbles(conn, user_id, limit, from_ts, to_ts, artist)}

@app.get("/api/scrobbles/{username}/daily-counts")
def scrobble_daily_counts(
    username: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    artist: Optional[str] = None,
    conn=Depends(get_db),
):
    user_id = storage.upsert_user(conn, username)
    from_ts = _to_unix(from_date)
    to_ts = _to_unix(to_date)
    return {"daily_counts": storage.get_daily_counts(conn, user_id, from_ts, to_ts, artist)}

@app.get("/api/scrobbles/{username}/top-tracks")
def scrobble_top_tracks(
    username: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 30,
    conn=Depends(get_db),
):
    user_id = storage.upsert_user(conn, username)
    from_ts = _to_unix(from_date)
    to_ts = _to_unix(to_date)
    return {"top_tracks": storage.get_top_tracks(conn, user_id, from_ts, to_ts, limit)}

@app.get("/api/scrobbles/{username}/date-range")
def scrobble_date_range(username: str, conn=Depends(get_db)):
    user_id = storage.upsert_user(conn, username)
    span = storage.get_history_span(conn, user_id)
    if span is None:
        return {"earliest": None, "latest": None}
    span_start, span_end = span
    return {
        "earliest": date.fromordinal(span_start).isoformat(),
        "latest": date.fromordinal(span_end).isoformat(),
    }

@app.get("/api/scrobbles/{username}/lifted-top-tracks")
def scrobble_lifted_top_tracks(
    username: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 15,
    conn=Depends(get_db),
):
    user_id = storage.upsert_user(conn, username)
    span = storage.get_history_span(conn, user_id)
    if span is None:
        return {"lifted_top_tracks": []}
    span_start, span_end = span

    window_start = date.fromisoformat(from_date).toordinal() if from_date else span_start
    window_end = date.fromisoformat(to_date).toordinal() if to_date else span_end

    series = storage.get_song_daily_series(conn, user_id)
    results = propLiftEngine.compute_lift(
        series, span_start, span_end, window_start, window_end, limit=limit
    )
    return {"lifted_top_tracks": results}

@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/analyze")
def analyze():
    return FileResponse(FRONTEND_DIR / "analyze.html")


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
