from __future__ import unicode_literals

import logging
import os

import tornado.web

logger = logging.getLogger(__name__)


class ImageHandler(tornado.web.StaticFileHandler):

    def get_cache_time(self, *args):
        return self.CACHE_MAX_AGE


class IndexHandler(tornado.web.RequestHandler):

    def initialize(self, root):
        self.root = root

    def get(self, path):
        return self.render('index.html', images=self.uris())

    def get_template_path(self):
        return os.path.join(os.path.dirname(__file__), 'www')

    def uris(self):
        for _, _, files in os.walk(self.root):
            for name in files:
                yield name
