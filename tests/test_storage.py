import pytest

from mopidy_local import storage


def test_get_image_type_from_header_png():
    data_bytes = b"\x89PNG\r\n\x1a\nffe000104a464"
    assert storage.get_image_type_from_header(data_bytes) == "png"


@pytest.mark.parametrize(
    "data",
    [
        pytest.param("474946383761ffe000104a46", id="GIF87a"),
        pytest.param("474946383961ffe000104a46", id="GIF89a"),
    ],
)
def test_get_image_type_from_header_gif(data):
    data_bytes = bytes.fromhex(data)
    assert storage.get_image_type_from_header(data_bytes) == "gif"


@pytest.mark.parametrize(
    "data",
    [
        pytest.param("ffd8ffe000104a46494600", id="JFIF"),
        pytest.param("ffd8ffe100184578696600", id="Exif"),
        pytest.param("ffd8ffe1095068747470", id="XMP"),
    ],
)
def test_get_image_type_from_header_jpeg(data):
    data_bytes = bytes.fromhex(data)
    assert storage.get_image_type_from_header(data_bytes) == "jpeg"


def test_get_image_type_from_header_unknown_header():
    data_bytes = b"PIF81affe000104a464"
    with pytest.raises(ValueError):
        storage.get_image_type_from_header(data_bytes)


def test_get_image_type_from_header_too_short_header():
    data_bytes = b"\xff"
    with pytest.raises(ValueError):
        storage.get_image_type_from_header(data_bytes)
