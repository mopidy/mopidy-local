import pathlib
import os
import unittest
from unittest import mock

import pykka
from mopidy import core
from mopidy.models import SearchResult, Track, Album, Image

from mopidy_local import actor, storage, translator
from tests import dummy_audio, path_to_data_dir


class LocalLibraryProviderTest(unittest.TestCase):
    config = {
        "core": {"data_dir": path_to_data_dir(""), "max_tracklist_length": 10000},
        "local": {
            "media_dir": path_to_data_dir(""),
            "directories": [],
            "timeout": 10,
            "max_search_results": 100,
            "use_artist_sortname": False,
            "album_art_files": ["*.jpg", "*.jpeg", "*.png"],
            "album_art_min_dimensions": 50
        },
    }

    def setUp(self):
        self.audio = dummy_audio.create_proxy()
        self.backend = actor.LocalBackend.start(
            config=self.config, audio=self.audio
        ).proxy()
        self.core = core.Core.start(
            audio=self.audio, backends=[self.backend], config=self.config
        ).proxy()
        self.library = self.backend.library
        self.storage = storage.LocalStorageProvider(self.config)
        self.storage.load()

    def tearDown(self):  # noqa: N802
        pykka.ActorRegistry.stop_all()
        try:
            os.remove(path_to_data_dir("local/library.db"))
        except OSError:
            pass

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
            name.encode(), pathlib.Path("/media/dir")
        )
        track = Track(name=name, uri=uri)
        self.storage.begin()
        self.storage.add(track)
        self.storage.close()
        assert [track] == self.library.lookup(uri).get()

    def test_add_track_with_album_cover(self):
        name = "Test.mp3"
        uri = translator.path_to_local_track_uri(name, pathlib.Path("/media/dir"))
        track = Track(name=name, uri=uri, album=Album(uri="local:album:0", name="album #0"))
        self.storage.begin()
        self.storage.add(track)
        self.storage.close()

        # DB assertions
        assert [track] == self.library.lookup(uri).get()
        images = self.library.get_images([uri]).get()
        assert len(images) == 1
        assert len(images[uri]) == 1
        expected_name = "2995b49dad376e28a052ecbc0f352cc5-95x95.jpeg"
        assert images[uri][0] == Image(height=95, width=95, uri=f"/local/{expected_name}")

        # File assertions
        assert path_to_data_dir(f"local/images").is_dir()
        assert len(os.listdir(path_to_data_dir(f"local/images"))) == 1
        assert path_to_data_dir(f"local/images/{expected_name}").exists()

    def test_add_track_with_too_small_album_cover(self):
        # Change min size so that the 95x95 image is ignored
        self.storage._min_dimensions = 100

        name = "Test.mp3"
        uri = translator.path_to_local_track_uri(name, pathlib.Path("/media/dir"))
        track = Track(name=name, uri=uri, album=Album(uri="local:album:0", name="album #0"))
        self.storage.begin()
        self.storage.add(track)
        self.storage.close()

        # DB assertions
        assert [track] == self.library.lookup(uri).get()
        images = self.library.get_images([uri]).get()
        assert len(images) == 1
        assert len(images[uri]) == 0

        # File assertions
        assert path_to_data_dir(f"local/images").is_dir()
        assert not os.listdir(path_to_data_dir(f"local/images"))

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
