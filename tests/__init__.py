import pathlib

from mopidy.types import Uri


def path_to_data_dir(name) -> pathlib.Path:
    path = pathlib.Path(__file__).parent / "data" / name
    return path.resolve()


def generate_song(i) -> Uri:
    return Uri(f"local:track:song{i}.wav")


class IsA:  # noqa: PLW1641
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
