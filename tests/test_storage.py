import pytest

from backend import storage


@pytest.fixture
def conn(tmp_path):
    return storage.connect(tmp_path / "test.db")


def test_upsert_user_is_idempotent(conn):
    id1 = storage.upsert_user(conn, "alice")
    id2 = storage.upsert_user(conn, "alice")
    assert id1 == id2


def test_save_scrobbles_dedupes_on_repull(conn):
    user_id = storage.upsert_user(conn, "alice")
    tracks = [
        {"artist": "A", "track": "Song", "album": None, "mbid": None, "played_at": 100},
    ]
    storage.save_scrobbles(conn, user_id, tracks)
    storage.save_scrobbles(conn, user_id, tracks)  # simulates an overlapping re-pull

    assert storage.scrobble_count(conn, user_id) == 1


def test_save_scrobbles_reports_saved_vs_duplicates(conn):
    user_id = storage.upsert_user(conn, "alice")
    first_batch = [
        {"artist": "A", "track": "Song 1", "album": None, "mbid": None, "played_at": 100},
        {"artist": "A", "track": "Song 2", "album": None, "mbid": None, "played_at": 200},
    ]
    result = storage.save_scrobbles(conn, user_id, first_batch)
    assert result == {"saved": 2, "duplicates": 0}

    # overlapping re-pull: Song 1 repeats, Song 3 is new
    second_batch = first_batch[:1] + [
        {"artist": "A", "track": "Song 3", "album": None, "mbid": None, "played_at": 300},
    ]
    result = storage.save_scrobbles(conn, user_id, second_batch)
    assert result == {"saved": 1, "duplicates": 1}


def test_get_scrobbles_orders_newest_first(conn):
    user_id = storage.upsert_user(conn, "alice")
    storage.save_scrobbles(
        conn,
        user_id,
        [
            {"artist": "A", "track": "Old", "album": None, "mbid": None, "played_at": 100},
            {"artist": "A", "track": "New", "album": None, "mbid": None, "played_at": 200},
        ],
    )

    rows = storage.get_scrobbles(conn, user_id)

    assert [r["track"] for r in rows] == ["New", "Old"]
