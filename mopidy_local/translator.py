import logging
import os
import pathlib
import urllib

logger = logging.getLogger(__name__)


def local_uri_to_file_uri(local_uri, media_dir):
    """Convert local track or directory URI to file URI."""
    return path_to_file_uri(local_uri_to_path(local_uri, media_dir))


def local_uri_to_path(local_uri, media_dir):
    """Convert local track or directory URI to absolute path."""
    if not local_uri.startswith("local:directory:") and not local_uri.startswith(
        "local:track:"
    ):
        raise ValueError("Invalid URI.")
    uri_path = urllib.parse.urlsplit(local_uri.split(":", 2)[2]).path
    file_bytes = urllib.parse.unquote_to_bytes(uri_path)
    file_path = pathlib.Path(os.fsdecode(file_bytes))
    return media_dir / file_path


def path_to_file_uri(path):
    """Convert absolute path to file URI."""
    return pathlib.Path(os.fsdecode(path)).as_uri()


def path_to_local_track_uri(relpath):
    """Convert path relative to :confval:`local/media_dir` to local track
    URI."""
    return "local:track:%s" % urllib.parse.quote(os.fsencode(relpath))
