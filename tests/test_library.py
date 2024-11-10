import contextlib
import pathlib
import unittest
from unittest import mock

import pykka
from mopidy import core
from mopidy.models import SearchResult, Track

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
        self.backend = actor.LocalBackend.start(
            config=self.config,
            audio=self.audio,
        ).proxy()
        self.core = core.Core.start(
            audio=self.audio,
            backends=[self.backend],
            config=self.config,
        ).proxy()
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
        self.storage.add(track)
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
        self.storage.add(track)
        self.storage.close()
        assert [track] == self.library.lookup(uri).get()

    def test_clear(self):
        self.storage.begin()
        self.storage.add(Track(uri="local:track:track.mp3"))
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

    @mock.patch("mopidy_local.schema.list_distinct")
    def test_distinct_field_track_uses_track_name(self, distinct_mock):
        distinct_mock.return_value = []

        assert self.library.get_distinct("track").get() == set()
        distinct_mock.assert_called_once_with(mock.ANY, "track_name", [])
