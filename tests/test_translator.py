import os
import pathlib

import pytest

from mopidy_local import translator


@pytest.mark.parametrize(
    ("local_uri", "file_uri"),
    [
        ("local:directory:A/B", "file:///home/alice/Music/A/B"),
        ("local:directory:A%20B", "file:///home/alice/Music/A%20B"),
        ("local:directory:A+B", "file:///home/alice/Music/A%2BB"),
        (
            "local:directory:%C3%A6%C3%B8%C3%A5",
            "file:///home/alice/Music/%C3%A6%C3%B8%C3%A5",
        ),
        ("local:track:A/B.mp3", "file:///home/alice/Music/A/B.mp3"),
        ("local:track:A%20B.mp3", "file:///home/alice/Music/A%20B.mp3"),
        ("local:track:A+B.mp3", "file:///home/alice/Music/A%2BB.mp3"),
        (
            "local:track:%C3%A6%C3%B8%C3%A5.mp3",
            "file:///home/alice/Music/%C3%A6%C3%B8%C3%A5.mp3",
        ),
    ],
)
def test_local_uri_to_file_uri(local_uri, file_uri):
    media_dir = pathlib.Path("/home/alice/Music")

    assert translator.local_uri_to_file_uri(local_uri, media_dir) == file_uri


@pytest.mark.parametrize("uri", ["A/B", "local:foo:A/B"])
def test_local_uri_to_file_uri_errors(uri):
    media_dir = pathlib.Path("/home/alice/Music")

    with pytest.raises(ValueError):
        translator.local_uri_to_file_uri(uri, media_dir)


@pytest.mark.parametrize(
    ("uri", "path"),
    [
        ("local:directory:A/B", b"/home/alice/Music/A/B"),
        ("local:directory:A%20B", b"/home/alice/Music/A B"),
        ("local:directory:A+B", b"/home/alice/Music/A+B"),
        (
            "local:directory:%C3%A6%C3%B8%C3%A5",
            b"/home/alice/Music/\xc3\xa6\xc3\xb8\xc3\xa5",
        ),
        ("local:track:A/B.mp3", b"/home/alice/Music/A/B.mp3"),
        ("local:track:A%20B.mp3", b"/home/alice/Music/A B.mp3"),
        ("local:track:A+B.mp3", b"/home/alice/Music/A+B.mp3"),
        (
            "local:track:%C3%A6%C3%B8%C3%A5.mp3",
            b"/home/alice/Music/\xc3\xa6\xc3\xb8\xc3\xa5.mp3",
        ),
    ],
)
def test_local_uri_to_path(uri, path):
    media_dir = pathlib.Path("/home/alice/Music")

    result = translator.local_uri_to_path(uri, media_dir)

    assert isinstance(result, pathlib.Path)
    assert bytes(result) == path


@pytest.mark.parametrize("uri", ["A/B", "local:foo:A/B"])
def test_local_uri_to_path_errors(uri):
    media_dir = pathlib.Path("/home/alice/Music")

    with pytest.raises(ValueError):
        translator.local_uri_to_path(uri, media_dir)


@pytest.mark.parametrize(
    ("path", "uri"),
    [
        ("/foo", "file:///foo"),
        (b"/foo", "file:///foo"),
        ("/æøå", "file:///%C3%A6%C3%B8%C3%A5"),
        (b"/\x00\x01\x02", "file:///%00%01%02"),
        (pathlib.Path("/æøå"), "file:///%C3%A6%C3%B8%C3%A5"),
    ],
)
def test_path_to_file_uri(path, uri):
    assert translator.path_to_file_uri(path) == uri


@pytest.mark.parametrize(
    ("path", "uri"),
    [
        (pathlib.Path("foo"), "local:track:foo"),
        (pathlib.Path("/home/alice/Music/foo"), "local:track:foo"),
        (pathlib.Path("æøå"), "local:track:%C3%A6%C3%B8%C3%A5"),
        (pathlib.Path(os.fsdecode(b"\x00\x01\x02")), "local:track:%00%01%02"),
    ],
)
def test_path_to_local_track_uri(path, uri):
    media_dir = pathlib.Path("/home/alice/Music")

    result = translator.path_to_local_track_uri(path, media_dir)

    assert isinstance(result, str)
    assert result == uri
