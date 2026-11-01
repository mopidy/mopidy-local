from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import pykka
import pytest
from mopidy.core import Core

from mopidy_local import actor
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
