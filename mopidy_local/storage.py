import glob
import hashlib
import imghdr
import logging
import os
import os.path
import sqlite3
import struct

import uritools

from . import Extension, schema, translator

logger = logging.getLogger(__name__)


def check_dirs_and_files(config):
    if not os.path.isdir(config["local"]["media_dir"]):
        logger.warning(
            "Local media dir %s does not exist or we lack permissions to the "
            "directory or one of its parents" % config["local"]["media_dir"]
        )


# would be nice to have these in imghdr...
def get_image_size_png(data):
    return struct.unpack(">ii", data[16:24])


def get_image_size_gif(data):
    return struct.unpack("<HH", data[6:10])


def get_image_size_jpeg(data):
    # original source: http://goo.gl/6bo5Vx
    index = 0
    ftype = 0
    size = 2
    while not 0xC0 <= ftype <= 0xCF:
        index += size
        ftype = data[index]
        while ftype == 0xFF:
            index += 1
            ftype = data[index]
        index += 1
        size = struct.unpack(">H", data[index : index + 2])[0] - 2
        index += 2
    index += 1  # skip precision byte
    height, width = struct.unpack(">HH", data[index : index + 4])
    return width, height


class LocalStorageProvider:
    def __init__(self, config):
        self._config = ext_config = config[Extension.ext_name]
        self._media_dir = ext_config["media_dir"]
        self._data_dir = Extension.get_data_dir(config)
        self._image_dir = Extension.get_image_dir(config)
        self._base_uri = "/" + Extension.ext_name + "/"
        self._patterns = list(map(str, ext_config["album_art_files"]))
        self._dbpath = self._data_dir / "library.db"
        self._connection = None

    def load(self):
        with self._connect() as connection:
            version = schema.load(connection)
            logger.debug("Using SQLite database schema v%s", version)
            return schema.count_tracks(connection)

    def begin(self):
        return schema.tracks(self._connect())

    def add(self, track, tags=None, duration=None):
        logger.info("Adding track: %s", track)
        images = None
        if track.album and track.album.name:  # FIXME: album required
            uri = translator.local_uri_to_file_uri(track.uri, self._media_dir)
            try:
                images = self._extract_images(track.uri, tags)
                logger.debug("%s images: %s", track.uri, images)
            except Exception as e:
                logger.warn("Error extracting images for %s: %s", uri, e)
        try:
            track = self._validate_track(track)
            schema.insert_track(self._connect(), track, images)
        except Exception as e:
            logger.warn("Skipped %s: %s", track.uri, e)

    def remove(self, uri):
        schema.delete_track(self._connect(), uri)

    def flush(self):
        if not self._connection:
            return False
        self._connection.commit()
        return True

    def close(self):
        if self._connection:
            schema.cleanup(self._connection)
            self._connection.commit()
            self._connection.close()
            self._connection = None
        else:
            logger.error("Attempting to close while not connected")
        self._cleanup_images()

    def clear(self):
        logger.info("Clearing image directory")
        try:
            for root, dirs, files in os.walk(self._image_dir, topdown=False):
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
                for name in files:
                    os.remove(os.path.join(root, name))
        except Exception as e:
            logger.warn("Error clearing image directory: %s", e)
        logger.info("Clearing SQLite database")
        try:
            schema.clear(self._connect())
            return True
        except sqlite3.Error as e:
            logger.error("Error clearing SQLite database: %s", e)
            return False

    def _connect(self):
        if not self._connection:
            self._connection = sqlite3.connect(
                self._dbpath,
                factory=schema.Connection,
                timeout=self._config["timeout"],
                check_same_thread=False,
            )
        return self._connection

    def _validate_artist(self, model):
        if not model.name:
            raise ValueError("Empty artist name")
        if not model.uri:
            model = model.replace(uri=self._model_uri("artist", model))
        return model

    def _validate_album(self, model):
        if not model.name:
            raise ValueError("Empty album name")
        if not model.uri:
            model = model.replace(uri=self._model_uri("album", model))
        return model.replace(artists=list(map(self._validate_artist, model.artists)))

    def _validate_track(self, model):
        if not model.uri:
            raise ValueError("Empty track URI")
        if model.name:
            name = model.name
        else:
            name = translator.local_uri_to_path(model.uri, "").name
        if model.album and model.album.name:
            album = self._validate_album(model.album)
        else:
            album = None
        return model.replace(
            name=name,
            album=album,
            artists=list(map(self._validate_artist, model.artists)),
            composers=list(map(self._validate_artist, model.composers)),
            performers=list(map(self._validate_artist, model.performers)),
        )

    def _cleanup_images(self):
        logger.info("Cleaning up image directory")
        with self._connect() as c:
            uris = set(schema.get_image_uris(c))
        for root, _, files in os.walk(self._image_dir):
            for name in files:
                if uritools.urijoin(self._base_uri, name) not in uris:
                    path = os.path.join(root, name)
                    logger.info("Deleting file %s", path)
                    os.remove(path)

    def _extract_images(self, uri, tags):
        images = set()  # filter duplicate images, e.g. embedded/external
        for image in tags.get("image", []) + tags.get("preview-image", []):
            try:
                # FIXME: gst.Buffer or plain str/bytes type?
                data = getattr(image, "data", image)
                images.add(self._get_or_create_image_file(None, data))
            except Exception as e:
                logger.warn("Error extracting images for %r: %r", uri, e)
        # look for external album art
        path = translator.local_uri_to_path(uri, self._media_dir)
        # replace brackets with character classes for use with glob
        dirname = os.path.dirname(path).replace("[", "[[]")
        for pattern in self._patterns:
            for path in glob.glob(os.path.join(dirname, pattern)):
                try:
                    images.add(self._get_or_create_image_file(path))
                except Exception as e:
                    logger.warn("Cannot read image file %r: %r", path, e)
        return images

    def _get_or_create_image_file(self, path, data=None):
        what = imghdr.what(path, data)
        if not what:
            raise ValueError("Unknown image type")
        if not data:
            with open(path, "rb") as f:
                data = f.read()
        digest, width, height = hashlib.md5(data).hexdigest(), None, None
        try:
            if what == "png":
                width, height = get_image_size_png(data)
            elif what == "gif":
                width, height = get_image_size_gif(data)
            elif what == "jpeg":
                width, height = get_image_size_jpeg(data)
        except Exception as e:
            logger.error("Error getting image size for %r: %r", path, e)
        if width and height:
            name = "%s-%dx%d.%s" % (digest, width, height, what)
        else:
            name = f"{digest}.{what}"
        dest = os.path.join(self._image_dir, name)
        if not os.path.isfile(dest):
            logger.info("Creating file %s", dest)
            with open(dest, "wb") as fh:
                fh.write(data)
        return uritools.urijoin(self._base_uri, name)

    def _model_uri(self, type, model):
        # only use valid mbids; TODO: use regex for that?
        if model.musicbrainz_id and len(model.musicbrainz_id) == 36
           and self._config["use_%s_mbid_uri" % type]:
            return f"local:{type}:mbid:{model.musicbrainz_id}"
        elif type == "album":
            # ignore num_tracks for multi-disc albums
            digest = hashlib.md5(str(model.replace(num_tracks=None)).encode())
        else:
            digest = hashlib.md5(str(model).encode())
        return "local:{}:md5:{}".format(type, digest.hexdigest())
