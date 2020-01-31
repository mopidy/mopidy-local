*********
Changelog
*********


v3.1.1 (2020-01-31)
===================

- Handle scan results without duration gracefully. (#36, PR: #35)


v3.1.0 (2020-01-09)
===================

- Improve handling of paths with arbitrary encodings in the scanner. (#20, PR: #29)

- Add ``.cue`` to the list of excluded file extensions. (PR: #29)

- Replace ``os.path`` usage with ``pathlib`` to handle arbitrary file path
  encodings better. (#20, PR: #30)

- Add an ``included_files_extensions`` config. (#8, PR: #32)

- Remove broken support for creating URIs from MusicBrainz IDs. This was turned
  off in Mopidy < 3, but was by accident enabled by default in Mopidy-Local
  3.0. Now the broken feature is fully removed. (#26, PR: #31)


v3.0.0 (2019-12-22)
===================

- Depend on final release of Mopidy 3.0.0.


v3.0.0a3 (2019-12-15)
=====================

- Move parts of the scanner functionality from Mopidy. (#19)


v3.0.0a2 (2019-12-09)
=====================

- Require Python >= 3.7. (PR: #10)

- Require Mopidy >= 3.0.0a5. (PR: #10)

- Require Pykka >= 2.0.1. (PR: #10)

- Update project setup. (PR: #10)

- Merge Mopidy-Local-SQLite into Mopidy-Local (PR: #10)

- Merge Mopidy-Local-Images web extension into Mopidy-Local. (PR: #10)

- Remove support for pluggable libraries, remove the JSON library storage,
  and use SQLite instead. (PR: #10)


v3.0.0a1 (2019-08-04)
=====================

Initial release which extracts the Mopidy-Local extension from Mopidy core.

This is an alpha release because it depends on the pre-releases of Mopidy 3.0.
