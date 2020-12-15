import sqlite3
import unittest

from mopidy.models import Album, Artist, Ref, Track

from mopidy_local import schema

DBPATH = ":memory:"


class SchemaTest(unittest.TestCase):
    artists = [
        Artist(uri="local:artist:0", name="artist #0", musicbrainz_id="1234a-987c"),
        Artist(uri="local:artist:1", name="artist #1"),
    ]
    albums = [
        Album(uri="local:album:0", name="album #0", musicbrainz_id="1234a-3421d"),
        Album(uri="local:album:1", name="album #1", artists=[artists[0]]),
        Album(uri="local:album:2", name="album #2", artists=[artists[1]]),
    ]
    tracks = [
        Track(uri="local:track:0", name="track #0", date="2015-03-15", genre="Rock"),
        Track(uri="local:track:1", name="track #1", artists=[artists[0]]),
        Track(uri="local:track:2", name="track #2", album=albums[0]),
        Track(uri="local:track:3", name="track #3", album=albums[1]),
        Track(
            uri="local:track:4",
            name="track #4",
            album=albums[2],
            composers=[artists[0]],
            performers=[artists[0]],
            musicbrainz_id="1234a-567b",
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
        self.assertEqual(
            [track.name for track in self.tracks],
            schema.list_distinct(self.connection, "track_name"),
        )
        self.assertEqual([], schema.list_distinct(self.connection, "track_no"))
        self.assertEqual([], schema.list_distinct(self.connection, "disc_no"))
        self.assertEqual(
            [album.name for album in self.albums],
            schema.list_distinct(self.connection, "album"),
        )
        self.assertEqual(
            [artist.name for artist in self.artists[0:2]],
            schema.list_distinct(self.connection, "albumartist"),
        )
        self.assertEqual(
            [artist.name for artist in self.artists[0:1]],
            schema.list_distinct(self.connection, "artist"),
        )
        self.assertEqual(
            [artist.name for artist in self.artists[0:1]],
            schema.list_distinct(self.connection, "composer"),
        )
        self.assertEqual(
            [artist.name for artist in self.artists[0:1]],
            schema.list_distinct(self.connection, "performer"),
        )
        self.assertEqual(
            [self.tracks[0].date], schema.list_distinct(self.connection, "date")
        )
        self.assertEqual(
            [self.tracks[0].genre], schema.list_distinct(self.connection, "genre")
        )
        self.assertEqual(
            [self.tracks[4].musicbrainz_id],
            schema.list_distinct(self.connection, "musicbrainz_trackid"),
        )
        self.assertEqual(
            [self.artists[0].musicbrainz_id],
            schema.list_distinct(self.connection, "musicbrainz_artistid"),
        )
        self.assertEqual(
            [self.albums[0].musicbrainz_id],
            schema.list_distinct(self.connection, "musicbrainz_albumid"),
        )

    def test_lookup_track(self):
        with self.connection as c:
            for track in self.tracks:
                result = schema.lookup(c, Ref.TRACK, track.uri)
                assert [track] == list(result)

    def test_lookup_album(self):
        with self.connection as c:
            result = schema.lookup(c, Ref.ALBUM, self.albums[0].uri)
            assert [self.tracks[2]] == list(result)

            result = schema.lookup(c, Ref.ALBUM, self.albums[1].uri)
            assert [self.tracks[3]] == list(result)

            result = schema.lookup(c, Ref.ALBUM, self.albums[2].uri)
            assert [self.tracks[4]] == list(result)

    def test_lookup_artist(self):
        with self.connection as c:
            result = schema.lookup(c, Ref.ARTIST, self.artists[0].uri)
            assert [self.tracks[1], self.tracks[3]] == list(result)

            result = schema.lookup(c, Ref.ARTIST, self.artists[1].uri)
            assert [self.tracks[4]] == list(result)

    @unittest.SkipTest  # TODO: check indexed search
    def test_indexed_search(self):
        for results, query, filters in [
            (map(lambda t: t.uri, self.tracks), [], []),
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
                self.assertCountEqual(results, map(lambda t: t.uri, tracks))

    def test_fulltext_search(self):
        for results, query, filters in [
            (map(lambda t: t.uri, self.tracks), [("track_name", "track")], []),
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
            self.assertCountEqual(results, map(lambda t: t.uri, tracks))

    def test_browse_artists(self):
        def ref(artist):
            return Ref.artist(name=artist.name, uri=artist.uri)

        with self.connection as c:
            assert list(map(ref, self.artists)) == schema.browse(c, Ref.ARTIST)
            assert list(map(ref, self.artists)) == schema.browse(
                c, Ref.ARTIST, role=["artist", "albumartist"]
            )
            assert list(map(ref, self.artists[0:1])) == schema.browse(
                c, Ref.ARTIST, role="artist"
            )
            assert list(map(ref, self.artists[0:1])) == schema.browse(
                c, Ref.ARTIST, role="composer"
            )
            assert list(map(ref, self.artists[0:1])) == schema.browse(
                c, Ref.ARTIST, role="performer"
            )
            assert list(map(ref, self.artists)) == schema.browse(
                c, Ref.ARTIST, role="albumartist"
            )

    def test_browse_albums(self):
        def ref(album):
            return Ref.album(name=album.name, uri=album.uri)

        with self.connection as c:
            assert list(map(ref, self.albums)) == schema.browse(c, Ref.ALBUM)
            assert list(map(ref, [])) == schema.browse(
                c, Ref.ALBUM, artist=self.artists[0].uri
            )
            assert list(map(ref, self.albums[1:2])) == schema.browse(
                c, Ref.ALBUM, albumartist=self.artists[0].uri
            )

    def test_browse_tracks(self):
        def ref(track):
            return Ref.track(name=track.name, uri=track.uri)

        with self.connection as c:
            assert list(map(ref, self.tracks)) == schema.browse(c, Ref.TRACK)
            assert list(map(ref, self.tracks[1:2])) == schema.browse(
                c, Ref.TRACK, artist=self.artists[0].uri
            )
            assert list(map(ref, self.tracks[2:3])) == schema.browse(
                c, Ref.TRACK, album=self.albums[0].uri
            )
            assert list(map(ref, self.tracks[3:4])) == schema.browse(
                c, Ref.TRACK, albumartist=self.artists[0].uri
            )
            assert list(map(ref, self.tracks[4:5])) == schema.browse(
                c,
                Ref.TRACK,
                composer=self.artists[0].uri,
                performer=self.artists[0].uri,
            )

    def test_delete(self):
        c = self.connection
        schema.delete_track(c, self.tracks[0].uri)
        schema.cleanup(c)
        assert 3 == len(c.execute("SELECT * FROM album").fetchall())
        assert 2 == len(c.execute("SELECT * FROM artist").fetchall())

        schema.delete_track(c, self.tracks[1].uri)
        schema.cleanup(c)
        assert 3 == len(c.execute("SELECT * FROM album").fetchall())
        assert 2 == len(c.execute("SELECT * FROM artist").fetchall())

        schema.delete_track(c, self.tracks[2].uri)
        schema.cleanup(c)
        assert 2 == len(c.execute("SELECT * FROM album").fetchall())
        assert 2 == len(c.execute("SELECT * FROM artist").fetchall())

        schema.delete_track(c, self.tracks[3].uri)
        schema.cleanup(c)
        assert 1 == len(c.execute("SELECT * FROM album").fetchall())
        assert 2 == len(c.execute("SELECT * FROM artist").fetchall())

        schema.delete_track(c, self.tracks[4].uri)
        schema.cleanup(c)
        assert 0 == len(c.execute("SELECT * FROM album").fetchall())
        assert 0 == len(c.execute("SELECT * FROM artist").fetchall())
