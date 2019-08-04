from __future__ import absolute_import, unicode_literals

import os

from mopidy.internal import deprecation


def path_to_data_dir(name):
    if not isinstance(name, bytes):
        name = name.encode('utf-8')
    path = os.path.dirname(__file__)
    path = os.path.join(path, b'data')
    path = os.path.abspath(path)
    return os.path.join(path, name)


def generate_song(i):
    return 'local:track:song%s.wav' % i


def populate_tracklist(func):
    def wrapper(self):
        with deprecation.ignore('core.tracklist.add:tracks_arg'):
            self.tl_tracks = self.core.tracklist.add(self.tracks)
        return func(self)

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper
