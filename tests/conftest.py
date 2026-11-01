from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import pykka
import pytest
from mopidy.core import Core

from mopidy_local import actor
from mopidy_local.library import LocalLibraryProvider
from tests import dummy_audio, path_to_data_dir

if TYPE_CHECKING:
    from collections.abc import Generator

    from mopidy.audio import AudioProxy
    from mopidy.backend import BackendProxy
    from mopidy.core import (
        CoreProxy,
        PlaybackControllerProxy,
        TracklistControllerProxy,
    )
    from mopidy.models import TlTrack, Track
    from mopidy.types import Uri

    from tests import AddToTracklist


@pytest.fixture
def config() -> dict[str, Any]:
    return {
        "core": {
            "data_dir": path_to_data_dir(""),
            "max_tracklist_length": 10000,
        },
        "local": {
            "media_dir": path_to_data_dir(""),
            "directories": [],
            "timeout": 10,
            "use_artist_sortname": False,
            "album_art_files": [],
        },
    }


@pytest.fixture(autouse=True)
def stop_actors() -> Generator[None]:
    yield
    pykka.ActorRegistry.stop_all()


@pytest.fixture
def audio() -> AudioProxy:
    return cast("AudioProxy", dummy_audio.create_proxy())


@pytest.fixture
def backend(config: dict[str, Any], audio: AudioProxy) -> BackendProxy:
    return cast(
        "BackendProxy",
        actor.LocalBackend.start(config=config, audio=audio).proxy(),
    )


@pytest.fixture
def core(config: dict[str, Any], audio: AudioProxy, backend: BackendProxy) -> CoreProxy:
    return cast(
        "CoreProxy",
        Core.start(config=config, audio=audio, backends=[backend]).proxy(),
    )


@pytest.fixture
def playback(core: CoreProxy) -> PlaybackControllerProxy:
    return core.playback


@pytest.fixture
def tracklist(core: CoreProxy) -> TracklistControllerProxy:
    return core.tracklist


@pytest.fixture
def add_to_tracklist(
    monkeypatch: pytest.MonkeyPatch, tracklist: TracklistControllerProxy
) -> AddToTracklist:
    """Put tracks in a fake library, and add them to the tracklist by URI."""
    library: dict[Uri, Track] = {}
    monkeypatch.setattr(
        LocalLibraryProvider,
        "lookup",
        lambda _self, uri: [library[uri]] if uri in library else [],
    )

    def add(*tracks: Track, at_position: int | None = None) -> list[TlTrack]:
        library.update({track.uri: track for track in tracks})
        return tracklist.add(
            uris=[track.uri for track in tracks],
            at_position=at_position,
        ).get()

    return add
