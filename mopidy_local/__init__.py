from __future__ import absolute_import, unicode_literals

import logging
import os

from mopidy import config, ext


__version__ = "3.0.0a1"


logger = logging.getLogger(__name__)


class Extension(ext.Extension):

    dist_name = 'Mopidy-Local'
    ext_name = 'local'
    version = __version__

    def get_default_config(self):
        conf_file = os.path.join(os.path.dirname(__file__), 'ext.conf')
        return config.read(conf_file)

    def get_config_schema(self):
        schema = super(Extension, self).get_config_schema()
        schema['library'] = config.Deprecated()
        schema['media_dir'] = config.Path()
        schema['data_dir'] = config.Deprecated()
        schema['playlists_dir'] = config.Deprecated()
        schema['tag_cache_file'] = config.Deprecated()
        schema['scan_timeout'] = config.Integer(
            minimum=1000, maximum=1000 * 60 * 60)
        schema['scan_flush_threshold'] = config.Integer(minimum=0)
        schema['scan_follow_symlinks'] = config.Boolean()
        schema['excluded_file_extensions'] = config.List(optional=True)
        # from mopidy-local-images
        schema['base_uri'] = config.String(optional=True)
        schema['image_dir'] = config.String(optional=True)
        schema['album_art_files'] = config.List(optional=True)
        # from mopidy-local-sqlite
        schema['directories'] = config.List()
        schema['timeout'] = config.Integer(optional=True, minimum=1)
        schema['use_album_mbid_uri'] = config.Boolean()
        schema['use_artist_mbid_uri'] = config.Boolean()
        schema['use_artist_sortname'] = config.Boolean()
        return schema

    def setup(self, registry):
        from .actor import LocalBackend
        LocalBackend.libraries = registry['local:library']
        registry.add('backend', LocalBackend)
        registry.add('http:app', {'name': 'images', 'factory': self.webapp})

    def get_command(self):
        from .commands import LocalCommand
        return LocalCommand()

    # from mopidy-local-images
    def webapp(self, config, core):
        from .web import ImageHandler, IndexHandler
        if config[self.ext_name]['image_dir']:
            image_dir = config[self.ext_name]['image_dir']
        else:
            image_dir = self.get_data_subdir(config, b'images')
        return [
            (r'/(index.html)?', IndexHandler, {'root': image_dir}),
            (r'/(.+)', ImageHandler, {'path': image_dir})
        ]

    # TODO: Extension.get_data_dir() with optional sub-path(s)?
    @classmethod
    def get_data_subdir(cls, config, *paths):
        from mopidy.internal import path
        data_dir = cls.get_data_dir(config)
        dir_path = os.path.join(data_dir, *paths)
        path.get_or_create_dir(dir_path)
        return dir_path
