import logging
import pathlib
import time

from mopidy import commands, exceptions
from mopidy.audio import scan, tags

from mopidy_local import mtimes, storage, translator

logger = logging.getLogger(__name__)

MIN_DURATION_MS = 100  # Shortest length of track to include.


class LocalCommand(commands.Command):
    def __init__(self):
        super().__init__()
        self.add_child("scan", ScanCommand())
        self.add_child("clear", ClearCommand())


class ClearCommand(commands.Command):
    help = "Clear local media files from the local library."

    def run(self, args, config):
        library = storage.LocalStorageProvider(config)

        prompt = "Are you sure you want to clear the library? [y/N] "

        if input(prompt).lower() != "y":
            print("Clearing library aborted")
            return 0

        if library.clear():
            print("Library successfully cleared")
            return 0

        print("Unable to clear library")
        return 1


class ScanCommand(commands.Command):
    help = "Scan local media files and populate the local library."

    def __init__(self):
        super().__init__()
        self.add_argument(
            "--limit",
            action="store",
            type=int,
            dest="limit",
            default=None,
            help="Maximum number of tracks to scan",
        )
        self.add_argument(
            "--force",
            action="store_true",
            dest="force",
            default=False,
            help="Force rescan of all media files",
        )

    def run(self, args, config):
        media_dir = pathlib.Path(config["local"]["media_dir"]).resolve()
        library = storage.LocalStorageProvider(config)

        file_mtimes = self._find_files(
            media_dir=media_dir,
            follow_symlinks=config["local"]["scan_follow_symlinks"],
        )

        uris_to_update, uris_in_library = self._check_tracks_in_library(
            media_dir=media_dir,
            file_mtimes=file_mtimes,
            library=library,
            force_rescan=args.force,
        )

        uris_to_update.update(
            self._find_files_to_scan(
                media_dir=media_dir,
                file_mtimes=file_mtimes,
                uris_in_library=uris_in_library,
                excluded_file_exts=[
                    file_ext.lower()
                    for file_ext in config["local"]["excluded_file_extensions"]
                ],
            )
        )

        self._scan_metadata(
            media_dir=media_dir,
            file_mtimes=file_mtimes,
            uris=uris_to_update,
            library=library,
            timeout=config["local"]["scan_timeout"],
            flush_threshold=config["local"]["scan_flush_threshold"],
            limit=args.limit,
        )

        library.close()
        return 0

    def _find_files(self, *, media_dir, follow_symlinks):
        logger.info(f"Finding files in {media_dir.as_uri()} ...")
        file_mtimes, file_errors = mtimes.find_mtimes(media_dir, follow=follow_symlinks)
        logger.info(f"Found {len(file_mtimes)} files in {media_dir.as_uri()}")

        if file_errors:
            logger.warning(
                f"Encountered {len(file_errors)} errors "
                f"while scanning {media_dir.as_uri()}"
            )
        for name in file_errors:
            logger.debug(f"Scan error {file_errors[name]!r} for {name!r}")

        return file_mtimes

    def _check_tracks_in_library(
        self, *, media_dir, file_mtimes, library, force_rescan
    ):
        num_tracks = library.load()
        logger.info(f"Checking {num_tracks} tracks from library")

        uris_to_update = set()
        uris_to_remove = set()
        uris_in_library = set()

        for track in library.begin():
            absolute_path = translator.local_uri_to_path(track.uri, media_dir)
            mtime = file_mtimes.get(absolute_path)
            if mtime is None:
                logger.debug(f"Removing {track.uri}: File not found")
                uris_to_remove.add(track.uri)
            elif mtime > track.last_modified or force_rescan:
                uris_to_update.add(track.uri)
            uris_in_library.add(track.uri)

        logger.info(f"Removing {len(uris_to_remove)} missing tracks")
        for local_uri in uris_to_remove:
            library.remove(local_uri)

        return uris_to_update, uris_in_library

    def _find_files_to_scan(
        self, *, media_dir, file_mtimes, uris_in_library, excluded_file_exts
    ):
        uris_to_update = set()

        for absolute_path in file_mtimes:
            relative_path = absolute_path.relative_to(media_dir)
            local_uri = translator.path_to_local_track_uri(relative_path)

            if any(p.startswith(".") for p in relative_path.parts):
                logger.debug(f"Skipped {local_uri}: Hidden directory/file")
            elif relative_path.suffix.lower() in excluded_file_exts:
                logger.debug(f"Skipped {local_uri}: File extension excluded")
            elif local_uri not in uris_in_library:
                uris_to_update.add(local_uri)

        logger.info(f"Found {len(uris_to_update)} tracks which need to be updated")
        return uris_to_update

    def _scan_metadata(
        self, *, media_dir, file_mtimes, uris, library, timeout, flush_threshold, limit
    ):
        logger.info("Scanning...")

        uris = sorted(uris, key=lambda v: v.lower())
        uris = uris[:limit]

        scanner = scan.Scanner(timeout)
        progress = _ScanProgress(batch_size=flush_threshold, total=len(uris))

        for local_uri in uris:
            try:
                relative_path = translator.local_uri_to_path(local_uri, media_dir)
                file_uri = translator.path_to_file_uri(media_dir / relative_path)
                result = scanner.scan(file_uri)
                if not result.playable:
                    logger.warning(f"Failed {local_uri}: No audio found in file")
                elif result.duration < MIN_DURATION_MS:
                    logger.warning(
                        f"Failed {local_uri}: Track shorter than {MIN_DURATION_MS}ms"
                    )
                else:
                    mtime = file_mtimes.get(media_dir / relative_path)
                    track = tags.convert_tags_to_track(result.tags).replace(
                        uri=local_uri, length=result.duration, last_modified=mtime
                    )
                    library.add(track, result.tags, result.duration)
                    logger.debug(f"Added {track.uri}")
            except exceptions.ScannerError as error:
                logger.warning(f"Failed {local_uri}: {error}")

            if progress.increment():
                progress.log()
                if library.flush():
                    logger.debug("Progress flushed")

        progress.log()
        logger.info("Done scanning")


class _ScanProgress:
    def __init__(self, *, batch_size, total):
        self.count = 0
        self.batch_size = batch_size
        self.total = total
        self.start = time.time()

    def increment(self):
        self.count += 1
        return self.batch_size and self.count % self.batch_size == 0

    def log(self):
        duration = time.time() - self.start
        if self.count >= self.total or not self.count:
            logger.info(
                f"Scanned {self.count} of {self.total} files in {duration:.3f}s."
            )
        else:
            remainder = duration / self.count * (self.total - self.count)
            logger.info(
                f"Scanned {self.count} of {self.total} files "
                f"in {duration:.3f}s, ~{remainder:.0f}s left"
            )
