import sqlite3
from typing import Any, Dict, List

QUERYABLE_COLUMNS = {"user_id", "artist", "track", "album", "mbid", "played_at"}


def query_scrobbles(conn: sqlite3.Connection, **filters: Any) -> List[Dict]:
    unknown = set(filters) - QUERYABLE_COLUMNS
    if unknown:
        raise ValueError(f"Cannot query by column(s): {', '.join(sorted(unknown))}")
    if not filters:
        raise ValueError("query_scrobbles requires at least one filter")

    where_clause = " AND ".join(f"{column} = ?" for column in filters)
    values = list(filters.values())

    rows = conn.execute(
        f"SELECT artist, track, album, mbid, played_at FROM scrobbles "
        f"WHERE {where_clause} ORDER BY played_at DESC",
        values,
    ).fetchall()

    return [
        {"artist": r[0], "track": r[1], "album": r[2], "mbid": r[3], "played_at": r[4]}
        for r in rows
    ]
