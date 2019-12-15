import pathlib

from mopidy.internal import deprecation


def path_to_data_dir(name):
    path = pathlib.Path(__file__).parent / "data" / name
    return path.resolve()


def generate_song(i):
    return "local:track:song%s.wav" % i


def populate_tracklist(func):
    def wrapper(self):
        with deprecation.ignore("core.tracklist.add:tracks_arg"):
            self.tl_tracks = self.core.tracklist.add(self.tracks)
        return func(self)

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


class IsA:
    def __init__(self, klass):
        self.klass = klass

    def __eq__(self, rhs):
        try:
            return isinstance(rhs, self.klass)
        except TypeError:
            return type(rhs) == type(self.klass)  # noqa

    def __ne__(self, rhs):
        return not self.__eq__(rhs)

    def __repr__(self):
        return str(self.klass)
