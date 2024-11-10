-- Mopidy-Local-SQLite schema

BEGIN EXCLUSIVE TRANSACTION;

PRAGMA user_version = 7;                -- schema version

CREATE TABLE artist (
    uri             TEXT PRIMARY KEY,   -- artist URI
    name            TEXT NOT NULL,      -- artist name
    sortname        TEXT,               -- artist name for sorting
    musicbrainz_id  TEXT                -- MusicBrainz ID
);

CREATE TABLE album (
    uri             TEXT PRIMARY KEY,   -- album URI
    name            TEXT NOT NULL,      -- album name
    artists         TEXT,               -- (list of Artist) album artists
    num_tracks      INTEGER,            -- number of tracks in album
    num_discs       INTEGER,            -- number of discs in album
    date            TEXT,               -- album release date (YYYY or YYYY-MM-DD)
    musicbrainz_id  TEXT,               -- MusicBrainz ID
    images          TEXT,               -- (list of strings) album image URIs
    FOREIGN KEY (artists) REFERENCES artist (uri)
);

CREATE TABLE track (
    uri             TEXT PRIMARY KEY,   -- track URI
    name            TEXT NOT NULL,      -- track name
    album           TEXT,               -- track album
    artists         TEXT,               -- (list of Artist) – track artists
    composers       TEXT,               -- (list of Artist) – track composers
    performers      TEXT,               -- (list of Artist) – track performers
    genre           TEXT,               -- track genre
    track_no        INTEGER,            -- track number in album
    disc_no         INTEGER,            -- disc number in album
    date            TEXT,               -- track release date (YYYY or YYYY-MM-DD)
    length          INTEGER,            -- track length in milliseconds
    bitrate         INTEGER,            -- bitrate in kbit/s
    comment         TEXT,               -- track comment
    musicbrainz_id  TEXT,               -- MusicBrainz ID
    last_modified   INTEGER,            -- Represents last modification time
    FOREIGN KEY (album) REFERENCES album (uri),
    FOREIGN KEY (artists) REFERENCES artist (uri),
    FOREIGN KEY (composers) REFERENCES artist (uri),
    FOREIGN KEY (performers) REFERENCES artist (uri)
);

CREATE INDEX album_name_index            ON album (name);
CREATE INDEX album_artists_index         ON album (artists);
CREATE INDEX album_date_index            ON album (date);
CREATE INDEX artist_name_index           ON artist (name);
CREATE INDEX track_name_index            ON track (name);
CREATE INDEX track_album_index           ON track (album);
CREATE INDEX track_artists_index         ON track (artists);
CREATE INDEX track_composers_index       ON track (composers);
CREATE INDEX track_performers_index      ON track (performers);
CREATE INDEX track_genre_index           ON track (genre);
CREATE INDEX track_track_no_index        ON track (track_no);
CREATE INDEX track_disc_no_index         ON track (disc_no);
CREATE INDEX track_date_index            ON track (date);
CREATE INDEX track_comment_index         ON track (comment);
CREATE INDEX track_last_modified_index   ON track (last_modified);
CREATE INDEX album_musicbrainz_id_index  ON album (musicbrainz_id);
CREATE INDEX artist_musicbrainz_id_index ON artist (musicbrainz_id);
CREATE INDEX track_musicbrainz_id_index  ON track (musicbrainz_id);

-- Convenience views

CREATE VIEW albums AS
SELECT album.uri                        AS uri,
       album.name                       AS name,
       artist.uri                       AS artist_uri,
       artist.name                      AS artist_name,
       artist.sortname                  AS artist_sortname,
       artist.musicbrainz_id            AS artist_musicbrainz_id,
       album.num_tracks                 AS num_tracks,
       album.num_discs                  AS num_discs,
       album.date                       AS date,
       album.musicbrainz_id             AS musicbrainz_id,
       album.images                     AS images
  FROM album
  LEFT OUTER JOIN artist                ON album.artists = artist.uri;

CREATE VIEW tracks AS
SELECT track.rowid                      AS docid,
       track.uri                        AS uri,
       track.name                       AS name,
       track.genre                      AS genre,
       track.track_no                   AS track_no,
       track.disc_no                    AS disc_no,
       track.date                       AS date,
       track.length                     AS length,
       track.bitrate                    AS bitrate,
       track.comment                    AS comment,
       track.musicbrainz_id             AS musicbrainz_id,
       track.last_modified              AS last_modified,
       album.uri                        AS album_uri,
       album.name                       AS album_name,
       album.num_tracks                 AS album_num_tracks,
       album.num_discs                  AS album_num_discs,
       album.date                       AS album_date,
       album.musicbrainz_id             AS album_musicbrainz_id,
       album.images                     AS album_images,
       artist.uri                       AS artist_uri,
       artist.name                      AS artist_name,
       artist.sortname                  AS artist_sortname,
       artist.musicbrainz_id            AS artist_musicbrainz_id,
       composer.uri                     AS composer_uri,
       composer.name                    AS composer_name,
       composer.sortname                AS composer_sortname,
       composer.musicbrainz_id          AS composer_musicbrainz_id,
       performer.uri                    AS performer_uri,
       performer.name                   AS performer_name,
       performer.sortname               AS performer_sortname,
       performer.musicbrainz_id         AS performer_musicbrainz_id,
       albumartist.uri                  AS albumartist_uri,
       albumartist.name                 AS albumartist_name,
       albumartist.sortname             AS albumartist_sortname,
       albumartist.musicbrainz_id       AS albumartist_musicbrainz_id
  FROM track
  LEFT OUTER JOIN album                 ON track.album = album.uri
  LEFT OUTER JOIN artist                ON track.artists = artist.uri
  LEFT OUTER JOIN artist AS composer    ON track.composers = composer.uri
  LEFT OUTER JOIN artist AS performer   ON track.performers = performer.uri
  LEFT OUTER JOIN artist AS albumartist ON album.artists = albumartist.uri;

-- Indexed search; column names match Mopidy query fields

CREATE VIEW search AS
SELECT docid                            AS docid,
       uri                              AS uri,
       name                             AS track_name,
       album_name                       AS album,
       artist_name                      AS artist,
       composer_name                    AS composer,
       performer_name                   AS performer,
       albumartist_name                 AS albumartist,
       genre                            AS genre,
       track_no                         AS track_no,
       disc_no                          AS disc_no,
       coalesce(date, album_date)       AS date,
       comment                          AS comment,
       musicbrainz_id                   AS musicbrainz_trackid,
       album_musicbrainz_id             AS musicbrainz_albumid,
       artist_musicbrainz_id            AS musicbrainz_artistid

 FROM tracks;

-- Full-text search; column names match Mopidy query fields

CREATE VIRTUAL TABLE fts USING fts3 (
    uri,
    track_name,
    album,
    artist,
    composer,
    performer,
    albumartist,
    genre,
    track_no,
    disc_no,
    date,
    comment,
    musicbrainz_trackid,
    musicbrainz_albumid,
    musicbrainz_artistid
);

CREATE TRIGGER track_after_insert AFTER INSERT ON track
BEGIN
    INSERT INTO fts (
        docid,
        uri,
        track_name,
        album,
        artist,
        composer,
        performer,
        albumartist,
        genre,
        track_no,
        disc_no,
        date,
        comment,
        musicbrainz_trackid,
        musicbrainz_albumid,
        musicbrainz_artistid
    ) SELECT * FROM search WHERE docid = new.rowid;
END;

CREATE TRIGGER track_after_update AFTER UPDATE ON track
BEGIN
    INSERT INTO fts (
        docid,
        uri,
        track_name,
        album,
        artist,
        composer,
        performer,
        albumartist,
        genre,
        track_no,
        disc_no,
        date,
        comment,
        musicbrainz_trackid,
        musicbrainz_albumid,
        musicbrainz_artistid
    ) SELECT * FROM search WHERE docid = new.rowid;
END;

CREATE TRIGGER track_before_update BEFORE UPDATE ON track
BEGIN
    DELETE FROM fts WHERE docid = old.rowid;
END;

CREATE TRIGGER track_before_delete BEFORE DELETE ON track
BEGIN
    DELETE FROM fts WHERE docid = old.rowid;
END;

END TRANSACTION;
