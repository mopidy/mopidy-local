import pytest

from mopidy_local import storage


@pytest.mark.parametrize(
    "data",
    [
        pytest.param("ffd8ffe000104a46494600", id="JFIF"),
        pytest.param("ffd8ffe100184578696600", id="Exif"),
        pytest.param("ffd8ffe1095068747470", id="XMP"),
    ],
)
def test_jpeg_detection(data):
    data_bytes = bytes.fromhex(data)
    assert storage.imghdr.what(None, data_bytes) is not None
