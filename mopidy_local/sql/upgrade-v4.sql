-- Mopidy-Local-SQLite schema upgrade v4 -> v5

BEGIN EXCLUSIVE TRANSACTION;

CREATE INDEX track_last_modified_index  ON track (last_modified);

PRAGMA user_version = 5;  -- update schema version

END TRANSACTION;
