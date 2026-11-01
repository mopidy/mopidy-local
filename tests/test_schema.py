from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

import pytest
from mopidy.models import Album, Artist, ModelType, Ref, Track

from mopidy_local import schema

if TYPE_CHECKING:
    from collections.abc import Generator

DBPATH = ":memory:"

ARTISTS = [
    Artist(
        uri="local:artist:0",
        name="artist #0",
        musicbrainz_id="b5e8922b-5dee-44f2-85e1-7e78b69a7e1d",
    ),
    Artist(uri="local:artist:1", name="artist #1"),
]

ALBUMS = [
    Album(
        uri="local:album:0",
        name="album #0",
        musicbrainz_id="13b290bc-465d-4cb8-85df-9c18c0614a66",
    ),
    Album(uri="local:album:1", name="album #1", artists=[ARTISTS[0]]),
    Album(uri="local:album:2", name="album #2", artists=[ARTISTS[1]]),
]

TRACKS = [
    Track(
        uri="local:track:0",
        name="track #0",
        date="2015-03-15",
        genre="Rock",
    ),
    Track(
        uri="local:track:1",
        name="track #1",
        date="2014",
        artists=[ARTISTS[0]],
    ),
    Track(
        uri="local:track:2",
        name="track #2",
        date="2020-09-01",
        album=ALBUMS[0],
    ),
    Track(
        uri="local:track:3",
        name="track #3",
        date="2020-10-01",
        album=ALBUMS[1],
    ),
    Track(
        uri="local:track:4",
        name="track #4",
        album=ALBUMS[2],
        composers=[ARTISTS[0]],
        performers=[ARTISTS[0]],
        musicbrainz_id="e6cea07e-9d2d-4cd2-912f-94fd11c99763",
    ),
]


@pytest.fixture
def connection() -> Generator[sqlite3.Connection]:
    connection = sqlite3.connect(DBPATH, factory=schema.Connection)
    schema.load(connection)
    for track in TRACKS:
        schema.insert_track(connection, track)
    yield connection
    connection.close()


def test_create(connection: sqlite3.Connection):
    count = schema.count_tracks(connection)
    assert len(TRACKS) == count
    tracks = list(schema.tracks(connection))
    assert len(TRACKS) == len(tracks)


def test_list_distinct(connection: sqlite3.Connection):
    assert [track.name for track in TRACKS] == schema.list_distinct(
        connection,
        "track_name",
    )
    assert schema.list_distinct(connection, "track_no") == []
    assert schema.list_distinct(connection, "disc_no") == []
    assert [album.name for album in ALBUMS] == schema.list_distinct(
        connection,
        "album",
    )
    assert [artist.name for artist in ARTISTS[0:2]] == schema.list_distinct(
        connection,
        "albumartist",
    )
    assert [artist.name for artist in ARTISTS[0:1]] == schema.list_distinct(
        connection,
        "artist",
    )
    assert [artist.name for artist in ARTISTS[0:1]] == schema.list_distinct(
        connection,
        "composer",
    )
    assert [artist.name for artist in ARTISTS[0:1]] == schema.list_distinct(
        connection,
        "performer",
    )
    assert [track.date for track in TRACKS if track.date] == schema.list_distinct(
        connection, "date"
    )
    assert [TRACKS[0].genre] == schema.list_distinct(connection, "genre")
    assert [str(TRACKS[4].musicbrainz_id)] == schema.list_distinct(
        connection,
        "musicbrainz_trackid",
    )
    assert [str(ARTISTS[0].musicbrainz_id)] == schema.list_distinct(
        connection,
        "musicbrainz_artistid",
    )
    assert [str(ALBUMS[0].musicbrainz_id)] == schema.list_distinct(
        connection,
        "musicbrainz_albumid",
    )


def test_dates(connection: sqlite3.Connection):
    with connection as c:
        results = schema.dates(c)
        assert results == ["2014-01-01", "2015-03-15", "2020-09-01", "2020-10-01"]

        results = schema.dates(c, format="%Y")
        assert results == ["2014", "2015", "2020"]


def test_lookup_track(connection: sqlite3.Connection):
    with connection as c:
        for track in TRACKS:
            result = schema.lookup(c, ModelType.TRACK, track.uri)
            assert [track] == list(result)


def test_lookup_album(connection: sqlite3.Connection):
    with connection as c:
        result = schema.lookup(c, ModelType.ALBUM, ALBUMS[0].uri)
        assert [TRACKS[2]] == list(result)

        result = schema.lookup(c, ModelType.ALBUM, ALBUMS[1].uri)
        assert [TRACKS[3]] == list(result)

        result = schema.lookup(c, ModelType.ALBUM, ALBUMS[2].uri)
        assert [TRACKS[4]] == list(result)


def test_lookup_artist(connection: sqlite3.Connection):
    with connection as c:
        result = schema.lookup(c, ModelType.ARTIST, ARTISTS[0].uri)
        assert [TRACKS[1], TRACKS[3]] == list(result)

        result = schema.lookup(c, ModelType.ARTIST, ARTISTS[1].uri)
        assert [TRACKS[4]] == list(result)


@pytest.mark.skip(reason="TODO: check indexed search")
def test_indexed_search(connection: sqlite3.Connection):
    for results, query, filters in [
        ((t.uri for t in TRACKS), [], []),
        ([], [("any", "none")], []),
        (
            [TRACKS[1].uri, TRACKS[3].uri, TRACKS[4].uri],
            [("any", ARTISTS[0].name)],
            [],
        ),
        (
            [TRACKS[3].uri],
            [("any", ARTISTS[0].name)],
            [{"album": ALBUMS[1].uri}],
        ),
        (
            [TRACKS[2].uri],
            [("album", TRACKS[2].album.name)],
            [],
        ),
        (
            [TRACKS[1].uri],
            [("artist", next(iter(TRACKS[1].artists)).name)],
            [],
        ),
        ([TRACKS[0].uri], [("track_name", TRACKS[0].name)], []),
    ]:
        for exact in (True, False):
            with connection as c:
                tracks = schema.search_tracks(c, query, 10, 0, exact, filters)
            assert set(results) == {t.uri for t in tracks}


def test_fulltext_search(connection: sqlite3.Connection):
    for results, query, filters in [
        ((t.uri for t in TRACKS), [("track_name", "track")], []),
        (
            [TRACKS[1].uri, TRACKS[3].uri],
            [("track_name", "track")],
            [
                {"artist": ARTISTS[0].uri},
                {"albumartist": ARTISTS[0].uri},
            ],
        ),
    ]:
        with connection as c:
            tracks = schema.search_tracks(c, query, 10, 0, False, filters)
        assert set(results) == {t.uri for t in tracks}


def test_browse_artists(connection: sqlite3.Connection):
    def ref(artist):
        return Ref.artist(name=artist.name, uri=artist.uri)

    with connection as c:
        assert list(map(ref, ARTISTS)) == schema.browse(c, ModelType.ARTIST)
        assert list(map(ref, ARTISTS)) == schema.browse(
            c,
            ModelType.ARTIST,
            role=["artist", "albumartist"],
        )
        assert list(map(ref, ARTISTS[0:1])) == schema.browse(
            c,
            ModelType.ARTIST,
            role="artist",
        )
        assert list(map(ref, ARTISTS[0:1])) == schema.browse(
            c,
            ModelType.ARTIST,
            role="composer",
        )
        assert list(map(ref, ARTISTS[0:1])) == schema.browse(
            c,
            ModelType.ARTIST,
            role="performer",
        )
        assert list(map(ref, ARTISTS)) == schema.browse(
            c,
            ModelType.ARTIST,
            role="albumartist",
        )


def test_browse_albums(connection: sqlite3.Connection):
    def ref(album):
        return Ref.album(name=album.name, uri=album.uri)

    with connection as c:
        assert list(map(ref, ALBUMS)) == schema.browse(c, ModelType.ALBUM)
        assert list(map(ref, [])) == schema.browse(
            c,
            ModelType.ALBUM,
            artist=ARTISTS[0].uri,
        )
        assert list(map(ref, ALBUMS[1:2])) == schema.browse(
            c,
            ModelType.ALBUM,
            albumartist=ARTISTS[0].uri,
        )


def test_browse_tracks(connection: sqlite3.Connection):
    def ref(track):
        return Ref.track(name=track.name, uri=track.uri)

    with connection as c:
        assert list(map(ref, TRACKS)) == schema.browse(c, ModelType.TRACK)
        assert list(map(ref, TRACKS[1:2])) == schema.browse(
            c,
            ModelType.TRACK,
            artist=ARTISTS[0].uri,
        )
        assert list(map(ref, TRACKS[2:3])) == schema.browse(
            c,
            ModelType.TRACK,
            album=ALBUMS[0].uri,
        )
        assert list(map(ref, TRACKS[3:4])) == schema.browse(
            c,
            ModelType.TRACK,
            albumartist=ARTISTS[0].uri,
        )
        assert list(map(ref, TRACKS[4:5])) == schema.browse(
            c,
            ModelType.TRACK,
            composer=ARTISTS[0].uri,
            performer=ARTISTS[0].uri,
        )


def test_delete(connection: sqlite3.Connection):
    c = connection
    schema.delete_track(c, TRACKS[0].uri)
    schema.cleanup(c)
    assert len(c.execute("SELECT * FROM album").fetchall()) == 3
    assert len(c.execute("SELECT * FROM artist").fetchall()) == 2

    schema.delete_track(c, TRACKS[1].uri)
    schema.cleanup(c)
    assert len(c.execute("SELECT * FROM album").fetchall()) == 3
    assert len(c.execute("SELECT * FROM artist").fetchall()) == 2

    schema.delete_track(c, TRACKS[2].uri)
    schema.cleanup(c)
    assert len(c.execute("SELECT * FROM album").fetchall()) == 2
    assert len(c.execute("SELECT * FROM artist").fetchall()) == 2

    schema.delete_track(c, TRACKS[3].uri)
    schema.cleanup(c)
    assert len(c.execute("SELECT * FROM album").fetchall()) == 1
    assert len(c.execute("SELECT * FROM artist").fetchall()) == 2

    schema.delete_track(c, TRACKS[4].uri)
    schema.cleanup(c)
    assert len(c.execute("SELECT * FROM album").fetchall()) == 0
    assert len(c.execute("SELECT * FROM artist").fetchall()) == 0


def test_tracks_skips_track_with_invalid_date(connection: sqlite3.Connection):
    # Databases created before we validated our models can hold dates in
    # any format. See mopidy-local#92.
    connection.execute(
        "UPDATE track SET date = '31-12-2006' WHERE uri = ?",
        [TRACKS[0].uri],
    )

    tracks = schema.tracks(connection)

    assert len(tracks) == len(TRACKS) - 1
    assert TRACKS[0].uri not in [track.uri for track in tracks]


def test_tracks_skips_track_with_invalid_album_date(connection: sqlite3.Connection):
    connection.execute(
        "UPDATE album SET date = '12-1996' WHERE uri = ?",
        [ALBUMS[0].uri],
    )

    tracks = schema.tracks(connection)

    # tracks[2] is the only track on albums[0].
    assert len(tracks) == len(TRACKS) - 1
    assert TRACKS[2].uri not in [track.uri for track in tracks]


def test_lookup_skips_track_with_invalid_date(connection: sqlite3.Connection):
    connection.execute(
        "UPDATE track SET date = '31-12-2006' WHERE uri = ?",
        [TRACKS[0].uri],
    )

    with connection as c:
        assert schema.lookup(c, ModelType.TRACK, TRACKS[0].uri) == []


def test_search_skips_track_with_invalid_date(connection: sqlite3.Connection):
    connection.execute(
        "UPDATE track SET date = '31-12-2006' WHERE uri = ?",
        [TRACKS[0].uri],
    )

    with connection as c:
        result = schema.search_tracks(c, [], 10, 0, exact=False)

    assert len(result) == len(TRACKS) - 1
    assert TRACKS[0].uri not in [track.uri for track in result]
