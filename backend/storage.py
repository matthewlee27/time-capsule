"""SQLite-backed storage for connected users and pulled scrobbles.

Matches plan.md's "Data Pull & Storage" default: data lands server-side,
never the browser. A plain DB table (vs. an in-memory-only pull) so pulled
history survives across runs instead of re-fetching the same range from
Last.fm every time.
"""

import sqlite3
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

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


def get_scrobbles(
    conn: sqlite3.Connection,
    user_id: int,
    limit: int = 50,
    from_ts: Optional[int] = None,
    to_ts: Optional[int] = None,
    artist: Optional[str] = None,
) -> List[Dict]:
    where = ["user_id = ?"]
    params: List = [user_id]

    if from_ts is not None:
        where.append("played_at >= ?")
        params.append(from_ts)
    if to_ts is not None:
        where.append("played_at <= ?")
        params.append(to_ts)
    if artist is not None:
        where.append("artist = ?")
        params.append(artist)

    params.append(limit)

    rows = conn.execute(
        f"SELECT artist, track, album, played_at FROM scrobbles "
        f"WHERE {' AND '.join(where)} ORDER BY played_at DESC LIMIT ?",
        params,
    ).fetchall()
    return [
        {"artist": r[0], "track": r[1], "album": r[2], "played_at": r[3]}
        for r in rows
    ]


def get_daily_counts(
    conn: sqlite3.Connection,
    user_id: int,
    from_ts: Optional[int] = None,
    to_ts: Optional[int] = None,
    artist: Optional[str] = None,
) -> List[Dict]:
    where = ["user_id = ?"]
    params: List = [user_id]

    if from_ts is not None:
        where.append("played_at >= ?")
        params.append(from_ts)
    if to_ts is not None:
        where.append("played_at <= ?")
        params.append(to_ts)
    if artist is not None:
        where.append("artist = ?")
        params.append(artist)

    rows = conn.execute(
        f"SELECT date(played_at, 'unixepoch') AS day, COUNT(*) FROM scrobbles "
        f"WHERE {' AND '.join(where)} GROUP BY day ORDER BY day",
        params,
    ).fetchall()
    return [{"date": r[0], "count": r[1]} for r in rows]


def get_top_tracks(
    conn: sqlite3.Connection,
    user_id: int,
    from_ts: Optional[int] = None,
    to_ts: Optional[int] = None,
    limit: int = 30,
    artist_cap: Optional[int] = None,
) -> List[Dict]:
    """Top tracks by play count. With artist_cap set, walks the full
    ranked list and skips any track once `artist_cap` tracks from that
    artist are already in the result, so one artist can't crowd out the
    rest of the list."""
    where = ["user_id = ?"]
    params: List = [user_id]

    if from_ts is not None:
        where.append("played_at >= ?")
        params.append(from_ts)
    if to_ts is not None:
        where.append("played_at <= ?")
        params.append(to_ts)

    query = (
        f"SELECT artist, track, COUNT(*) AS play_count FROM scrobbles "
        f"WHERE {' AND '.join(where)} GROUP BY artist, track "
        f"ORDER BY play_count DESC"
    )

    if artist_cap is None:
        rows = conn.execute(query + " LIMIT ?", params + [limit]).fetchall()
        return [{"artist": r[0], "track": r[1], "play_count": r[2]} for r in rows]

    results: List[Dict] = []
    counts: Dict[str, int] = {}
    for artist, track, play_count in conn.execute(query, params):
        if counts.get(artist, 0) >= artist_cap:
            continue
        results.append({"artist": artist, "track": track, "play_count": play_count})
        counts[artist] = counts.get(artist, 0) + 1
        if len(results) >= limit:
            break
    return results


def get_song_daily_series(
    conn: sqlite3.Connection, user_id: int
) -> Dict[Tuple[str, str], List[Tuple[int, int]]]:
    """One sorted (day_ordinal, count) array per song, spanning the user's
    entire history — the sparse structure algorithms.md calls for, built
    from a single grouped query rather than materializing a dense
    songs x days matrix."""
    rows = conn.execute(
        "SELECT artist, track, date(played_at, 'unixepoch') AS day, COUNT(*) "
        "FROM scrobbles WHERE user_id = ? GROUP BY artist, track, day ORDER BY artist, track, day",
        (user_id,),
    ).fetchall()

    series: Dict[Tuple[str, str], List[Tuple[int, int]]] = {}
    for artist, track, day, count in rows:
        series.setdefault((artist, track), []).append((date.fromisoformat(day).toordinal(), count))
    return series


def get_history_span(conn: sqlite3.Connection, user_id: int) -> Optional[Tuple[int, int]]:
    """The (day_ordinal, day_ordinal) range from a user's first to last
    stored scrobble — the "0 to N" from algorithms.md, scoped to what's
    actually been pulled."""
    row = conn.execute(
        "SELECT MIN(played_at), MAX(played_at) FROM scrobbles WHERE user_id = ?", (user_id,)
    ).fetchone()
    if row[0] is None:
        return None
    return (
        datetime.fromtimestamp(row[0], tz=timezone.utc).date().toordinal(),
        datetime.fromtimestamp(row[1], tz=timezone.utc).date().toordinal(),
    )
