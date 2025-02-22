import sqlite3
import unittest
from uuid import UUID

from mopidy.models import Album, Artist, Ref, RefType, Track

from mopidy_local import schema

DBPATH = ":memory:"


class SchemaTest(unittest.TestCase):
    artists = [
        Artist(
            uri="local:artist:0",
            name="artist #0",
            musicbrainz_id=UUID("b5e8922b-5dee-44f2-85e1-7e78b69a7e1d"),
        ),
        Artist(uri="local:artist:1", name="artist #1"),
    ]
    albums = [
        Album(
            uri="local:album:0",
            name="album #0",
            musicbrainz_id=UUID("13b290bc-465d-4cb8-85df-9c18c0614a66"),
        ),
        Album(uri="local:album:1", name="album #1", artists=[artists[0]]),
        Album(uri="local:album:2", name="album #2", artists=[artists[1]]),
    ]
    tracks = [
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
            artists=[artists[0]],
        ),
        Track(
            uri="local:track:2",
            name="track #2",
            date="2020-09-01",
            album=albums[0],
        ),
        Track(
            uri="local:track:3",
            name="track #3",
            date="2020-10-01",
            album=albums[1],
        ),
        Track(
            uri="local:track:4",
            name="track #4",
            album=albums[2],
            composers=[artists[0]],
            performers=[artists[0]],
            musicbrainz_id=UUID("e6cea07e-9d2d-4cd2-912f-94fd11c99763"),
        ),
    ]

    def setUp(self):
        self.connection = sqlite3.connect(DBPATH, factory=schema.Connection)
        schema.load(self.connection)
        for track in self.tracks:
            schema.insert_track(self.connection, track)

    def tearDown(self):
        self.connection.close()
        self.connection = None

    def test_create(self):
        count = schema.count_tracks(self.connection)
        assert len(self.tracks) == count
        tracks = list(schema.tracks(self.connection))
        assert len(self.tracks) == len(tracks)

    def test_list_distinct(self):
        assert [track.name for track in self.tracks] == schema.list_distinct(
            self.connection,
            "track_name",
        )
        assert schema.list_distinct(self.connection, "track_no") == []
        assert schema.list_distinct(self.connection, "disc_no") == []
        assert [album.name for album in self.albums] == schema.list_distinct(
            self.connection,
            "album",
        )
        assert [artist.name for artist in self.artists[0:2]] == schema.list_distinct(
            self.connection,
            "albumartist",
        )
        assert [artist.name for artist in self.artists[0:1]] == schema.list_distinct(
            self.connection,
            "artist",
        )
        assert [artist.name for artist in self.artists[0:1]] == schema.list_distinct(
            self.connection,
            "composer",
        )
        assert [artist.name for artist in self.artists[0:1]] == schema.list_distinct(
            self.connection,
            "performer",
        )
        assert [
            track.date for track in self.tracks if track.date
        ] == schema.list_distinct(self.connection, "date")
        assert [self.tracks[0].genre] == schema.list_distinct(self.connection, "genre")
        assert [str(self.tracks[4].musicbrainz_id)] == schema.list_distinct(
            self.connection,
            "musicbrainz_trackid",
        )
        assert [str(self.artists[0].musicbrainz_id)] == schema.list_distinct(
            self.connection,
            "musicbrainz_artistid",
        )
        assert [str(self.albums[0].musicbrainz_id)] == schema.list_distinct(
            self.connection,
            "musicbrainz_albumid",
        )

    def test_dates(self):
        with self.connection as c:
            results = schema.dates(c)
            assert results == ["2014-01-01", "2015-03-15", "2020-09-01", "2020-10-01"]

            results = schema.dates(c, format="%Y")
            assert results == ["2014", "2015", "2020"]

    def test_lookup_track(self):
        with self.connection as c:
            for track in self.tracks:
                result = schema.lookup(c, RefType.TRACK, track.uri)
                assert [track] == list(result)

    def test_lookup_album(self):
        with self.connection as c:
            result = schema.lookup(c, RefType.ALBUM, self.albums[0].uri)
            assert [self.tracks[2]] == list(result)

            result = schema.lookup(c, RefType.ALBUM, self.albums[1].uri)
            assert [self.tracks[3]] == list(result)

            result = schema.lookup(c, RefType.ALBUM, self.albums[2].uri)
            assert [self.tracks[4]] == list(result)

    def test_lookup_artist(self):
        with self.connection as c:
            result = schema.lookup(c, RefType.ARTIST, self.artists[0].uri)
            assert [self.tracks[1], self.tracks[3]] == list(result)

            result = schema.lookup(c, RefType.ARTIST, self.artists[1].uri)
            assert [self.tracks[4]] == list(result)

    @unittest.SkipTest  # TODO: check indexed search
    def test_indexed_search(self):
        for results, query, filters in [
            ((t.uri for t in self.tracks), [], []),
            ([], [("any", "none")], []),
            (
                [self.tracks[1].uri, self.tracks[3].uri, self.tracks[4].uri],
                [("any", self.artists[0].name)],
                [],
            ),
            (
                [self.tracks[3].uri],
                [("any", self.artists[0].name)],
                [{"album": self.albums[1].uri}],
            ),
            (
                [self.tracks[2].uri],
                [("album", self.tracks[2].album.name)],
                [],
            ),
            (
                [self.tracks[1].uri],
                [("artist", next(iter(self.tracks[1].artists)).name)],
                [],
            ),
            ([self.tracks[0].uri], [("track_name", self.tracks[0].name)], []),
        ]:
            for exact in (True, False):
                with self.connection as c:
                    tracks = schema.search_tracks(c, query, 10, 0, exact, filters)
                assert set(results) == {t.uri for t in tracks}

    def test_fulltext_search(self):
        for results, query, filters in [
            ((t.uri for t in self.tracks), [("track_name", "track")], []),
            (
                [self.tracks[1].uri, self.tracks[3].uri],
                [("track_name", "track")],
                [
                    {"artist": self.artists[0].uri},
                    {"albumartist": self.artists[0].uri},
                ],
            ),
        ]:
            with self.connection as c:
                tracks = schema.search_tracks(c, query, 10, 0, False, filters)
            assert set(results) == {t.uri for t in tracks}

    def test_browse_artists(self):
        def ref(artist):
            return Ref.artist(name=artist.name, uri=artist.uri)

        with self.connection as c:
            assert list(map(ref, self.artists)) == schema.browse(c, RefType.ARTIST)
            assert list(map(ref, self.artists)) == schema.browse(
                c,
                RefType.ARTIST,
                role=["artist", "albumartist"],
            )
            assert list(map(ref, self.artists[0:1])) == schema.browse(
                c,
                RefType.ARTIST,
                role="artist",
            )
            assert list(map(ref, self.artists[0:1])) == schema.browse(
                c,
                RefType.ARTIST,
                role="composer",
            )
            assert list(map(ref, self.artists[0:1])) == schema.browse(
                c,
                RefType.ARTIST,
                role="performer",
            )
            assert list(map(ref, self.artists)) == schema.browse(
                c,
                RefType.ARTIST,
                role="albumartist",
            )

    def test_browse_albums(self):
        def ref(album):
            return Ref.album(name=album.name, uri=album.uri)

        with self.connection as c:
            assert list(map(ref, self.albums)) == schema.browse(c, RefType.ALBUM)
            assert list(map(ref, [])) == schema.browse(
                c,
                RefType.ALBUM,
                artist=self.artists[0].uri,
            )
            assert list(map(ref, self.albums[1:2])) == schema.browse(
                c,
                RefType.ALBUM,
                albumartist=self.artists[0].uri,
            )

    def test_browse_tracks(self):
        def ref(track):
            return Ref.track(name=track.name, uri=track.uri)

        with self.connection as c:
            assert list(map(ref, self.tracks)) == schema.browse(c, RefType.TRACK)
            assert list(map(ref, self.tracks[1:2])) == schema.browse(
                c,
                RefType.TRACK,
                artist=self.artists[0].uri,
            )
            assert list(map(ref, self.tracks[2:3])) == schema.browse(
                c,
                RefType.TRACK,
                album=self.albums[0].uri,
            )
            assert list(map(ref, self.tracks[3:4])) == schema.browse(
                c,
                RefType.TRACK,
                albumartist=self.artists[0].uri,
            )
            assert list(map(ref, self.tracks[4:5])) == schema.browse(
                c,
                RefType.TRACK,
                composer=self.artists[0].uri,
                performer=self.artists[0].uri,
            )

    def test_delete(self):
        c = self.connection
        schema.delete_track(c, self.tracks[0].uri)
        schema.cleanup(c)
        assert len(c.execute("SELECT * FROM album").fetchall()) == 3
        assert len(c.execute("SELECT * FROM artist").fetchall()) == 2

        schema.delete_track(c, self.tracks[1].uri)
        schema.cleanup(c)
        assert len(c.execute("SELECT * FROM album").fetchall()) == 3
        assert len(c.execute("SELECT * FROM artist").fetchall()) == 2

        schema.delete_track(c, self.tracks[2].uri)
        schema.cleanup(c)
        assert len(c.execute("SELECT * FROM album").fetchall()) == 2
        assert len(c.execute("SELECT * FROM artist").fetchall()) == 2

        schema.delete_track(c, self.tracks[3].uri)
        schema.cleanup(c)
        assert len(c.execute("SELECT * FROM album").fetchall()) == 1
        assert len(c.execute("SELECT * FROM artist").fetchall()) == 2

        schema.delete_track(c, self.tracks[4].uri)
        schema.cleanup(c)
        assert len(c.execute("SELECT * FROM album").fetchall()) == 0
        assert len(c.execute("SELECT * FROM artist").fetchall()) == 0
