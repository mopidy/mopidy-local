from __future__ import unicode_literals

import shutil
import tempfile
import unittest

from mopidy.local import translator
from mopidy.models import SearchResult, Track

from mopidy_local import sqlite


class SQLiteLibraryProviderTest(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.library = sqlite.SQLiteLibrary(dict(
            core={
                'data_dir': self.tempdir,
            },
            local={
                'media_dir': self.tempdir,
                'data_dir': self.tempdir,
                'excluded_file_extensions': [],
                'directories': [],
                'encodings': ['utf-8', 'latin-1'],
                'timeout': 1.0,
                'use_album_mbid_uri': False,
                'use_artist_mbid_uri': False,
                'search_limit': None,
                'base_uri': '/images/',
                'image_dir': None,
                'album_art_files': []
            }
        ))
        self.library.load()

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_add_noname_ascii(self):
        name = b'Test.mp3'
        uri = translator.path_to_local_track_uri(name)
        track = Track(name=name, uri=uri)
        self.library.begin()
        self.library.add(track)
        self.library.close()
        self.assertEqual([track], self.library.lookup(uri))

    def test_add_noname_utf8(self):
        name = u'Mi\xf0vikudags.mp3'
        uri = translator.path_to_local_track_uri(name.encode('utf-8'))
        track = Track(name=name, uri=uri)
        self.library.begin()
        self.library.add(track)
        self.library.close()
        self.assertEqual([track], self.library.lookup(uri))

    def test_clear(self):
        self.library.begin()
        self.library.add(Track(uri='local:track:track.mp3'))
        self.library.close()
        self.library.clear()
        self.assertEqual(self.library.load(), 0)

    def test_search_uri(self):
        empty = SearchResult(uri='local:search?')
        self.assertEqual(empty, self.library.search(uris=None))
        self.assertEqual(empty, self.library.search(uris=[]))
        self.assertEqual(empty, self.library.search(uris=['local:']))
        self.assertEqual(empty, self.library.search(uris=['local:directory']))
        self.assertEqual(empty, self.library.search(uris=['local:directory:']))
        self.assertEqual(empty, self.library.search(uris=['foobar:']))
