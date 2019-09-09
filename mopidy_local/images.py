from __future__ import absolute_import, unicode_literals

import glob
import hashlib
import imghdr
import logging
import os
import os.path
import re
import struct

import uritools

from mopidy.audio import scan
from mopidy.exceptions import ExtensionError

from . import Extension, Library, translator

logger = logging.getLogger(__name__)


# would be nice to have these in imghdr...
def get_image_size_png(data):
    return struct.unpack(str('>ii'), data[16:24])


def get_image_size_gif(data):
    return struct.unpack(str('<HH'), data[6:10])


def get_image_size_jpeg(data):
    # original source: http://goo.gl/6bo5Vx
    index = 0
    ftype = 0
    size = 2
    while not 0xc0 <= ftype <= 0xcf:
        index += size
        ftype = ord(data[index])
        while ftype == 0xff:
            index += 1
            ftype = ord(data[index])
        index += 1
        size = struct.unpack(str('>H'), data[index:index+2])[0] - 2
        index += 2
    index += 1  # skip precision byte
    height, width = struct.unpack(str('>HH'), data[index:index+4])
    return width, height


class ImageLibrary(Library):

    name = 'images'

    add_supports_tags_and_duration = True

    libraries = []

    _image_size_re = re.compile(r'.*-(\d+)x(\d+)\.(?:png|gif|jpeg)$')

    def __init__(self, config):
        ext_config = config[Extension.ext_name]
        libname = ext_config['library']

        try:
            lib = next(lib for lib in self.libraries if lib.name == libname)
            self.library = lib(config)
        except StopIteration:
            raise ExtensionError('Local library %s not found' % libname)
        logger.debug('Using %s as the local library', libname)

        try:
            self.media_dir = config['local']['media_dir']
        except KeyError:
            raise ExtensionError('Mopidy-Local not enabled')
        self.base_uri = ext_config['base_uri']
        if ext_config['image_dir']:
            self.image_dir = ext_config['image_dir']
        else:
            self.image_dir = Extension.get_data_subdir(config, b'images')
        self.patterns = list(map(str, ext_config['album_art_files']))
        self.scanner = scan.Scanner(config['local']['scan_timeout'])

    def load(self):
        return self.library.load()

    def browse(self, uri):
        return self.library.browse(uri)

    def get_distinct(self, field, query=None):
        return self.library.get_distinct(field, query)

    def get_images(self, uris):
        images = self.library.get_images(uris)
        for uri in images:
            images[uri] = list(map(self._normalize_image, images[uri]))
        return images

    def lookup(self, uri):
        return self.library.lookup(uri)

    def search(self, query=None, limit=100, offset=0, uris=None, exact=False):
        return self.library.search(query, limit, offset, uris, exact)

    def begin(self):
        logger.info('Start image scan')
        return self.library.begin()

    def add(self, track, tags=None, duration=None):
        if track.album and track.album.name:  # FIXME: album required
            uri = translator.local_uri_to_file_uri(track.uri, self.media_dir)
            try:
                if tags is None:
                    images = self._extract_images(track.uri, self._scan(uri))
                else:
                    images = self._extract_images(track.uri, tags)
                logger.debug('%s images: %s', track.uri, images)
                # FIXME: Album.images removed, copy no longer available
                # album = track.album.copy(images=images)
                # track = track.copy(album=album)
            except Exception as e:
                logger.warn('Error extracting images for %s: %s', uri, e)
        if getattr(self.library, 'add_supports_tags_and_duration', False):
            self.library.add(track, tags, duration)
        else:
            self.library.add(track)

    def remove(self, uri):
        self.library.remove(uri)

    def flush(self):
        return self.library.flush()

    def close(self):
        self.library.close()
        self._cleanup()

    def clear(self):
        try:
            for root, dirs, files in os.walk(self.image_dir, topdown=False):
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
                for name in files:
                    os.remove(os.path.join(root, name))
        except Exception as e:
            logger.warn('Error clearing image directory: %s', e)
        return self.library.clear()

    def _cleanup(self):
        logger.info('Cleaning up image directory')
        # uris = set()
        # FIXME: Album.images removed
        # for track in self.library.begin():
        #     if track.album and track.album.images:
        #         uris.update(track.album.images)
        self.library.close()

        # TODO: get from SQLite
        # for root, _, files in os.walk(self.image_dir):
        #     for name in files:
        #         if uritools.urijoin(self.base_uri, name) not in uris:
        #             path = os.path.join(root, name)
        #             logger.info('Deleting file %s', path)
        #             os.remove(path)

    def _normalize_image(self, image):
        if image.width or image.height:
            return image
        m = self._image_size_re.match(image.uri)
        if m:
            return image.copy(width=int(m.group(1)), height=int(m.group(2)))
        else:
            return image

    def _extract_images(self, uri, tags):
        images = set()  # filter duplicate images, e.g. embedded/external
        for image in tags.get('image', []) + tags.get('preview-image', []):
            try:
                # FIXME: gst.Buffer or plain str/bytes type?
                data = getattr(image, 'data', image)
                images.add(self._get_or_create_image_file(None, data))
            except Exception as e:
                logger.warn('Error extracting images for %r: %r', uri, e)
        # look for external album art
        path = translator.local_uri_to_path(uri, self.media_dir)
        dirname = os.path.dirname(path)
        for pattern in self.patterns:
            for path in glob.glob(os.path.join(dirname, pattern)):
                try:
                    images.add(self._get_or_create_image_file(path))
                except Exception as e:
                    logger.warn('Cannot read image file %r: %r', path, e)
        return images

    def _get_or_create_image_file(self, path, data=None):
        what = imghdr.what(path, data)
        if not what:
            raise ValueError('Unknown image type')
        if not data:
            data = open(path).read()
        digest, width, height = hashlib.md5(data).hexdigest(), None, None
        try:
            if what == 'png':
                width, height = get_image_size_png(data)
            elif what == 'gif':
                width, height = get_image_size_gif(data)
            elif what == 'jpeg':
                width, height = get_image_size_jpeg(data)
        except Exception as e:
            logger.error('Error getting image size for %r: %r', path, e)
        if width and height:
            name = '%s-%dx%d.%s' % (digest, width, height, what)
        else:
            name = '%s.%s' % (digest, what)
        dest = os.path.join(self.image_dir, name)
        if not os.path.isfile(dest):
            logger.info('Creating file %s', dest)
            with open(dest, 'wb') as fh:
                fh.write(data)
        return uritools.urijoin(self.base_uri, name)

    def _scan(self, uri):
        logger.debug('Scanning %s for images', uri)
        data = self.scanner.scan(uri)
        return data.get('tags', {})
