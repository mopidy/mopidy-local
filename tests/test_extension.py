from mopidy_local import Extension


def test_get_default_config():
    ext = Extension()

    config = ext.get_default_config()

    assert "[local]" in config
    assert "enabled = true" in config


def test_get_config_schema():
    ext = Extension()

    schema = ext.get_config_schema()

    assert "library" in schema
    assert "media_dir" in schema
    assert "data_dir" in schema
    assert "playlists_dir" in schema
    assert "tag_cache_file" in schema
    assert "scan_timeout" in schema
    assert "scan_flush_threshold" in schema
    assert "scan_follow_symlinks" in schema
    assert "included_file_extensions" in schema
    assert "excluded_file_extensions" in schema
    # from mopidy-local-sqlite
    assert "directories" in schema
    assert "timeout" in schema
    assert "use_artist_sortname" in schema
    # from mopidy-local-images
    assert "album_art_files" in schema
