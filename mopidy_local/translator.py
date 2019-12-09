import logging
import os
import pathlib
import urllib

logger = logging.getLogger(__name__)


def local_uri_to_file_uri(uri, media_dir):
    """Convert local track or directory URI to file URI."""
    return path_to_file_uri(local_uri_to_path(uri, media_dir))


def local_uri_to_path(uri, media_dir):
    """Convert local track or directory URI to absolute path."""
    if not uri.startswith("local:directory:") and not uri.startswith("local:track:"):
        raise ValueError("Invalid URI.")
    uri_path = uri.split(":", 2)[2]
    file_bytes = urllib.parse.unquote_to_bytes(urllib.parse.urlsplit(uri_path).path)
    file_path = pathlib.Path(os.fsdecode(file_bytes))
    return media_dir / file_path


def path_to_file_uri(path):
    """Convert absolute path to file URI."""
    return pathlib.Path(os.fsdecode(path)).as_uri()


def path_to_local_track_uri(relpath):
    """Convert path relative to :confval:`local/media_dir` to local track
    URI."""
    if isinstance(relpath, str):
        relpath = relpath.encode()
    return "local:track:%s" % urllib.parse.quote(relpath)


def path_to_local_directory_uri(relpath):
    """Convert path relative to :confval:`local/media_dir` to directory URI."""
    if isinstance(relpath, str):
        relpath = relpath.encode()
    return "local:directory:%s" % urllib.parse.quote(relpath)
