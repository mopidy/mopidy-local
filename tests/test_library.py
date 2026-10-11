import contextlib
import pathlib
import unittest
from typing import cast
from unittest import mock

import pykka
from mopidy import backend, core
from mopidy.models import Album, Artist, SearchResult, Track

from mopidy_local import actor, storage, translator
from tests import dummy_audio, path_to_data_dir


class LocalLibraryProviderTest(unittest.TestCase):
    config = {
        "core": {
            "data_dir": path_to_data_dir(""),
            "max_tracklist_length": 10000,
        },
        "local": {
            "media_dir": path_to_data_dir(""),
            "directories": [],
            "timeout": 10,
            "max_search_results": 100,
            "use_artist_sortname": False,
            "album_art_files": [],
        },
    }

    def setUp(self):
        self.audio = dummy_audio.create_proxy()
        self.backend = cast(
            "backend.BackendProxy",
            actor.LocalBackend.start(
                config=self.config,
                audio=self.audio,
            ).proxy(),
        )
        self.core = cast(
            "core.CoreProxy",
            core.Core.start(
                audio=self.audio,
                backends=[self.backend],
                config=self.config,
            ).proxy(),
        )
        self.library = self.backend.library
        self.storage = storage.LocalStorageProvider(self.config)
        self.storage.load()

    def tearDown(self):
        pykka.ActorRegistry.stop_all()
        with contextlib.suppress(OSError):
            path_to_data_dir("local/library.db").unlink()

    def test_add_noname_ascii(self):
        name = "Test.mp3"
        uri = translator.path_to_local_track_uri(name, pathlib.Path("/media/dir"))
        track = Track(name=name, uri=uri)
        self.storage.begin()
        self.storage.add(
            track, lax_album_match=False, provide_default_album_artists=False
        )
        self.storage.close()
        assert [track] == self.library.lookup(uri).get()

    def test_add_noname_utf8(self):
        name = "Mi\xf0vikudags.mp3"
        uri = translator.path_to_local_track_uri(
            name.encode(),
            pathlib.Path("/media/dir"),
        )
        track = Track(name=name, uri=uri)
        self.storage.begin()
        self.storage.add(
            track, lax_album_match=False, provide_default_album_artists=False
        )
        self.storage.close()
        assert [track] == self.library.lookup(uri).get()

    def test_add_lax_album_match(self):
        artist = Artist(name="Test artist")
        tracks = [
            Track(
                uri="local:track:one",
                name="Track one",
                artists=[artist],
                album=Album(name="Test album", artists=[artist], date="2024"),
            ),
            Track(
                uri="local:track:two",
                name="Track two",
                artists=[artist],
                album=Album(name="Test album", artists=[artist], date="2025"),
            ),
        ]
        self.storage.begin()
        for track in tracks:
            self.storage.add(
                track,
                lax_album_match=True,
                provide_default_album_artists=False,
                tags={},
            )
        self.storage.close()

        albums = [self.library.lookup(track.uri).get()[0].album for track in tracks]
        assert albums[0].uri == albums[1].uri

    def test_add_provides_default_album_artists(self):
        artist = Artist(name="Test artist")
        track = Track(
            uri="local:track:track",
            name="Test track",
            artists=[artist],
            album=Album(name="Test album"),
        )
        self.storage.begin()
        self.storage.add(
            track,
            lax_album_match=False,
            provide_default_album_artists=True,
            tags={},
        )
        self.storage.close()

        stored_track = self.library.lookup(track.uri).get()[0]
        assert [artist.name] == [artist.name for artist in stored_track.album.artists]

    def test_clear(self):
        self.storage.begin()
        self.storage.add(
            Track(uri="local:track:track.mp3"),
            lax_album_match=False,
            provide_default_album_artists=False,
        )
        self.storage.close()
        self.storage.clear()
        assert self.storage.load() == 0

    def test_search_uri(self):
        lib = self.library
        empty = SearchResult(uri="local:search?")
        assert empty == lib.search(uris=None).get()
        assert empty == lib.search(uris=[]).get()
        assert empty == lib.search(uris=["local:"]).get()
        assert empty == lib.search(uris=["local:directory"]).get()
        assert empty == lib.search(uris=["local:directory:"]).get()
        assert empty == lib.search(uris=["foobar:"]).get()

    def test_browse_directory_overrides_album_already_in_query(self):
        album = Album(uri="local:album:0", name="album #0")
        self.storage.begin()
        self.storage.add(
            Track(uri="local:track:0", name="track #0", album=album),
            lax_album_match=False,
            provide_default_album_artists=False,
        )
        self.storage.close()

        refs = self.library.browse("local:directory?album=local:album:0").get()

        assert [ref.uri for ref in refs] == [
            "local:directory?album=local:album:0&type=track",
        ]

    @mock.patch("mopidy_local.schema.list_distinct")
    def test_distinct_field_track_uses_track_name(self, distinct_mock):
        distinct_mock.return_value = []

        assert self.library.get_distinct("track").get() == set()
        distinct_mock.assert_called_once_with(mock.ANY, "track_name", [])
