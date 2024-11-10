-- Mopidy-Local-SQLite schema upgrade v2 -> v3

BEGIN EXCLUSIVE TRANSACTION;

CREATE VIEW albums AS
SELECT album.uri                        AS uri,
       album.name                       AS name,
       artist.uri                       AS artist_uri,
       artist.name                      AS artist_name,
       artist.musicbrainz_id            AS artist_musicbrainz_id,
       album.num_tracks                 AS num_tracks,
       album.num_discs                  AS num_discs,
       album.date                       AS date,
       album.musicbrainz_id             AS musicbrainz_id,
       album.images                     AS images
  FROM album
  LEFT OUTER JOIN artist                ON album.artists = artist.uri;

CREATE VIEW artists AS
SELECT uri, name, musicbrainz_id
  FROM artist
 WHERE EXISTS (SELECT * FROM album WHERE album.artists = artist.uri)
    OR EXISTS (SELECT * FROM track WHERE track.artists = artist.uri);

CREATE VIEW composers AS
SELECT uri, name, musicbrainz_id
  FROM artist
 WHERE EXISTS (SELECT * FROM track WHERE track.composers = artist.uri);

CREATE VIEW performers AS
SELECT uri, name, musicbrainz_id
  FROM artist
 WHERE EXISTS (SELECT * FROM track WHERE track.performers = artist.uri);

PRAGMA user_version = 3;  -- update schema version

END TRANSACTION;
