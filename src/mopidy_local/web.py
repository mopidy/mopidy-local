import logging
import os
import pathlib

import tornado.web

logger = logging.getLogger(__name__)


class ImageHandler(tornado.web.StaticFileHandler):
    def get_cache_time(self, *_args, **_kwargs):
        return self.CACHE_MAX_AGE


class IndexHandler(tornado.web.RequestHandler):
    def initialize(self, root):
        self.root = root

    def get(self, _path):
        return self.render("index.html", images=self.uris())

    def get_template_path(self) -> str | None:
        return str(pathlib.Path(__file__).parent / "www")

    def uris(self):
        for _, _, files in os.walk(self.root):
            yield from files
