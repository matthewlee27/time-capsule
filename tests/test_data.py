import pytest

from backend import data, storage


@pytest.fixture
def conn(tmp_path):
    return storage.connect(tmp_path / "test.db")


def test_query_scrobbles_filters_by_allowed_column(conn):
    user_id = storage.upsert_user(conn, "alice")
    storage.save_scrobbles(
        conn,
        user_id,
        [
            {"artist": "Radiohead", "track": "Idioteque", "album": None, "mbid": None, "played_at": 100},
            {"artist": "Bjork", "track": "Hyperballad", "album": None, "mbid": None, "played_at": 200},
        ],
    )

    rows = data.query_scrobbles(conn, user_id=user_id, artist="Radiohead")

    assert [r["track"] for r in rows] == ["Idioteque"]


def test_query_scrobbles_rejects_unknown_column(conn):
    with pytest.raises(ValueError):
        data.query_scrobbles(conn, evil="1; DROP TABLE users;--")


def test_query_scrobbles_requires_at_least_one_filter(conn):
    with pytest.raises(ValueError):
        data.query_scrobbles(conn)
