import logging
from typing import ClassVar

import pykka
from mopidy import backend
from mopidy.types import UriScheme

from mopidy_local import storage
from mopidy_local.library import LocalLibraryProvider
from mopidy_local.playback import LocalPlaybackProvider

logger = logging.getLogger(__name__)


class LocalBackend(pykka.ThreadingActor, backend.Backend):
    uri_schemes: ClassVar[list[UriScheme]] = [UriScheme("local")]

    def __init__(self, config, audio):
        super().__init__()

        self.config = config

        storage.check_dirs_and_files(config)

        self.playback = LocalPlaybackProvider(audio=audio, backend=self)
        self.library = LocalLibraryProvider(backend=self, config=config)
