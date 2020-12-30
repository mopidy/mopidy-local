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
  for browsing.

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
