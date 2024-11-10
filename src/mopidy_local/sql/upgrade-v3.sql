-- Mopidy-Local-SQLite schema upgrade v3 -> v4

BEGIN EXCLUSIVE TRANSACTION;

CREATE INDEX album_date_index           ON album (date);
CREATE INDEX track_track_no_index       ON track (track_no);
CREATE INDEX track_date_index           ON track (date);

DROP VIEW artists;
DROP VIEW composers;
DROP VIEW performers;

PRAGMA user_version = 4;  -- update schema version

END TRANSACTION;
