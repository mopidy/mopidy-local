-- Mopidy-Local-SQLite schema upgrade v6 -> v7

BEGIN EXCLUSIVE TRANSACTION;

CREATE INDEX track_disc_no_index         ON track (disc_no);
CREATE INDEX album_musicbrainz_id_index  ON album (musicbrainz_id);
CREATE INDEX artist_musicbrainz_id_index ON artist (musicbrainz_id);
CREATE INDEX track_musicbrainz_id_index  ON track (musicbrainz_id);

DROP VIEW search;

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

DROP TABLE fts;

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

DROP TRIGGER track_after_insert;
DROP TRIGGER track_after_update;

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
    disc_no,
    date,
    comment,
    musicbrainz_trackid,
    musicbrainz_albumid,
    musicbrainz_artistid
) SELECT * FROM search;

PRAGMA user_version = 7;  -- update schema version

END TRANSACTION;
