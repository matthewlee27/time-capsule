# Storage

Single SQLite file (`backend/data/time_capsule.db`), shared by all users — see [backend/storage.py](../backend/storage.py) for the schema and query functions. No retention/expiry policy yet; rows persist until manually deleted.

## `users`

| column | type | constraints | notes |
| --- | --- | --- | --- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | internal user id — what `scrobbles.user_id` points at |
| `lastfm_username` | TEXT | NOT NULL, UNIQUE | the Last.fm identity connected in step 2 |
| `created_at` | INTEGER | NOT NULL | unix timestamp, when the user was first connected |

## `scrobbles`

| column | type | constraints | notes |
| --- | --- | --- | --- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `user_id` | INTEGER | NOT NULL, REFERENCES `users(id)` | which user this scrobble belongs to |
| `artist` | TEXT | NOT NULL | from Last.fm, not a Spotify id — see plan.md's Track Resolution section |
| `track` | TEXT | NOT NULL | track name, same caveat as `artist` |
| `album` | TEXT | nullable | Last.fm doesn't always return one |
| `mbid` | TEXT | nullable | MusicBrainz id, when Last.fm has one |
| `played_at` | INTEGER | NOT NULL | unix timestamp of the scrobble itself (from Last.fm's `date.uts`) — this is the "listened to at" time, not a storage timestamp |
| `created_at` | INTEGER | NOT NULL | unix timestamp of when *we* stored the row |
| — | — | UNIQUE(`user_id`, `artist`, `track`, `played_at`) | dedup key — makes re-pulling an overlapping date range safe (see [storage.save_scrobbles](../backend/storage.py)) |
