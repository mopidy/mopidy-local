from __future__ import annotations

import contextlib
import pathlib
from typing import TYPE_CHECKING, Any
from unittest import mock

import pytest
from mopidy.models import Album, SearchResult, Track

from mopidy_local import storage as storage_module
from mopidy_local import translator
from tests import path_to_data_dir

if TYPE_CHECKING:
    from collections.abc import Generator

    from mopidy.backend import BackendProxy, LibraryProviderProxy

    from mopidy_local.storage import LocalStorageProvider


@pytest.fixture
def config(config: dict[str, Any]) -> dict[str, Any]:
    return {**config, "local": {**config["local"], "max_search_results": 100}}


@pytest.fixture
def library(
    backend: BackendProxy, storage: LocalStorageProvider
) -> LibraryProviderProxy:
    return backend.library


@pytest.fixture
def storage(config: dict[str, Any]) -> Generator[LocalStorageProvider]:
    storage = storage_module.LocalStorageProvider(config)
    storage.load()
    yield storage
    with contextlib.suppress(OSError):
        path_to_data_dir("local/library.db").unlink()


def test_add_noname_ascii(library: LibraryProviderProxy, storage: LocalStorageProvider):
    name = "Test.mp3"
    uri = translator.path_to_local_track_uri(name, pathlib.Path("/media/dir"))
    track = Track(name=name, uri=uri)
    storage.begin()
    storage.add(track)
    storage.close()
    assert [track] == library.lookup(uri).get()


def test_add_noname_utf8(library: LibraryProviderProxy, storage: LocalStorageProvider):
    name = "Mi\xf0vikudags.mp3"
    uri = translator.path_to_local_track_uri(
        name.encode(),
        pathlib.Path("/media/dir"),
    )
    track = Track(name=name, uri=uri)
    storage.begin()
    storage.add(track)
    storage.close()
    assert [track] == library.lookup(uri).get()


def test_clear(storage: LocalStorageProvider):
    storage.begin()
    storage.add(Track(uri="local:track:track.mp3"))
    storage.close()
    storage.clear()
    assert storage.load() == 0


def test_search_uri(library: LibraryProviderProxy):
    lib = library
    empty = SearchResult(uri="local:search?")
    assert empty == lib.search(uris=None).get()
    assert empty == lib.search(uris=[]).get()
    assert empty == lib.search(uris=["local:"]).get()
    assert empty == lib.search(uris=["local:directory"]).get()
    assert empty == lib.search(uris=["local:directory:"]).get()
    assert empty == lib.search(uris=["foobar:"]).get()


def test_browse_directory_overrides_album_already_in_query(
    library: LibraryProviderProxy, storage: LocalStorageProvider
):
    album = Album(uri="local:album:0", name="album #0")
    storage.begin()
    storage.add(Track(uri="local:track:0", name="track #0", album=album))
    storage.close()

    refs = library.browse("local:directory?album=local:album:0").get()

    assert [ref.uri for ref in refs] == [
        "local:directory?album=local:album:0&type=track",
    ]


@mock.patch("mopidy_local.schema.list_distinct")
def test_distinct_field_track_uses_track_name(
    distinct_mock: mock.Mock, library: LibraryProviderProxy
):
    distinct_mock.return_value = []

    assert library.get_distinct("track").get() == set()
    distinct_mock.assert_called_once_with(mock.ANY, "track_name", [])
