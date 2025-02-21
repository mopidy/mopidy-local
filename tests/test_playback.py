import time
import unittest
from typing import cast
from unittest import mock

import pykka
from mopidy import backend, core
from mopidy.core import PlaybackState
from mopidy.models import TlTrack, Track
from mopidy.types import DurationMs

from mopidy_local import actor
from tests import (
    dummy_audio,
    generate_song,
    path_to_data_dir,
    populate_tracklist,
)

# TODO: Test 'playlist repeat', e.g. repeat=1,single=0


class LocalPlaybackProviderTest(unittest.TestCase):
    config = {
        "core": {
            "data_dir": path_to_data_dir(""),
            "max_tracklist_length": 10000,
        },
        "local": {
            "media_dir": path_to_data_dir(""),
            "directories": [],
            "timeout": 10,
            "use_artist_sortname": False,
            "album_art_files": [],
        },
    }

    # We need four tracks so that our shuffled track tests behave nicely with
    # reversed as a fake shuffle. Ensuring that shuffled order is [4,3,2,1] and
    # normal order [1,2,3,4] which means next_track != next_track_with_random
    tracks = [
        Track(uri=generate_song(i), length=DurationMs(4464)) for i in (1, 2, 3, 4)
    ]
    tl_tracks: pykka.Future[list[TlTrack]]

    def add_track(self, uri):
        track = Track(uri=uri, length=DurationMs(4464))
        self.tracklist.add([track])

    def trigger_about_to_finish(self):
        # Flush any queued core calls.
        self.playback.get_current_tl_track().get()

        callback = self.audio.get_about_to_finish_callback().get()
        callback()

    def setUp(self):
        self.audio = dummy_audio.create_proxy()
        self.backend = cast(
            backend.BackendProxy,
            actor.LocalBackend.start(
                config=self.config,
                audio=self.audio,
            ).proxy(),
        )
        self.core = cast(
            core.CoreProxy,
            core.Core.start(
                audio=self.audio,
                backends=[self.backend],
                config=self.config,
            ).proxy(),
        )
        self.playback = self.core.playback
        self.tracklist = self.core.tracklist

        assert len(self.tracks) >= 3, "Need at least three tracks to run tests."
        assert self.tracks[0].length
        assert self.tracks[0].length >= 2000, (
            "First song needs to be at least 2000 miliseconds"
        )

    def tearDown(self):
        pykka.ActorRegistry.stop_all()

    def assert_state_is(self, state):
        assert self.playback.get_state().get() == state

    def assert_current_track_is(self, track):
        assert self.playback.get_current_track().get() == track

    def assert_current_track_is_not(self, track):
        assert self.playback.get_current_track().get() != track

    def assert_current_track_index_is(self, index):
        assert self.tracklist.index().get() == index

    def assert_next_tl_track_is(self, tl_track):
        next_tlid = self.tracklist.get_next_tlid().get()
        assert next_tlid == (tl_track and tl_track.tlid)

    def assert_next_tl_track_is_not(self, tl_track):
        next_tlid = self.tracklist.get_next_tlid().get()
        assert next_tlid != (tl_track and tl_track.tlid)

    def assert_previous_tl_track_is(self, tl_track):
        previous_tlid = self.tracklist.get_previous_tlid().get()
        assert previous_tlid == (tl_track and tl_track.tlid)

    def assert_eot_tl_track_is(self, tl_track):
        eot_tlid = self.tracklist.get_eot_tlid().get()
        assert eot_tlid == (tl_track and tl_track.tlid)

    def assert_eot_tl_track_is_not(self, tl_track):
        eot_tlid = self.tracklist.get_eot_tlid().get()
        assert eot_tlid != (tl_track and tl_track.tlid)

    def test_uri_scheme(self):
        assert "file" not in self.core.get_uri_schemes().get()
        assert "local" in self.core.get_uri_schemes().get()

    def test_play_mp3(self):
        self.add_track("local:track:blank.mp3")
        self.playback.play().get()
        self.assert_state_is(PlaybackState.PLAYING)

    def test_play_ogg(self):
        self.add_track("local:track:blank.ogg")
        self.playback.play().get()
        self.assert_state_is(PlaybackState.PLAYING)

    def test_play_flac(self):
        self.add_track("local:track:blank.flac")
        self.playback.play().get()
        self.assert_state_is(PlaybackState.PLAYING)

    def test_play_uri_with_non_ascii_bytes(self):
        # Regression test: If trying to do .split(u':') on a bytestring, the
        # string will be decoded from ASCII to Unicode, which will crash on
        # non-ASCII strings, like the bytestring the following URI decodes to.
        self.add_track("local:track:12%20Doin%E2%80%99%20It%20Right.flac")
        self.playback.play().get()
        self.assert_state_is(PlaybackState.PLAYING)

    def test_initial_state_is_stopped(self):
        self.assert_state_is(PlaybackState.STOPPED)

    def test_play_with_empty_playlist(self):
        self.assert_state_is(PlaybackState.STOPPED)
        self.playback.play().get()
        self.assert_state_is(PlaybackState.STOPPED)

    def test_play_with_empty_playlist_return_value(self):
        assert self.playback.play().get() is None

    @populate_tracklist
    def test_play_state(self):
        self.assert_state_is(PlaybackState.STOPPED)
        self.playback.play().get()
        self.assert_state_is(PlaybackState.PLAYING)

    @populate_tracklist
    def test_play_return_value(self):
        assert self.playback.play().get() is None

    @populate_tracklist
    def test_play_track_state(self):
        self.assert_state_is(PlaybackState.STOPPED)
        self.playback.play(tlid=self.tl_tracks.get()[-1].tlid).get()
        self.assert_state_is(PlaybackState.PLAYING)

    @populate_tracklist
    def test_play_track_return_value(self):
        assert self.playback.play(tlid=self.tl_tracks.get()[-1].tlid).get() is None

    @populate_tracklist
    def test_play_when_playing(self):
        self.playback.play().get()
        track = self.playback.get_current_track().get()
        self.playback.play().get()
        self.assert_current_track_is(track)

    @populate_tracklist
    def test_play_when_paused(self):
        self.playback.play().get()
        track = self.playback.get_current_track().get()
        self.playback.pause().get()
        self.playback.play().get()
        self.assert_state_is(PlaybackState.PLAYING)
        self.assert_current_track_is(track)

    @populate_tracklist
    def test_play_when_paused_after_next(self):
        self.playback.play().get()
        self.playback.next().get()
        self.playback.next().get()
        track = self.playback.get_current_track().get()
        self.playback.pause().get()
        self.playback.play().get()
        self.assert_state_is(PlaybackState.PLAYING)
        self.assert_current_track_is(track)

    @populate_tracklist
    def test_play_sets_current_track(self):
        self.playback.play().get()
        self.assert_current_track_is(self.tracks[0])

    @populate_tracklist
    def test_play_track_sets_current_track(self):
        self.playback.play(tlid=self.tl_tracks.get()[-1].tlid).get()
        self.assert_current_track_is(self.tracks[-1])

    @populate_tracklist
    def test_play_skips_to_next_track_on_failure(self):
        # If backend's play() returns False, it is a failure.
        uri = self.backend.playback.translate_uri(self.tracks[0].uri).get()
        self.audio.trigger_fake_playback_failure(uri)

        self.playback.play().get()
        self.assert_current_track_is_not(self.tracks[0])
        self.assert_current_track_is(self.tracks[1])

    @populate_tracklist
    def test_current_track_after_completed_playlist(self):
        self.playback.play(tlid=self.tl_tracks.get()[-1].tlid).get()
        self.trigger_about_to_finish()
        # EOS should have triggered
        self.assert_state_is(PlaybackState.STOPPED)
        self.assert_current_track_is(None)

        self.playback.play(tlid=self.tl_tracks.get()[-1].tlid).get()
        self.playback.next().get()
        self.assert_state_is(PlaybackState.STOPPED)
        self.assert_current_track_is(None)

    @populate_tracklist
    def test_previous(self):
        self.playback.play().get()
        self.playback.next().get()
        self.playback.previous().get()
        self.assert_current_track_is(self.tracks[0])

    @populate_tracklist
    def test_previous_more(self):
        self.playback.play().get()  # At track 0
        self.playback.next().get()  # At track 1
        self.playback.next().get()  # At track 2
        self.playback.previous().get()  # At track 1
        self.assert_current_track_is(self.tracks[1])

    @populate_tracklist
    def test_previous_return_value(self):
        self.playback.play().get()
        self.playback.next().get()
        assert self.playback.previous().get() is None

    @populate_tracklist
    def test_previous_does_not_trigger_playback(self):
        self.playback.play().get()
        self.playback.next().get()
        self.playback.stop()
        self.playback.previous().get()
        self.assert_state_is(PlaybackState.STOPPED)

    @populate_tracklist
    def test_previous_at_start_of_playlist(self):
        self.playback.previous().get()
        self.assert_state_is(PlaybackState.STOPPED)
        self.assert_current_track_is(None)

    def test_previous_for_empty_playlist(self):
        self.playback.previous().get()
        self.assert_state_is(PlaybackState.STOPPED)
        self.assert_current_track_is(None)

    @populate_tracklist
    def test_previous_skips_to_previous_track_on_failure(self):
        # If backend's play() returns False, it is a failure.
        uri = self.backend.playback.translate_uri(self.tracks[1].uri).get()
        self.audio.trigger_fake_playback_failure(uri)

        self.playback.play(tlid=self.tl_tracks.get()[2].tlid).get()
        self.assert_current_track_is(self.tracks[2])
        self.playback.previous().get()
        self.assert_current_track_is_not(self.tracks[1])
        self.assert_current_track_is(self.tracks[0])

    @populate_tracklist
    def test_next(self):
        self.playback.play().get()

        old_track = self.playback.get_current_track().get()
        old_position = self.tracklist.index().get()

        self.playback.next().get()

        assert self.tracklist.index().get() == (old_position + 1)
        self.assert_current_track_is_not(old_track)

    @populate_tracklist
    def test_next_return_value(self):
        self.playback.play().get()
        assert self.playback.next().get() is None

    @populate_tracklist
    def test_next_does_not_trigger_playback(self):
        self.playback.next().get()
        self.assert_state_is(PlaybackState.STOPPED)

    @populate_tracklist
    def test_next_at_end_of_playlist(self):
        self.playback.play().get()

        for i, track in enumerate(self.tracks):
            self.assert_state_is(PlaybackState.PLAYING)
            self.assert_current_track_is(track)
            assert self.tracklist.index().get() == i

            self.playback.next()

        self.assert_state_is(PlaybackState.STOPPED)

    @populate_tracklist
    def test_next_until_end_of_playlist_and_play_from_start(self):
        self.playback.play().get()

        for _ in self.tracks:
            self.playback.next().get()

        self.assert_current_track_is(None)
        self.assert_state_is(PlaybackState.STOPPED)

        self.playback.play().get()
        self.assert_state_is(PlaybackState.PLAYING)
        self.assert_current_track_is(self.tracks[0])

    def test_next_for_empty_playlist(self):
        self.playback.next().get()
        self.assert_state_is(PlaybackState.STOPPED)

    @populate_tracklist
    def test_next_skips_to_next_track_on_failure(self):
        # If backend's play() returns False, it is a failure.
        uri = self.backend.playback.translate_uri(self.tracks[1].uri).get()
        self.audio.trigger_fake_playback_failure(uri)

        self.playback.play().get()
        self.assert_current_track_is(self.tracks[0])
        self.playback.next().get()
        self.assert_current_track_is_not(self.tracks[1])
        self.assert_current_track_is(self.tracks[2])

    @populate_tracklist
    def test_next_track_before_play(self):
        self.assert_next_tl_track_is(self.tl_tracks.get()[0])

    @populate_tracklist
    def test_next_track_during_play(self):
        self.playback.play().get()
        self.assert_next_tl_track_is(self.tl_tracks.get()[1])

    @populate_tracklist
    def test_next_track_after_previous(self):
        self.playback.play().get()
        self.playback.next().get()
        self.playback.previous().get()
        self.assert_next_tl_track_is(self.tl_tracks.get()[1])

    def test_next_track_empty_playlist(self):
        self.assert_next_tl_track_is(None)

    @populate_tracklist
    def test_next_track_at_end_of_playlist(self):
        self.playback.play().get()
        for _ in self.tl_tracks.get()[1:]:
            self.playback.next().get()
        self.assert_next_tl_track_is(None)

    @populate_tracklist
    def test_next_track_at_end_of_playlist_with_repeat(self):
        self.tracklist.set_repeat(True)
        self.playback.play().get()
        for _ in self.tracks[1:]:
            self.playback.next().get()
        self.assert_next_tl_track_is(self.tl_tracks.get()[0])

    @populate_tracklist
    @mock.patch("random.shuffle")
    def test_next_track_with_random(self, shuffle_mock):
        shuffle_mock.side_effect = lambda tracks: tracks.reverse()

        self.tracklist.set_random(True)
        self.assert_next_tl_track_is(self.tl_tracks.get()[-1])

    @populate_tracklist
    def test_next_with_consume(self):
        self.tracklist.set_consume(True)
        self.playback.play().get()
        self.playback.next().get()
        assert self.tracks[0] not in self.tracklist.get_tracks().get()

    @populate_tracklist
    def test_next_with_single_and_repeat(self):
        self.tracklist.set_single(True)
        self.tracklist.set_repeat(True)
        self.playback.play().get()
        self.assert_current_track_is(self.tracks[0])
        self.playback.next().get()
        self.assert_current_track_is(self.tracks[1])

    @populate_tracklist
    @mock.patch("random.shuffle")
    def test_next_with_random(self, shuffle_mock):
        shuffle_mock.side_effect = lambda tracks: tracks.reverse()

        self.tracklist.set_random(True)
        self.playback.play().get()
        self.assert_current_track_is(self.tracks[-1])
        self.playback.next().get()
        self.assert_current_track_is(self.tracks[-2])

    @populate_tracklist
    @mock.patch("random.shuffle")
    def test_next_track_with_random_after_append_playlist(self, shuffle_mock):
        shuffle_mock.side_effect = lambda tracks: tracks.reverse()

        self.tracklist.set_random(True)

        expected_tl_track = self.tl_tracks.get()[-1]
        next_tlid = self.tracklist.get_next_tlid().get()

        # Baseline checking that first next_track is last tl track per our fake
        # shuffle.
        assert next_tlid == expected_tl_track.tlid

        self.tracklist.add(self.tracks[:1])

        old_next_tlid = next_tlid
        expected_tl_track = self.tracklist.get_tl_tracks().get()[-1]
        next_tlid = self.tracklist.get_next_tlid().get()

        # Verify that first next track has changed since we added to the
        # playlist.
        assert next_tlid == expected_tl_track.tlid
        assert next_tlid != old_next_tlid

    @populate_tracklist
    def test_end_of_track(self):
        self.playback.play().get()

        old_track = self.playback.get_current_track().get()
        old_position = self.tracklist.index().get()

        self.trigger_about_to_finish()

        new_track = self.playback.get_current_track().get()
        assert self.tracklist.index().get() == (old_position + 1)
        assert new_track.uri != old_track.uri

    @populate_tracklist
    def test_end_of_track_return_value(self):
        self.playback.play().get()
        assert self.trigger_about_to_finish() is None

    @populate_tracklist
    def test_end_of_track_does_not_trigger_playback(self):
        self.trigger_about_to_finish()
        self.assert_state_is(PlaybackState.STOPPED)

    @populate_tracklist
    def test_end_of_track_at_end_of_playlist(self):
        self.playback.play().get()

        for i, track in enumerate(self.tracks):
            self.assert_state_is(PlaybackState.PLAYING)
            self.assert_current_track_is(track)
            assert self.tracklist.index().get() == i

            self.trigger_about_to_finish()

        self.assert_state_is(PlaybackState.STOPPED)

    @populate_tracklist
    def test_end_of_track_until_end_of_playlist_and_play_from_start(self):
        self.playback.play().get()

        for _ in self.tracks:
            self.trigger_about_to_finish()

        assert self.playback.get_current_track().get() is None
        self.assert_state_is(PlaybackState.STOPPED)

        self.playback.play().get()
        self.assert_state_is(PlaybackState.PLAYING)
        self.assert_current_track_is(self.tracks[0])

    def test_end_of_track_for_empty_playlist(self):
        self.trigger_about_to_finish()
        self.assert_state_is(PlaybackState.STOPPED)

    # TODO: On about to finish does not handle skipping to next track yet.
    @unittest.expectedFailure
    @populate_tracklist
    def test_end_of_track_skips_to_next_track_on_failure(self):
        # If backend's play() returns False, it is a failure.
        return_values = [True, False, True]
        self.backend.playback.play = lambda: return_values.pop()
        self.playback.play().get()
        self.assert_current_track_is(self.tracks[0])
        self.trigger_about_to_finish()
        self.assert_current_track_is_not(self.tracks[1])
        self.assert_current_track_is(self.tracks[2])

    @populate_tracklist
    def test_end_of_track_track_before_play(self):
        self.assert_next_tl_track_is(self.tl_tracks.get()[0])

    @populate_tracklist
    def test_end_of_track_track_during_play(self):
        self.playback.play().get()
        self.assert_next_tl_track_is(self.tl_tracks.get()[1])

    @populate_tracklist
    def test_about_to_finish_after_previous(self):
        self.playback.play().get()
        self.trigger_about_to_finish()
        self.playback.previous().get()
        self.assert_next_tl_track_is(self.tl_tracks.get()[1])

    def test_end_of_track_track_empty_playlist(self):
        self.assert_next_tl_track_is(None)

    @populate_tracklist
    def test_end_of_track_track_at_end_of_playlist(self):
        self.playback.play().get()
        for _ in self.tracks[1:]:
            self.trigger_about_to_finish()

        self.assert_next_tl_track_is(None)

    @populate_tracklist
    def test_end_of_track_track_at_end_of_playlist_with_repeat(self):
        self.tracklist.set_repeat(True)
        self.playback.play().get()
        for _ in self.tracks[1:]:
            self.trigger_about_to_finish()

        self.assert_next_tl_track_is(self.tl_tracks.get()[0])

    @populate_tracklist
    @mock.patch("random.shuffle")
    def test_end_of_track_track_with_random(self, shuffle_mock):
        shuffle_mock.side_effect = lambda tracks: tracks.reverse()

        self.tracklist.set_random(True)
        self.assert_next_tl_track_is(self.tl_tracks.get()[-1])

    @populate_tracklist
    def test_end_of_track_with_consume(self):
        self.tracklist.set_consume(True)
        self.playback.play().get()
        self.trigger_about_to_finish()
        assert self.tracks[0] not in self.tracklist.get_tracks().get()

    @populate_tracklist
    @mock.patch("random.shuffle")
    def test_end_of_track_with_random(self, shuffle_mock):
        shuffle_mock.side_effect = lambda tracks: tracks.reverse()

        self.tracklist.set_random(True)
        self.playback.play().get()
        self.assert_current_track_is(self.tracks[-1])
        self.trigger_about_to_finish()
        self.assert_current_track_is(self.tracks[-2])

    @populate_tracklist
    @mock.patch("random.shuffle")
    def test_end_of_track_track_with_random_after_append_playlist(self, shuffle_mock):
        shuffle_mock.side_effect = lambda tracks: tracks.reverse()

        self.tracklist.set_random(True)

        expected_tl_track = self.tracklist.get_tl_tracks().get()[-1]
        eot_tlid = self.tracklist.get_eot_tlid().get()

        # Baseline checking that first eot_track is last tl track per our fake
        # shuffle.
        assert eot_tlid == expected_tl_track.tlid

        self.tracklist.add(self.tracks[:1])

        old_eot_tlid = eot_tlid
        expected_tl_track = self.tracklist.get_tl_tracks().get()[-1]
        eot_tlid = self.tracklist.get_eot_tlid().get()

        # Verify that first next track has changed since we added to the
        # playlist.
        assert eot_tlid == expected_tl_track.tlid
        assert eot_tlid != old_eot_tlid

    @populate_tracklist
    def test_previous_track_before_play(self):
        self.assert_previous_tl_track_is(None)

    @populate_tracklist
    def test_previous_track_after_play(self):
        self.playback.play().get()
        self.assert_previous_tl_track_is(None)

    @populate_tracklist
    def test_previous_track_after_next(self):
        self.playback.play().get()
        self.playback.next().get()
        self.assert_previous_tl_track_is(self.tl_tracks.get()[0])

    @populate_tracklist
    def test_previous_track_after_previous(self):
        self.playback.play().get()  # At track 0
        self.playback.next().get()  # At track 1
        self.playback.next().get()  # At track 2
        self.playback.previous().get()  # At track 1
        self.assert_previous_tl_track_is(self.tl_tracks.get()[0])

    def test_previous_track_empty_playlist(self):
        self.assert_previous_tl_track_is(None)

    @populate_tracklist
    def test_previous_track_with_consume(self):
        self.tracklist.set_consume(True)
        for _ in self.tracks:
            self.playback.next()
            current = self.playback.get_current_tl_track().get()
            self.assert_previous_tl_track_is(current)

    @populate_tracklist
    def test_previous_track_with_random(self):
        self.tracklist.set_random(True)
        for _ in self.tracks:
            self.playback.next()
            current = self.playback.get_current_tl_track().get()
            self.assert_previous_tl_track_is(current)

    @populate_tracklist
    def test_initial_current_track(self):
        self.assert_current_track_is(None)

    @populate_tracklist
    def test_current_track_during_play(self):
        self.playback.play().get()
        self.assert_current_track_is(self.tracks[0])

    @populate_tracklist
    def test_current_track_after_next(self):
        self.playback.play()
        self.playback.next().get()
        self.assert_current_track_is(self.tracks[1])

    @populate_tracklist
    def test_initial_tracklist_position(self):
        assert self.tracklist.index().get() is None

    @populate_tracklist
    def test_tracklist_position_during_play(self):
        self.playback.play().get()
        self.assert_current_track_index_is(0)

    @populate_tracklist
    def test_tracklist_position_after_next(self):
        self.playback.play().get()
        self.playback.next().get()
        self.assert_current_track_index_is(1)

    @populate_tracklist
    def test_tracklist_position_at_end_of_playlist(self):
        self.playback.play(tlid=self.tl_tracks.get()[-1].tlid).get()
        self.trigger_about_to_finish()
        # EOS should have triggered
        self.assert_current_track_index_is(None)

    @mock.patch("mopidy.core.playback.PlaybackController._on_tracklist_change")
    def test_on_tracklist_change_gets_called(self, change_mock):
        self.tracklist.add([Track()]).get()
        change_mock.assert_called_once_with()

    @populate_tracklist
    def test_on_tracklist_change_when_playing(self):
        self.playback.play().get()
        current_track = self.playback.get_current_track().get()
        self.tracklist.add([self.tracks[2]])
        self.assert_state_is(PlaybackState.PLAYING)
        self.assert_current_track_is(current_track)

    @populate_tracklist
    def test_on_tracklist_change_when_stopped(self):
        self.tracklist.add([self.tracks[2]])
        self.assert_state_is(PlaybackState.STOPPED)
        self.assert_current_track_is(None)

    @populate_tracklist
    def test_on_tracklist_change_when_paused(self):
        self.playback.play().get()
        self.playback.pause()
        current_track = self.playback.get_current_track().get()
        self.tracklist.add([self.tracks[2]])
        self.assert_state_is(PlaybackState.PAUSED)
        self.assert_current_track_is(current_track)

    @populate_tracklist
    def test_pause_when_stopped(self):
        self.playback.pause()
        self.assert_state_is(PlaybackState.PAUSED)

    @populate_tracklist
    def test_pause_when_playing(self):
        self.playback.play().get()
        self.playback.pause()
        self.assert_state_is(PlaybackState.PAUSED)

    @populate_tracklist
    def test_pause_when_paused(self):
        self.playback.play().get()
        self.playback.pause()
        self.playback.pause()
        self.assert_state_is(PlaybackState.PAUSED)

    @populate_tracklist
    def test_pause_return_value(self):
        self.playback.play().get()
        assert self.playback.pause().get() is None

    @populate_tracklist
    def test_resume_when_stopped(self):
        self.playback.resume()
        self.assert_state_is(PlaybackState.STOPPED)

    @populate_tracklist
    def test_resume_when_playing(self):
        self.playback.play().get()
        self.playback.resume()
        self.assert_state_is(PlaybackState.PLAYING)

    @populate_tracklist
    def test_resume_when_paused(self):
        self.playback.play().get()
        self.playback.pause()
        self.playback.resume()
        self.assert_state_is(PlaybackState.PLAYING)

    @populate_tracklist
    def test_resume_return_value(self):
        self.playback.play().get()
        self.playback.pause()
        assert self.playback.resume().get() is None

    @unittest.SkipTest  # Uses sleep and might not work with LocalBackend
    @populate_tracklist
    def test_resume_continues_from_right_position(self):
        self.playback.play().get()
        time.sleep(0.2)
        self.playback.pause()
        self.playback.resume()
        assert self.playback.get_time_position() != 0

    @populate_tracklist
    def test_seek_when_stopped(self):
        result = self.playback.seek(1000)
        assert result

    @unittest.SkipTest  # tkem doesn't know what's going on here
    @populate_tracklist
    def test_seek_when_stopped_updates_position(self):
        self.playback.seek(1000).get()
        position = self.playback.get_time_position()
        assert position >= 990

    def test_seek_on_empty_playlist(self):
        assert not self.playback.seek(0).get()

    def test_seek_on_empty_playlist_updates_position(self):
        self.playback.seek(0).get()
        self.assert_state_is(PlaybackState.STOPPED)

    @populate_tracklist
    def test_seek_when_stopped_triggers_play(self):
        self.playback.seek(0).get()
        self.assert_state_is(PlaybackState.PLAYING)

    @populate_tracklist
    def test_seek_when_playing(self):
        self.playback.play().get()
        result = self.playback.seek(self.tracks[0].length - 1000)
        assert result

    @populate_tracklist
    def test_seek_when_playing_updates_position(self):
        length = self.tracks[0].length
        self.playback.play().get()
        self.playback.seek(length - 1000).get()
        position = self.playback.get_time_position().get()
        assert position >= (length - 1010)

    @populate_tracklist
    def test_seek_when_paused(self):
        self.playback.play().get()
        self.playback.pause()
        result = self.playback.seek(self.tracks[0].length - 1000)
        assert result
        self.assert_state_is(PlaybackState.PAUSED)

    @populate_tracklist
    def test_seek_when_paused_updates_position(self):
        length = self.tracks[0].length
        self.playback.play().get()
        self.playback.pause()
        self.playback.seek(length - 1000)
        position = self.playback.get_time_position().get()
        assert position >= (length - 1010)

    @unittest.SkipTest
    @populate_tracklist
    def test_seek_beyond_end_of_song(self):
        # TODO: need to decide return value
        self.playback.play().get()
        result = self.playback.seek(self.tracks[0].length * 100)
        assert not result

    @populate_tracklist
    def test_seek_beyond_end_of_song_jumps_to_next_song(self):
        self.playback.play().get()
        self.playback.seek(self.tracks[0].length * 100).get()
        self.assert_current_track_is(self.tracks[1])

    @populate_tracklist
    def test_seek_beyond_end_of_song_for_last_track(self):
        self.playback.play(tlid=self.tl_tracks.get()[-1].tlid).get()
        self.playback.seek(self.tracks[-1].length * 100)
        self.assert_state_is(PlaybackState.STOPPED)

    @populate_tracklist
    def test_stop_when_stopped(self):
        self.playback.stop()
        self.assert_state_is(PlaybackState.STOPPED)

    @populate_tracklist
    def test_stop_when_playing(self):
        self.playback.play().get()
        self.playback.stop()
        self.assert_state_is(PlaybackState.STOPPED)

    @populate_tracklist
    def test_stop_when_paused(self):
        self.playback.play().get()
        self.playback.pause()
        self.playback.stop()
        self.assert_state_is(PlaybackState.STOPPED)

    def test_stop_return_value(self):
        self.playback.play().get()
        assert self.playback.stop().get() is None

    def test_time_position_when_stopped(self):
        assert self.playback.get_time_position().get() == 0

    @populate_tracklist
    def test_time_position_when_stopped_with_playlist(self):
        assert self.playback.get_time_position().get() == 0

    @unittest.SkipTest  # Uses sleep and does might not work with LocalBackend
    @populate_tracklist
    def test_time_position_when_playing(self):
        self.playback.play().get()
        first = self.playback.get_time_position().get()
        time.sleep(1)
        second = self.playback.get_time_position().get()
        assert second > first

    @populate_tracklist
    def test_time_position_when_paused(self):
        self.playback.play().get()
        self.playback.pause().get()
        first = self.playback.get_time_position().get()
        second = self.playback.get_time_position().get()
        assert first == second

    @populate_tracklist
    def test_play_with_consume(self):
        self.tracklist.set_consume(True)
        self.playback.play().get()
        self.assert_current_track_is(self.tracks[0])

    @populate_tracklist
    def test_playlist_is_empty_after_all_tracks_are_played_with_consume(self):
        self.tracklist.set_consume(True)
        self.playback.play().get()

        for _ in self.tracks:
            self.trigger_about_to_finish()
        # EOS should have trigger

        assert len(self.tracklist.get_tracks().get()) == 0

    @populate_tracklist
    @mock.patch("random.shuffle")
    def test_play_with_random(self, shuffle_mock):
        shuffle_mock.side_effect = lambda tracks: tracks.reverse()

        self.tracklist.set_random(True)
        self.playback.play().get()
        self.assert_current_track_is(self.tracks[-1])

    @populate_tracklist
    @mock.patch("random.shuffle")
    def test_previous_with_random(self, shuffle_mock):
        shuffle_mock.side_effect = lambda tracks: tracks.reverse()

        self.tracklist.set_random(True)
        self.playback.play().get()
        self.playback.next().get()
        current_track = self.playback.get_current_track().get()
        self.playback.previous()
        self.assert_current_track_is(current_track)

    @populate_tracklist
    def test_end_of_song_starts_next_track(self):
        self.playback.play().get()
        self.trigger_about_to_finish()
        self.assert_current_track_is(self.tracks[1])

    @populate_tracklist
    def test_end_of_song_with_single_and_repeat_starts_same(self):
        self.tracklist.set_single(True)
        self.tracklist.set_repeat(True)
        self.playback.play().get()
        self.assert_current_track_is(self.tracks[0])
        self.trigger_about_to_finish()
        self.assert_current_track_is(self.tracks[0])

    @populate_tracklist
    def test_end_of_song_with_single_random_and_repeat_starts_same(self):
        self.tracklist.set_single(True)
        self.tracklist.set_repeat(True)
        self.tracklist.set_random(True)
        self.playback.play().get()
        current_track = self.playback.get_current_track().get()
        self.trigger_about_to_finish()
        self.assert_current_track_is(current_track)

    @populate_tracklist
    def test_end_of_song_with_single_stops(self):
        self.tracklist.set_single(True)
        self.playback.play().get()
        self.assert_current_track_is(self.tracks[0])
        self.trigger_about_to_finish()
        self.assert_current_track_is(None)
        # EOS should have triggered
        self.assert_state_is(PlaybackState.STOPPED)

    @populate_tracklist
    def test_end_of_song_with_single_and_random_stops(self):
        self.tracklist.set_single(True)
        self.tracklist.set_random(True)
        self.playback.play().get()
        self.trigger_about_to_finish()
        # EOS should have triggered
        self.assert_current_track_is(None)
        self.assert_state_is(PlaybackState.STOPPED)

    @populate_tracklist
    def test_end_of_playlist_stops(self):
        self.playback.play(tlid=self.tl_tracks.get()[-1].tlid).get()
        self.trigger_about_to_finish()
        # EOS should have triggered
        self.assert_state_is(PlaybackState.STOPPED)

    def test_repeat_off_by_default(self):
        assert self.tracklist.get_repeat().get() is False

    def test_random_off_by_default(self):
        assert self.tracklist.get_random().get() is False

    def test_consume_off_by_default(self):
        assert self.tracklist.get_consume().get() is False

    @populate_tracklist
    def test_random_until_end_of_playlist(self):
        self.tracklist.set_random(True)
        self.playback.play().get()
        for _ in self.tracks[1:]:
            self.playback.next().get()
        self.assert_next_tl_track_is(None)

    @populate_tracklist
    def test_random_with_eot_until_end_of_playlist(self):
        self.tracklist.set_random(True)
        self.playback.play().get()
        for _ in self.tracks[1:]:
            self.trigger_about_to_finish()

        self.assert_eot_tl_track_is(None)

    @populate_tracklist
    def test_random_until_end_of_playlist_and_play_from_start(self):
        self.tracklist.set_random(True)
        self.playback.play().get()
        for _ in self.tracks:
            self.playback.next().get()
        self.assert_next_tl_track_is_not(None)
        self.assert_state_is(PlaybackState.STOPPED)
        self.playback.play().get()
        self.assert_state_is(PlaybackState.PLAYING)

    @populate_tracklist
    def test_random_with_eot_until_end_of_playlist_and_play_from_start(self):
        self.tracklist.set_random(True)
        self.playback.play().get()
        for _ in self.tracks:
            self.trigger_about_to_finish()
        # EOS should have triggered

        self.assert_eot_tl_track_is_not(None)
        self.assert_state_is(PlaybackState.STOPPED)
        self.playback.play().get()
        self.assert_state_is(PlaybackState.PLAYING)

    @populate_tracklist
    def test_random_until_end_of_playlist_with_repeat(self):
        self.tracklist.set_repeat(True)
        self.tracklist.set_random(True)
        self.playback.play().get()
        for _ in self.tracks[1:]:
            self.playback.next()
        self.assert_next_tl_track_is_not(None)

    @populate_tracklist
    def test_played_track_during_random_not_played_again(self):
        self.tracklist.set_random(True)
        self.playback.play().get()
        played = []
        for _ in self.tracks:
            track = self.playback.get_current_track().get()
            assert track not in played
            played.append(track)
            self.playback.next().get()

    @populate_tracklist
    @mock.patch("random.shuffle")
    def test_play_track_then_enable_random(self, shuffle_mock):
        # Covers underlying issue IssueGH17RegressionTest tests for.
        shuffle_mock.side_effect = lambda tracks: tracks.reverse()

        expected = self.tl_tracks.get()[::-1] + [None]
        actual = []

        self.playback.play().get()
        self.tracklist.set_random(True)
        while self.playback.get_state().get() != PlaybackState.STOPPED:
            self.playback.next().get()
            actual.append(self.playback.get_current_tl_track().get())
            if len(actual) > len(expected):
                break
        assert actual == expected
