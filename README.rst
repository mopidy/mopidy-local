************
Mopidy-Local
************

.. image:: https://img.shields.io/pypi/v/Mopidy-Local
    :target: https://pypi.org/project/Mopidy-Local/
    :alt: Latest PyPI version

.. image:: https://img.shields.io/github/workflow/status/mopidy/mopidy-local/CI
    :target: https://github.com/mopidy/mopidy-local/actions
    :alt: CI build status

.. image:: https://img.shields.io/codecov/c/gh/mopidy/mopidy-local
    :target: https://codecov.io/gh/mopidy/mopidy-local
    :alt: Test coverage

`Mopidy`_ extension for playing music from your local music archive.

.. _Mopidy: https://www.mopidy.com/


Table of contents
=================

- `Maintainer wanted`_
- Installation_
- Configuration_
- Usage_

  - `Generating a library`_
  - `Updating the library`_
  - `Clearing the library`_

- `Project resources`_
- Credits_


Maintainer wanted
=================

Mopidy-Local is currently kept on life support by the Mopidy core
developers. It is in need of a more dedicated maintainer.

If you want to be the maintainer of Mopidy-Local, please:

1. Make 2-3 good pull requests improving any part of the project.

2. Read and get familiar with all of the project's open issues.

3. Send a pull request removing this section and adding yourself as the
   "Current maintainer" in the "Credits" section below. In the pull request
   description, please refer to the previous pull requests and state that
   you've familiarized yourself with the open issues.

   As a maintainer, you'll be given push access to the repo and the authority to
   make releases to PyPI when you see fit.


Installation
============

Install by running::

    sudo python3 -m pip install Mopidy-Local

See https://mopidy.com/ext/local/ for alternative installation methods.


Configuration
=============

Before starting Mopidy, you must add configuration for
Mopidy-Local to your Mopidy configuration file::

    [local]
    media_dir = /path/to/your/music/archive

The following configuration values are available:

- ``local/enabled``: If the local extension should be enabled or not.
  Defaults to ``true``.

- ``local/media_dir``: Path to directory with local media files.

- ``local/max_search_results``: Number of search results that should be returned. Default is 100.

- ``local/scan_timeout``: Number of milliseconds before giving up scanning a
  file and moving on to the next file.

- ``local/scan_follow_symlinks``: If we should follow symlinks found in
  ``local/media_dir``.

- ``local/scan_flush_threshold``: Number of tracks to wait before telling
  library it should try and store its progress so far. Some libraries might not
  respect this setting. Set this to zero to disable flushing.

- ``local/included_file_extensions``: File extensions to include when scanning
  the media directory. Values should be separated by either comma or newline.
  Each file extension should start with a dot, .e.g. ``.flac``. Setting any
  values here will override the existence of ``local/excluded_file_extensions``.

- ``local/excluded_file_extensions``: File extensions to exclude when scanning
  the media directory. Values should be separated by either comma or newline.
  Each file extension should start with a dot, .e.g. ``.html``. Defaults to a
  list of common non-audio file extensions often found in music collections.
  This config value has no effect if ``local/included_file_extensions`` is set.

- ``local/directories``: List of top-level directory names and URIs
  for browsing. See below.

- ``local/timeout``: Database connection timeout in seconds.

- ``local/use_artist_sortname``: Whether to use the sortname field for
  ordering artist browse results. Disabled by default, since this may
  give confusing results if not all artists in the library have proper
  sortnames.

- ``local/album_art_files``: List of file names to check for when searching
  for external album art. These may contain UNIX shell patterns,
  i.e. ``*``, ``?``, etc.


Usage
=====


Generating a library
--------------------

The command ``mopidy local scan`` will scan the path set in the
``local/media_dir`` config value for any audio files and build a
library of metadata.

To make a local library for your music available for Mopidy:

#. Ensure that the ``local/media_dir`` config value points to where your
   music is located. Check the current setting by running::

    mopidy config

#. Scan your media library.::

    mopidy local scan

#. Start Mopidy, find the music library in a client, and play some local music!


Updating the library
--------------------

When you've added or removed music in your collection and want to update
Mopidy's index of your local library, you need to rescan::

    mopidy local scan

Options can be specified to control the behavior of the scan command:

- ``--force`` Force rescan of all media files
- ``--limit <number>`` Maximum number of tracks to scan

Example::

    mopidy local scan --limit 50


Clearing the library
--------------------

To delete your local images and clear your local library::

    mopidy local clear

A prompt will ask you to confirm this irreversible operation.


Library layout
--------------

The exposed library has a root directory and nine top-level directories defined
under the root directory:

- Albums
- Artists
- Composers
- Genres
- Performers
- Release Years
- Tracks
- Last Week's Updates
- Last Month's Updates

This can be configured through the ``directories`` setting. It's expected to be a
list of space separated name and URI supported for browsing, eg::

  directories =
      Albums                  local:directory?type=album
      Artists                 local:directory?type=artist
      Composers               local:directory?type=artist&role=composer
      Tracks                  local:directory?type=track
      Last Week's Updates     local:directory?max-age=604800

URIs supported for browsing
~~~~~~~~~~~~~~~~~~~~~~~~~~~

*Remember that URIs are opaque values that neither Mopidy’s core layer or Mopidy
frontends should attempt to derive any meaning from.* That said, it's necessary
to have a sufficient knowledge of Mopidy-Local URIs to customize the
``directories`` setting properly.

Browsing URIs starting with ``local:artist`` returns references to
albums and tracks with the given artist. Browsing URIs starting with
``local:album`` returns references to the album tracks. Browsing URIs
starting with ``local:track`` is not supported.

Other URIs supported for browsing start with ``local:directory``. The returned
references are specified through "query parameters":

- ``local:directory``: References to the top levels directories.

- ``local:directory?type=tracks``: References all tracks. Multiple
  parameters can be added to filter the referenced tracks: ``album``,
  ``albumartist``, ``artist``, ``composer``, ``date``, ``genre``,
  ``performer``, and ``max-age``.

- ``local:directory?type=date``: References to directories grouping tracks by
  date and album. Dates are transformed according to the optional parameter
  ``FORMAT`` which default to ``%Y-%m-%d``. The URIs of the references start
  with ``local:directory?date=``.

- ``local:directory?type=genre``: References to directories named after genres
  found among all tracks. Their URIs start with ``local::directory?genre=``.

- ``local:directory?type=album``: References to all albums.

- ``local:directory?type=album&PARAM=VALUE``: References to
  directories grouping tracks matching the given criteria.  ``PARAM``
  must be one of ``albumartist``, ``artist``, ``composer``, ``date``,
  ``genre``, ``performer``, ``max-age``. The referenced directories
  group the selected tracks by album; Their URIs start with
  ``local::directory?PARAM=VALUE&type=track&album=local:album:``.

- ``local:directory?type=artist``: References to all artists.

- ``local:directory?type=artist&role=ROLE``: References to directories with URIs
  ``local:directory?ROLE=URI`` where ``URI`` varies among all URIs starting with
  ``local:artist`` build from all tracks tag corresponding to ``ROLE``. ``ROLE``
  is one of ``albumartist``, ``artist``, ``composer``, or ``performer``.

- ``local:directory?album=URI``: A reference to a directory grouping the tracks
  of the album with given URI. Its URI starts with
  ``local:directory?album=URI&type=track``.

- ``local:directory?albumartist=URI``: References to directories
  grouping tracks whose albumartist tag has given URI. The referenced
  directories group the selected tracks by album; Their URIs start
  with
  ``local:directory?albumartist=URI&type=track&album=local:album:``.

- ``local:directory?artist=URI``: References to directories grouping
  tracks whose artist has given URI. The referenced directories group
  the selected tracks by album; Their URIs start with
  ``local:directory?artist=URI&type=track&album=local:album:``.

- ``local:directory?composer=URI``: References to directories grouping
  tracks whose composer has given URI. The referenced directories
  group the selected tracks by album; Their URIs start with
  ``local:directory?composer=URI&type=track&album=local:album:``.

- ``local:directory?date=DATE``: References to directories grouping
  tracks whose date match DATE. The referenced directories group the
  selected tracks by album; Their URIs start with
  ``local:directory?date=DATE&type=track&album=local:album:``. The
  match is to be interpreted as in a ``LIKE`` SQL statement.

- ``local:directory?genre=GENRE``: References to directories grouping
  tracks whose genre is GENRE. The referenced directories group the
  selected tracks by album; Their URIs start with
  ``local:directory?genre=GENRE&type=track&album=local:album:``.

- ``local:directory?performer=URI``: References to directories
  grouping tracks whose performer has given URI. The referenced
  directories group the selected tracks by album; Their URIs start
  with
  ``local:directory?performer=URI&type=track&album=local:album:``.

- ``local:directory?max-age=SECONDS``: References to directories
  grouping tracks whose "last modified" date is newer than SECONDS
  seconds. The referenced directories group the selected tracks by
  album; Their URIs start with
  ``local:directory?max-age=SECONDS&type=track&album=local:album:``.

Project resources
=================

- `Source code <https://github.com/mopidy/mopidy-local>`_
- `Issue tracker <https://github.com/mopidy/mopidy-local/issues>`_
- `Changelog <https://github.com/mopidy/mopidy-local/releases>`_


Credits
=======

- Original authors:
  `Stein Magnus Jodal <https://github.com/jodal>`__ and
  `Thomas Adamcik <https://github.com/adamcik>`__ for the Mopidy-Local extension in Mopidy core.
  `Thomas Kemmer <https://github.com/tkem>`__ for the SQLite storage and support for embedded album art.
- Current maintainer: None. Maintainer wanted, see section above.
- `Contributors <https://github.com/mopidy/mopidy-local/graphs/contributors>`_
