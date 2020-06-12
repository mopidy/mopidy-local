import logging
import operator
import sqlite3

import uritools
from mopidy import backend, models
from mopidy.models import Ref, SearchResult

from . import Extension, schema

logger = logging.getLogger(__name__)


def date_ref(date):
    return Ref.directory(
        uri=uritools.uricompose("local", None, "directory", {"date": date}), name=date
    )


def genre_ref(genre):
    return Ref.directory(
        uri=uritools.uricompose("local", None, "directory", {"genre": genre}),
        name=genre,
    )


class LocalLibraryProvider(backend.LibraryProvider):

    ROOT_DIRECTORY_URI = "local:directory"

    root_directory = models.Ref.directory(uri=ROOT_DIRECTORY_URI, name="Local media")

    def __init__(self, backend, config):
        super().__init__(backend)
        self._config = ext_config = config[Extension.ext_name]
        self._data_dir = Extension.get_data_dir(config)
        self._directories = []
        for line in ext_config["directories"]:
            name, uri = line.rsplit(None, 1)
            ref = Ref.directory(uri=uri, name=name)
            self._directories.append(ref)
        self._dbpath = self._data_dir / "library.db"
        self._connection = None

    def load(self):
        with self._connect() as connection:
            version = schema.load(connection)
            logger.debug("Using SQLite database schema v%s", version)
            return schema.count_tracks(connection)

    def lookup(self, uri):
        try:
            if uri.startswith("local:album"):
                return list(schema.lookup(self._connect(), Ref.ALBUM, uri))
            elif uri.startswith("local:artist"):
                return list(schema.lookup(self._connect(), Ref.ARTIST, uri))
            elif uri.startswith("local:track"):
                return list(schema.lookup(self._connect(), Ref.TRACK, uri))
            else:
                raise ValueError("Invalid lookup URI")
        except Exception as e:
            logger.error("Lookup error for %s: %s", uri, e)
            return []

    def browse(self, uri):
        try:
            if uri == self.ROOT_DIRECTORY_URI:
                return self._directories
            elif uri.startswith("local:directory"):
                return self._browse_directory(uri)
            elif uri.startswith("local:artist"):
                return self._browse_artist(uri)
            elif uri.startswith("local:album"):
                return self._browse_album(uri)
            else:
                raise ValueError("Invalid browse URI")
        except Exception as e:
            logger.error("Error browsing %s: %s", uri, e)
            return []

    def search(self, query=None, limit=100, offset=0, uris=None, exact=False):
        limit = self._config["max_search_results"]
        q = []
        for field, values in query.items() if query else []:
            q.extend((field, value) for value in values)
        filters = [f for uri in uris or [] for f in self._filters(uri) if f]
        with self._connect() as c:
            tracks = schema.search_tracks(c, q, limit, offset, exact, filters)
        uri = uritools.uricompose("local", path="search", query=q)
        return SearchResult(uri=uri, tracks=tracks)

    def get_images(self, uris):
        images = {}
        with self._connect() as c:
            for uri in uris:
                if uri.startswith("local:album"):
                    images[uri] = schema.get_album_images(c, uri)
                elif uri.startswith("local:track"):
                    images[uri] = schema.get_track_images(c, uri)
        return images

    def get_distinct(self, field, query=None):
        q = []
        for key, values in query.items() if query else []:
            q.extend((key, value) for value in values)
        # Gracefully handle both old and new field values for this API.
        compat_field = {"track": "track_name"}.get(field, field)
        return set(schema.list_distinct(self._connect(), compat_field, q))

    def _connect(self):
        if not self._connection:
            self._connection = sqlite3.connect(
                self._dbpath,
                factory=schema.Connection,
                timeout=self._config["timeout"],
                check_same_thread=False,
            )
        return self._connection

    def _browse_album(self, uri, order=("disc_no", "track_no", "name")):
        return schema.browse(self._connect(), Ref.TRACK, order, album=uri)

    def _browse_artist(self, uri, order=("type", "name COLLATE NOCASE")):
        with self._connect() as c:
            albums = schema.browse(c, Ref.ALBUM, order, albumartist=uri)
            refs = schema.browse(c, order=order, artist=uri)
        album_uris, tracks = {ref.uri for ref in albums}, []
        for ref in refs:
            if ref.type == Ref.ALBUM and ref.uri not in album_uris:
                albums.append(
                    Ref.directory(
                        uri=uritools.uricompose(
                            "local",
                            None,
                            "directory",
                            dict(type=Ref.TRACK, album=ref.uri, artist=uri),
                        ),
                        name=ref.name,
                    )
                )
            elif ref.type == Ref.TRACK:
                tracks.append(ref)
            else:
                logger.debug("Skipped SQLite browse result %s", ref.uri)
        albums.sort(key=operator.attrgetter("name"))
        return albums + tracks

    def _browse_directory(self, uri, order=("type", "name COLLATE NOCASE")):
        query = dict(uritools.urisplit(uri).getquerylist())
        type = query.pop("type", None)
        role = query.pop("role", None)

        # TODO: handle these in schema (generically)?
        if type == "date":
            format = query.get("format", "%Y-%m-%d")
            return list(map(date_ref, schema.dates(self._connect(), format=format)))
        if type == "genre":
            return list(map(genre_ref, schema.list_distinct(self._connect(), "genre")))

        # Fix #38: keep sort order of album tracks; this also applies
        # to composers and performers
        if type == Ref.TRACK and "album" in query:
            order = ("disc_no", "track_no", "name")
        if type == Ref.ARTIST and self._config["use_artist_sortname"]:
            order = ("coalesce(sortname, name) COLLATE NOCASE",)
        roles = role or ("artist", "albumartist")  # FIXME: re-think 'roles'...

        refs = []
        for ref in schema.browse(
            self._connect(), type, order, role=roles, **query
        ):  # noqa
            if ref.type == Ref.TRACK or (not query and not role):
                refs.append(ref)
            elif ref.type == Ref.ALBUM:
                refs.append(
                    Ref.directory(
                        uri=uritools.uricompose(
                            "local",
                            None,
                            "directory",
                            dict(query, type=Ref.TRACK, album=ref.uri),  # noqa
                        ),
                        name=ref.name,
                    )
                )
            elif ref.type == Ref.ARTIST:
                refs.append(
                    Ref.directory(
                        uri=uritools.uricompose(
                            "local", None, "directory", dict(query, **{role: ref.uri})
                        ),
                        name=ref.name,
                    )
                )
            else:
                logger.warning("Unexpected SQLite browse result: %r", ref)
        return refs

    def _filters(self, uri):
        if uri.startswith("local:directory"):
            return [dict(uritools.urisplit(uri).getquerylist())]
        elif uri.startswith("local:artist"):
            return [{"artist": uri}, {"albumartist": uri}]
        elif uri.startswith("local:album"):
            return [{"album": uri}]
        else:
            return []
