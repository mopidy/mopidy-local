import functools
import pathlib

from mopidy.internal import deprecation
from mopidy.types import Uri


def path_to_data_dir(name) -> pathlib.Path:
    path = pathlib.Path(__file__).parent / "data" / name
    return path.resolve()


def generate_song(i) -> Uri:
    return Uri(f"local:track:song{i}.wav")


def populate_tracklist(func):
    @functools.wraps(func)
    def wrapper(self):
        with deprecation.ignore("core.tracklist.add:tracks_arg"):
            self.tl_tracks = self.core.tracklist.add(self.tracks)
        return func(self)

    return wrapper


class IsA:
    def __init__(self, klass):
        self.klass = klass

    def __eq__(self, rhs):
        try:
            return isinstance(rhs, self.klass)
        except TypeError:
            return type(rhs) is type(self.klass)

    def __ne__(self, rhs):
        return not self.__eq__(rhs)

    def __repr__(self):
        return str(self.klass)
