"""SQLite-backed storage for connected users and pulled scrobbles.

Matches plan.md's "Data Pull & Storage" default: data lands server-side,
never the browser. A plain DB table (vs. an in-memory-only pull) so pulled
history survives across runs instead of re-fetching the same range from
Last.fm every time.
"""

import sqlite3
import time
from pathlib import Path
from typing import Dict, Iterable, List

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lastfm_username TEXT NOT NULL UNIQUE,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS scrobbles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    artist TEXT NOT NULL,
    track TEXT NOT NULL,
    album TEXT,
    mbid TEXT,
    played_at INTEGER NOT NULL,
    created_at INTEGER NOT NULL,
    UNIQUE(user_id, artist, track, played_at)
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA)
    return conn


def upsert_user(conn: sqlite3.Connection, username: str) -> int:
    conn.execute(
        "INSERT INTO users (lastfm_username, created_at) VALUES (?, ?) "
        "ON CONFLICT(lastfm_username) DO NOTHING",
        (username, int(time.time())),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id FROM users WHERE lastfm_username = ?", (username,)
    ).fetchone()
    return row[0]


def save_scrobbles(conn: sqlite3.Connection, user_id: int, tracks: Iterable[Dict]) -> Dict[str, int]:
    """Inserts pulled tracks, silently skipping ones already stored
    (same user/artist/track/played_at) so re-pulling an overlapping
    date range is safe. Returns how many were newly saved vs. already
    present as duplicates.

    Uses conn.total_changes rather than cur.rowcount to count inserts —
    rowcount's behavior across executemany + ON CONFLICT DO NOTHING isn't
    reliably documented, whereas total_changes only increments for rows
    actually written."""
    now = int(time.time())
    rows = [
        (user_id, t["artist"], t["track"], t.get("album"), t.get("mbid"), t["played_at"], now)
        for t in tracks
    ]
    if not rows:
        return {"saved": 0, "duplicates": 0}

    changes_before = conn.total_changes
    conn.executemany(
        "INSERT INTO scrobbles (user_id, artist, track, album, mbid, played_at, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(user_id, artist, track, played_at) DO NOTHING",
        rows,
    )
    conn.commit()
    saved = conn.total_changes - changes_before
    return {"saved": saved, "duplicates": len(rows) - saved}


def scrobble_count(conn: sqlite3.Connection, user_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM scrobbles WHERE user_id = ?", (user_id,)
    ).fetchone()
    return row[0]


def get_scrobbles(conn: sqlite3.Connection, user_id: int, limit: int = 50) -> List[Dict]:
    rows = conn.execute(
        "SELECT artist, track, album, played_at FROM scrobbles "
        "WHERE user_id = ? ORDER BY played_at DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    return [
        {"artist": r[0], "track": r[1], "album": r[2], "played_at": r[3]}
        for r in rows
    ]
