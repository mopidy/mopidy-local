-- Mopidy-Local-SQLite schema upgrade v5 -> v6

BEGIN EXCLUSIVE TRANSACTION;

ALTER TABLE artist ADD COLUMN sortname TEXT;

DROP VIEW albums;
DROP VIEW tracks;

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

PRAGMA user_version = 6;  -- update schema version

END TRANSACTION;
