from __future__ import annotations

import logging
import os
import urllib
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)


def local_uri_to_file_uri(local_uri: str, media_dir: Path) -> str:
    """Convert local track or directory URI to file URI."""
    path = local_uri_to_path(local_uri, media_dir)
    return path.as_uri()


def local_uri_to_path(local_uri: str, media_dir: Path) -> Path:
    """Convert local track or directory URI to absolute path."""
    if not local_uri.startswith("local:directory:") and not local_uri.startswith(
        "local:track:"
    ):
        raise ValueError("Invalid URI.")
    uri_path = urllib.parse.urlsplit(local_uri.split(":", 2)[2]).path
    file_bytes = urllib.parse.unquote_to_bytes(uri_path)
    file_path = Path(os.fsdecode(file_bytes))
    return media_dir / file_path


def path_to_file_uri(path: Union[str, bytes, Path]) -> str:
    """Convert absolute path to file URI."""
    return Path(os.fsdecode(path)).as_uri()


def path_to_local_track_uri(relpath: Union[str, bytes, Path]) -> str:
    """Convert path relative to :confval:`local/media_dir` to local track
    URI."""
    bytes_path = os.fsencode(relpath)
    return "local:track:%s" % urllib.parse.quote(bytes_path)
