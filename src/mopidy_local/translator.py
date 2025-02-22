from __future__ import annotations

import logging
import os
import urllib.parse
from pathlib import Path

from mopidy.types import Uri

logger = logging.getLogger(__name__)


def local_uri_to_file_uri(local_uri: str, media_dir: Path) -> Uri:
    """Convert local track or directory URI to file URI."""
    path = local_uri_to_path(local_uri, media_dir)
    return Uri(path.as_uri())


def local_uri_to_path(local_uri: str, media_dir: Path) -> Path:
    """Convert local track or directory URI to absolute path."""
    if not local_uri.startswith(("local:directory:", "local:track:")):
        msg = "Invalid URI."
        raise ValueError(msg)
    uri_path = urllib.parse.urlsplit(local_uri.split(":", 2)[2]).path
    file_bytes = urllib.parse.unquote_to_bytes(uri_path)
    file_path = Path(os.fsdecode(file_bytes))
    return media_dir / file_path


def path_to_file_uri(path: str | bytes | Path) -> str:
    """Convert absolute path to file URI."""
    ppath = Path(os.fsdecode(path))
    if not ppath.is_absolute():
        msg = "Path must be absolute"
        raise ValueError(msg)
    return ppath.as_uri()


def path_to_local_track_uri(path: str | bytes | Path, media_dir: Path) -> str:
    """Convert path to local track URI."""
    ppath = Path(os.fsdecode(path))
    if ppath.is_absolute():
        ppath = ppath.relative_to(media_dir)
    quoted_path = urllib.parse.quote(bytes(ppath))
    return f"local:track:{quoted_path}"
