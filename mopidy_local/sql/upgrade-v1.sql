-- Mopidy-Local-SQLite schema upgrade v1 -> v2

BEGIN EXCLUSIVE TRANSACTION;

-- update schema

CREATE INDEX album_name_index           ON album (name);
CREATE INDEX album_artists_index        ON album (artists);
CREATE INDEX artist_name_index          ON artist (name);
CREATE INDEX track_name_index           ON track (name);
CREATE INDEX track_album_index          ON track (album);
CREATE INDEX track_artists_index        ON track (artists);
CREATE INDEX track_composers_index      ON track (composers);
CREATE INDEX track_performers_index     ON track (performers);
CREATE INDEX track_genre_index          ON track (genre);
CREATE INDEX track_comment_index        on track (comment);

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
       artist.musicbrainz_id            AS artist_musicbrainz_id,
       composer.uri                     AS composer_uri,
       composer.name                    AS composer_name,
       composer.musicbrainz_id          AS composer_musicbrainz_id,
       performer.uri                    AS performer_uri,
       performer.name                   AS performer_name,
       performer.musicbrainz_id         AS performer_musicbrainz_id,
       albumartist.uri                  AS albumartist_uri,
       albumartist.name                 AS albumartist_name,
       albumartist.musicbrainz_id       AS albumartist_musicbrainz_id
  FROM track
  LEFT OUTER JOIN album                 ON track.album = album.uri
  LEFT OUTER JOIN artist                ON track.artists = artist.uri
  LEFT OUTER JOIN artist AS composer    ON track.composers = composer.uri
  LEFT OUTER JOIN artist AS performer   ON track.performers = performer.uri
  LEFT OUTER JOIN artist AS albumartist ON album.artists = albumartist.uri;

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
       coalesce(date, album_date)       AS date,
       comment                          AS comment
 FROM tracks;

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
    date,
    comment
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
        date,
        comment
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
        date,
        comment
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

-- update date

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
    date,
    comment
) SELECT * FROM search;

PRAGMA user_version = 2;  -- update schema version

END TRANSACTION;
