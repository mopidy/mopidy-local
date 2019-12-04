from mopidy import backend

from mopidy_local import translator


class LocalPlaybackProvider(backend.PlaybackProvider):
    def translate_uri(self, uri):
        return translator.local_uri_to_file_uri(
            uri, self.backend.config["local"]["media_dir"]
        )
