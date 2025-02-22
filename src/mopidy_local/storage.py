import hashlib
import logging
import pathlib
import shutil
import sqlite3
import struct

import uritools

from . import Extension, schema, translator

logger = logging.getLogger(__name__)


def check_dirs_and_files(config):
    if not pathlib.Path(config["local"]["media_dir"]).is_dir():
        logger.warning(
            f"Local media dir {config['local']['media_dir']} does not exist or "
            "we lack permissions to the directory or one of its parents"
        )


def get_image_size_png(data):
    return struct.unpack(">ii", data[16:24])


def get_image_size_gif(data):
    return struct.unpack("<HH", data[6:10])


def model_uri(kind, model):
    if kind == "album":
        # ignore num_tracks for multi-disc albums
        digest = hashlib.md5(str(model.replace(num_tracks=None)).encode())  # noqa: S324
    else:
        digest = hashlib.md5(str(model).encode())  # noqa: S324
    return f"local:{kind}:md5:{digest.hexdigest()}"


def get_image_size_jpeg(data):
    # original source: http://goo.gl/6bo5Vx
    index = 0
    ftype = 0
    size = 2
    while not 0xC0 <= ftype <= 0xCF:  # noqa: PLR2004
        index += size
        ftype = data[index]
        while ftype == 0xFF:  # noqa: PLR2004
            index += 1
            ftype = data[index]
        index += 1
        size = struct.unpack(">H", data[index : index + 2])[0] - 2
        index += 2
    index += 1  # skip precision byte
    height, width = struct.unpack(">HH", data[index : index + 4])
    return width, height


MIN_BYTES_FOR_IMAGE_TYPE = 8


def get_image_type_from_header(header: bytes) -> str:
    # original source: https://github.com/sphinx-doc/sphinx/commit/a502e7

    if len(header) < MIN_BYTES_FOR_IMAGE_TYPE:
        msg = "Unknown image type"
        raise ValueError(msg)

    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"

    if header.startswith((b"GIF87a", b"GIF89a")):
        return "gif"

    if header.startswith(b"\xff\xd8"):
        return "jpeg"

    msg = "Unknown image type"
    raise ValueError(msg)


class LocalStorageProvider:
    def __init__(self, config):
        self._config = ext_config = config[Extension.ext_name]
        self._media_dir = pathlib.Path(ext_config["media_dir"])
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

    def add(self, track, tags=None, duration=None):  # noqa: ARG002
        logger.debug("Adding track: %s", track)
        images = None
        if track.album and track.album.name:  # TODO: album required
            uri = translator.local_uri_to_file_uri(track.uri, self._media_dir)
            try:
                images = self._extract_images(track.uri, tags)
                logger.debug("%s images: %s", track.uri, images)
            except Exception as e:
                logger.warning("Error extracting images for %s: %s", uri, e)
        try:
            track = self._validate_track(track)
            schema.insert_track(self._connect(), track, images)
        except Exception as e:
            logger.warning("Skipped %s: %s", track.uri, e)

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
            shutil.rmtree(self._image_dir)
            self._image_dir.mkdir()
        except OSError as e:
            logger.warning("Error clearing image directory: %s", e)
        logger.info("Clearing SQLite database")
        try:
            schema.clear(self._connect())
        except sqlite3.Error as e:
            logger.error("Error clearing SQLite database: %s", e)
            return False
        else:
            return True

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
            msg = "Empty artist name"
            raise ValueError(msg)
        if not model.uri:
            model = model.replace(uri=model_uri("artist", model))
        return model

    def _validate_album(self, model):
        if not model.name:
            msg = "Empty album name"
            raise ValueError(msg)
        if not model.uri:
            model = model.replace(uri=model_uri("album", model))
        return model.replace(artists=list(map(self._validate_artist, model.artists)))

    def _validate_track(self, model):
        if not model.uri:
            msg = "Empty track URI"
            raise ValueError(msg)
        if model.name:
            name = model.name
        else:
            name = translator.local_uri_to_path(model.uri, pathlib.Path()).name
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
        for image_path in self._image_dir.glob("**/*"):
            if uritools.urijoin(self._base_uri, image_path.name) not in uris:
                logger.info(f"Deleting file {image_path.as_uri()}")
                image_path.unlink()

    def _extract_images(self, uri, tags):
        images = set()  # filter duplicate images, e.g. embedded/external
        for image in tags.get("image", []) + tags.get("preview-image", []):
            try:
                # TODO: Is this a gst.Buffer or plain str/bytes type?
                data = getattr(image, "data", image)
                images.add(self._image_from_embedded_data(data))
            except Exception as e:
                logger.warning("Error extracting images for %r: %r", uri, e)
        # look for external album art
        track_path = translator.local_uri_to_path(uri, self._media_dir)
        dir_path = track_path.parent
        for pattern in self._patterns:
            for match_path in dir_path.glob(pattern):
                try:
                    images.add(self._image_from_path(match_path))
                except Exception as e:
                    logger.warning(
                        f"Cannot read image file {match_path.as_uri()}: {e!r}",
                    )
        return images

    def _image_from_path(self, path: pathlib.Path):
        with path.open("rb") as f:
            header = f.read(MIN_BYTES_FOR_IMAGE_TYPE)
            data = header + f.read()
        return self._save_image(
            data=data,
            source=path.as_uri(),
            what=get_image_type_from_header(header),
        )

    def _image_from_embedded_data(self, data: bytes):
        header = data[:MIN_BYTES_FOR_IMAGE_TYPE]
        return self._save_image(
            data=data,
            source="embedded image",
            what=get_image_type_from_header(header),
        )

    def _save_image(self, *, data: bytes, source: str, what: str):
        digest = hashlib.md5(data).hexdigest()  # noqa: S324
        width, height = None, None
        try:
            if what == "png":
                width, height = get_image_size_png(data)
            elif what == "gif":
                width, height = get_image_size_gif(data)
            elif what == "jpeg":
                width, height = get_image_size_jpeg(data)
        except Exception as e:
            logger.error("Error getting image size for %r: %r", source, e)
        if width and height:
            name = f"{digest}-{width}x{height}.{what}"
        else:
            name = f"{digest}.{what}"
        image_path = self._image_dir / name
        if not image_path.is_file():
            logger.info(f"Creating file {image_path.as_uri()} from {source}")
            image_path.write_bytes(data)
        return uritools.urijoin(self._base_uri, name)
