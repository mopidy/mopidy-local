from __future__ import annotations

import time
import warnings
from typing import TYPE_CHECKING
from unittest import mock

import pytest
from mopidy.core import PlaybackController
from mopidy.models import TlTrack, Track
from mopidy.types import DurationMs, PlaybackState, Uri

from tests import generate_song

if TYPE_CHECKING:
    from mopidy.audio import AudioProxy
    from mopidy.backend import BackendProxy
    from mopidy.core import (
        CoreProxy,
        PlaybackControllerProxy,
        TracklistControllerProxy,
    )

# TODO: Test 'playlist repeat', e.g. repeat=1,single=0

# We need four tracks so that our shuffled track tests behave nicely with
# reversed as a fake shuffle. Ensuring that shuffled order is [4,3,2,1] and
# normal order [1,2,3,4] which means next_track != next_track_with_random
TRACKS = [Track(uri=generate_song(i), length=DurationMs(4464)) for i in (1, 2, 3, 4)]

assert len(TRACKS) >= 3, "Need at least three tracks to run tests."
assert TRACKS[0].length
assert TRACKS[0].length >= 2000, "First song needs to be at least 2000 miliseconds"


@pytest.fixture
def tl_tracks(tracklist: TracklistControllerProxy) -> list[TlTrack]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return tracklist.add(TRACKS).get()


def add_track(tracklist: TracklistControllerProxy, uri: Uri):
    track = Track(uri=uri, length=DurationMs(4464))
    tracklist.add([track])


def trigger_about_to_finish(audio: AudioProxy, playback: PlaybackControllerProxy):
    # Flush any queued core calls.
    playback.get_current_tl_track().get()

    callback = audio.get_about_to_finish_callback().get()
    callback()


def assert_state_is(playback: PlaybackControllerProxy, state: PlaybackState):
    assert playback.get_state().get() == state


def assert_current_track_is(playback: PlaybackControllerProxy, track: Track | None):
    assert playback.get_current_track().get() == track


def assert_current_track_is_not(playback: PlaybackControllerProxy, track: Track | None):
    assert playback.get_current_track().get() != track


def assert_current_track_index_is(
    tracklist: TracklistControllerProxy, index: int | None
):
    assert tracklist.index().get() == index


def assert_next_tl_track_is(
    tracklist: TracklistControllerProxy, tl_track: TlTrack | None
):
    next_tlid = tracklist.get_next_tlid().get()
    assert next_tlid == (tl_track and tl_track.tlid)


def assert_next_tl_track_is_not(
    tracklist: TracklistControllerProxy, tl_track: TlTrack | None
):
    next_tlid = tracklist.get_next_tlid().get()
    assert next_tlid != (tl_track and tl_track.tlid)


def assert_previous_tl_track_is(
    tracklist: TracklistControllerProxy, tl_track: TlTrack | None
):
    previous_tlid = tracklist.get_previous_tlid().get()
    assert previous_tlid == (tl_track and tl_track.tlid)


def assert_eot_tl_track_is(
    tracklist: TracklistControllerProxy, tl_track: TlTrack | None
):
    eot_tlid = tracklist.get_eot_tlid().get()
    assert eot_tlid == (tl_track and tl_track.tlid)


def assert_eot_tl_track_is_not(
    tracklist: TracklistControllerProxy, tl_track: TlTrack | None
):
    eot_tlid = tracklist.get_eot_tlid().get()
    assert eot_tlid != (tl_track and tl_track.tlid)


def test_uri_scheme(core: CoreProxy):
    assert "file" not in core.get_uri_schemes().get()
    assert "local" in core.get_uri_schemes().get()


def test_play_mp3(
    playback: PlaybackControllerProxy, tracklist: TracklistControllerProxy
):
    add_track(tracklist, "local:track:blank.mp3")
    playback.play().get()
    assert_state_is(playback, PlaybackState.PLAYING)


def test_play_ogg(
    playback: PlaybackControllerProxy, tracklist: TracklistControllerProxy
):
    add_track(tracklist, "local:track:blank.ogg")
    playback.play().get()
    assert_state_is(playback, PlaybackState.PLAYING)


def test_play_flac(
    playback: PlaybackControllerProxy, tracklist: TracklistControllerProxy
):
    add_track(tracklist, "local:track:blank.flac")
    playback.play().get()
    assert_state_is(playback, PlaybackState.PLAYING)


def test_play_uri_with_non_ascii_bytes(
    playback: PlaybackControllerProxy, tracklist: TracklistControllerProxy
):
    # Regression test: If trying to do .split(u':') on a bytestring, the
    # string will be decoded from ASCII to Unicode, which will crash on
    # non-ASCII strings, like the bytestring the following URI decodes to.
    add_track(tracklist, "local:track:12%20Doin%E2%80%99%20It%20Right.flac")
    playback.play().get()
    assert_state_is(playback, PlaybackState.PLAYING)


def test_initial_state_is_stopped(playback: PlaybackControllerProxy):
    assert_state_is(playback, PlaybackState.STOPPED)


def test_play_with_empty_playlist(playback: PlaybackControllerProxy):
    assert_state_is(playback, PlaybackState.STOPPED)
    playback.play().get()
    assert_state_is(playback, PlaybackState.STOPPED)


def test_play_with_empty_playlist_return_value(playback: PlaybackControllerProxy):
    assert playback.play().get() is None


@pytest.mark.usefixtures("tl_tracks")
def test_play_state(playback: PlaybackControllerProxy):
    assert_state_is(playback, PlaybackState.STOPPED)
    playback.play().get()
    assert_state_is(playback, PlaybackState.PLAYING)


@pytest.mark.usefixtures("tl_tracks")
def test_play_return_value(playback: PlaybackControllerProxy):
    assert playback.play().get() is None


def test_play_track_state(playback: PlaybackControllerProxy, tl_tracks: list[TlTrack]):
    assert_state_is(playback, PlaybackState.STOPPED)
    playback.play(tlid=tl_tracks[-1].tlid).get()
    assert_state_is(playback, PlaybackState.PLAYING)


def test_play_track_return_value(
    playback: PlaybackControllerProxy, tl_tracks: list[TlTrack]
):
    assert playback.play(tlid=tl_tracks[-1].tlid).get() is None


@pytest.mark.usefixtures("tl_tracks")
def test_play_when_playing(playback: PlaybackControllerProxy):
    playback.play().get()
    track = playback.get_current_track().get()
    playback.play().get()
    assert_current_track_is(playback, track)


@pytest.mark.usefixtures("tl_tracks")
def test_play_when_paused(playback: PlaybackControllerProxy):
    playback.play().get()
    track = playback.get_current_track().get()
    playback.pause().get()
    playback.play().get()
    assert_state_is(playback, PlaybackState.PLAYING)
    assert_current_track_is(playback, track)


@pytest.mark.usefixtures("tl_tracks")
def test_play_when_paused_after_next(playback: PlaybackControllerProxy):
    playback.play().get()
    playback.next().get()
    playback.next().get()
    track = playback.get_current_track().get()
    playback.pause().get()
    playback.play().get()
    assert_state_is(playback, PlaybackState.PLAYING)
    assert_current_track_is(playback, track)


@pytest.mark.usefixtures("tl_tracks")
def test_play_sets_current_track(playback: PlaybackControllerProxy):
    playback.play().get()
    assert_current_track_is(playback, TRACKS[0])


def test_play_track_sets_current_track(
    playback: PlaybackControllerProxy, tl_tracks: list[TlTrack]
):
    playback.play(tlid=tl_tracks[-1].tlid).get()
    assert_current_track_is(playback, TRACKS[-1])


@pytest.mark.usefixtures("tl_tracks")
def test_play_skips_to_next_track_on_failure(
    audio: AudioProxy, backend: BackendProxy, playback: PlaybackControllerProxy
):
    # If backend's play() returns False, it is a failure.
    uri = backend.playback.translate_uri(TRACKS[0].uri).get()
    audio.trigger_fake_playback_failure(uri)

    playback.play().get()
    assert_current_track_is_not(playback, TRACKS[0])
    assert_current_track_is(playback, TRACKS[1])


def test_current_track_after_completed_playlist(
    audio: AudioProxy, playback: PlaybackControllerProxy, tl_tracks: list[TlTrack]
):
    playback.play(tlid=tl_tracks[-1].tlid).get()
    trigger_about_to_finish(audio, playback)
    # EOS should have triggered
    assert_state_is(playback, PlaybackState.STOPPED)
    assert_current_track_is(playback, None)

    playback.play(tlid=tl_tracks[-1].tlid).get()
    playback.next().get()
    assert_state_is(playback, PlaybackState.STOPPED)
    assert_current_track_is(playback, None)


@pytest.mark.usefixtures("tl_tracks")
def test_previous(playback: PlaybackControllerProxy):
    playback.play().get()
    playback.next().get()
    playback.previous().get()
    assert_current_track_is(playback, TRACKS[0])


@pytest.mark.usefixtures("tl_tracks")
def test_previous_more(playback: PlaybackControllerProxy):
    playback.play().get()  # At track 0
    playback.next().get()  # At track 1
    playback.next().get()  # At track 2
    playback.previous().get()  # At track 1
    assert_current_track_is(playback, TRACKS[1])


@pytest.mark.usefixtures("tl_tracks")
def test_previous_return_value(playback: PlaybackControllerProxy):
    playback.play().get()
    playback.next().get()
    assert playback.previous().get() is None


@pytest.mark.usefixtures("tl_tracks")
def test_previous_does_not_trigger_playback(playback: PlaybackControllerProxy):
    playback.play().get()
    playback.next().get()
    playback.stop()
    playback.previous().get()
    assert_state_is(playback, PlaybackState.STOPPED)


@pytest.mark.usefixtures("tl_tracks")
def test_previous_at_start_of_playlist(playback: PlaybackControllerProxy):
    playback.previous().get()
    assert_state_is(playback, PlaybackState.STOPPED)
    assert_current_track_is(playback, None)


def test_previous_for_empty_playlist(playback: PlaybackControllerProxy):
    playback.previous().get()
    assert_state_is(playback, PlaybackState.STOPPED)
    assert_current_track_is(playback, None)


def test_previous_skips_to_previous_track_on_failure(
    audio: AudioProxy,
    backend: BackendProxy,
    playback: PlaybackControllerProxy,
    tl_tracks: list[TlTrack],
):
    # If backend's play() returns False, it is a failure.
    uri = backend.playback.translate_uri(TRACKS[1].uri).get()
    audio.trigger_fake_playback_failure(uri)

    playback.play(tlid=tl_tracks[2].tlid).get()
    assert_current_track_is(playback, TRACKS[2])
    playback.previous().get()
    assert_current_track_is_not(playback, TRACKS[1])
    assert_current_track_is(playback, TRACKS[0])


@pytest.mark.usefixtures("tl_tracks")
def test_next(playback: PlaybackControllerProxy, tracklist: TracklistControllerProxy):
    playback.play().get()

    old_track = playback.get_current_track().get()
    old_position = tracklist.index().get()

    playback.next().get()

    assert tracklist.index().get() == (old_position + 1)
    assert_current_track_is_not(playback, old_track)


@pytest.mark.usefixtures("tl_tracks")
def test_next_return_value(playback: PlaybackControllerProxy):
    playback.play().get()
    assert playback.next().get() is None


@pytest.mark.usefixtures("tl_tracks")
def test_next_does_not_trigger_playback(playback: PlaybackControllerProxy):
    playback.next().get()
    assert_state_is(playback, PlaybackState.STOPPED)


@pytest.mark.usefixtures("tl_tracks")
def test_next_at_end_of_playlist(
    playback: PlaybackControllerProxy, tracklist: TracklistControllerProxy
):
    playback.play().get()

    for i, track in enumerate(TRACKS):
        assert_state_is(playback, PlaybackState.PLAYING)
        assert_current_track_is(playback, track)
        assert tracklist.index().get() == i

        playback.next()

    assert_state_is(playback, PlaybackState.STOPPED)


@pytest.mark.usefixtures("tl_tracks")
def test_next_until_end_of_playlist_and_play_from_start(
    playback: PlaybackControllerProxy,
):
    playback.play().get()

    for _ in TRACKS:
        playback.next().get()

    assert_current_track_is(playback, None)
    assert_state_is(playback, PlaybackState.STOPPED)

    playback.play().get()
    assert_state_is(playback, PlaybackState.PLAYING)
    assert_current_track_is(playback, TRACKS[0])


def test_next_for_empty_playlist(playback: PlaybackControllerProxy):
    playback.next().get()
    assert_state_is(playback, PlaybackState.STOPPED)


@pytest.mark.usefixtures("tl_tracks")
def test_next_skips_to_next_track_on_failure(
    audio: AudioProxy, backend: BackendProxy, playback: PlaybackControllerProxy
):
    # If backend's play() returns False, it is a failure.
    uri = backend.playback.translate_uri(TRACKS[1].uri).get()
    audio.trigger_fake_playback_failure(uri)

    playback.play().get()
    assert_current_track_is(playback, TRACKS[0])
    playback.next().get()
    assert_current_track_is_not(playback, TRACKS[1])
    assert_current_track_is(playback, TRACKS[2])


def test_next_track_before_play(
    tracklist: TracklistControllerProxy, tl_tracks: list[TlTrack]
):
    assert_next_tl_track_is(tracklist, tl_tracks[0])


def test_next_track_during_play(
    playback: PlaybackControllerProxy,
    tracklist: TracklistControllerProxy,
    tl_tracks: list[TlTrack],
):
    playback.play().get()
    assert_next_tl_track_is(tracklist, tl_tracks[1])


def test_next_track_after_previous(
    playback: PlaybackControllerProxy,
    tracklist: TracklistControllerProxy,
    tl_tracks: list[TlTrack],
):
    playback.play().get()
    playback.next().get()
    playback.previous().get()
    assert_next_tl_track_is(tracklist, tl_tracks[1])


def test_next_track_empty_playlist(tracklist: TracklistControllerProxy):
    assert_next_tl_track_is(tracklist, None)


def test_next_track_at_end_of_playlist(
    playback: PlaybackControllerProxy,
    tracklist: TracklistControllerProxy,
    tl_tracks: list[TlTrack],
):
    playback.play().get()
    for _ in tl_tracks[1:]:
        playback.next().get()
    assert_next_tl_track_is(tracklist, None)


def test_next_track_at_end_of_playlist_with_repeat(
    playback: PlaybackControllerProxy,
    tracklist: TracklistControllerProxy,
    tl_tracks: list[TlTrack],
):
    tracklist.set_repeat(True)
    playback.play().get()
    for _ in TRACKS[1:]:
        playback.next().get()
    assert_next_tl_track_is(tracklist, tl_tracks[0])


@mock.patch("random.shuffle")
def test_next_track_with_random(
    shuffle_mock: mock.Mock,
    tracklist: TracklistControllerProxy,
    tl_tracks: list[TlTrack],
):
    shuffle_mock.side_effect = lambda tracks: tracks.reverse()

    tracklist.set_random(True)
    assert_next_tl_track_is(tracklist, tl_tracks[-1])


@pytest.mark.usefixtures("tl_tracks")
def test_next_with_consume(
    playback: PlaybackControllerProxy, tracklist: TracklistControllerProxy
):
    tracklist.set_consume(True)
    playback.play().get()
    playback.next().get()
    assert TRACKS[0] not in tracklist.get_tracks().get()


@pytest.mark.usefixtures("tl_tracks")
def test_next_with_single_and_repeat(
    playback: PlaybackControllerProxy, tracklist: TracklistControllerProxy
):
    tracklist.set_single(True)
    tracklist.set_repeat(True)
    playback.play().get()
    assert_current_track_is(playback, TRACKS[0])
    playback.next().get()
    assert_current_track_is(playback, TRACKS[1])


@mock.patch("random.shuffle")
@pytest.mark.usefixtures("tl_tracks")
def test_next_with_random(
    shuffle_mock: mock.Mock,
    playback: PlaybackControllerProxy,
    tracklist: TracklistControllerProxy,
):
    shuffle_mock.side_effect = lambda tracks: tracks.reverse()

    tracklist.set_random(True)
    playback.play().get()
    assert_current_track_is(playback, TRACKS[-1])
    playback.next().get()
    assert_current_track_is(playback, TRACKS[-2])


@mock.patch("random.shuffle")
def test_next_track_with_random_after_append_playlist(
    shuffle_mock: mock.Mock,
    tracklist: TracklistControllerProxy,
    tl_tracks: list[TlTrack],
):
    shuffle_mock.side_effect = lambda tracks: tracks.reverse()

    tracklist.set_random(True)

    expected_tl_track = tl_tracks[-1]
    next_tlid = tracklist.get_next_tlid().get()

    # Baseline checking that first next_track is last tl track per our fake
    # shuffle.
    assert next_tlid == expected_tl_track.tlid

    tracklist.add(TRACKS[:1])

    old_next_tlid = next_tlid
    expected_tl_track = tracklist.get_tl_tracks().get()[-1]
    next_tlid = tracklist.get_next_tlid().get()

    # Verify that first next track has changed since we added to the
    # playlist.
    assert next_tlid == expected_tl_track.tlid
    assert next_tlid != old_next_tlid


@pytest.mark.usefixtures("tl_tracks")
def test_end_of_track(
    audio: AudioProxy,
    playback: PlaybackControllerProxy,
    tracklist: TracklistControllerProxy,
):
    playback.play().get()

    old_track = playback.get_current_track().get()
    old_position = tracklist.index().get()

    trigger_about_to_finish(audio, playback)

    new_track = playback.get_current_track().get()
    assert tracklist.index().get() == (old_position + 1)
    assert new_track.uri != old_track.uri


@pytest.mark.usefixtures("tl_tracks")
def test_end_of_track_return_value(
    audio: AudioProxy, playback: PlaybackControllerProxy
):
    playback.play().get()
    assert trigger_about_to_finish(audio, playback) is None


@pytest.mark.usefixtures("tl_tracks")
def test_end_of_track_does_not_trigger_playback(
    audio: AudioProxy, playback: PlaybackControllerProxy
):
    trigger_about_to_finish(audio, playback)
    assert_state_is(playback, PlaybackState.STOPPED)


@pytest.mark.usefixtures("tl_tracks")
def test_end_of_track_at_end_of_playlist(
    audio: AudioProxy,
    playback: PlaybackControllerProxy,
    tracklist: TracklistControllerProxy,
):
    playback.play().get()

    for i, track in enumerate(TRACKS):
        assert_state_is(playback, PlaybackState.PLAYING)
        assert_current_track_is(playback, track)
        assert tracklist.index().get() == i

        trigger_about_to_finish(audio, playback)

    assert_state_is(playback, PlaybackState.STOPPED)


@pytest.mark.usefixtures("tl_tracks")
def test_end_of_track_until_end_of_playlist_and_play_from_start(
    audio: AudioProxy, playback: PlaybackControllerProxy
):
    playback.play().get()

    for _ in TRACKS:
        trigger_about_to_finish(audio, playback)

    assert playback.get_current_track().get() is None
    assert_state_is(playback, PlaybackState.STOPPED)

    playback.play().get()
    assert_state_is(playback, PlaybackState.PLAYING)
    assert_current_track_is(playback, TRACKS[0])


def test_end_of_track_for_empty_playlist(
    audio: AudioProxy, playback: PlaybackControllerProxy
):
    trigger_about_to_finish(audio, playback)
    assert_state_is(playback, PlaybackState.STOPPED)


# TODO: On about to finish does not handle skipping to next track yet.
@pytest.mark.xfail(strict=True)
@pytest.mark.usefixtures("tl_tracks")
def test_end_of_track_skips_to_next_track_on_failure(
    audio: AudioProxy, backend: BackendProxy, playback: PlaybackControllerProxy
):
    # If backend's play() returns False, it is a failure.
    return_values = [True, False, True]
    backend.playback.play = return_values.pop
    playback.play().get()
    assert_current_track_is(playback, TRACKS[0])
    trigger_about_to_finish(audio, playback)
    assert_current_track_is_not(playback, TRACKS[1])
    assert_current_track_is(playback, TRACKS[2])


def test_end_of_track_track_before_play(
    tracklist: TracklistControllerProxy, tl_tracks: list[TlTrack]
):
    assert_next_tl_track_is(tracklist, tl_tracks[0])


def test_end_of_track_track_during_play(
    playback: PlaybackControllerProxy,
    tracklist: TracklistControllerProxy,
    tl_tracks: list[TlTrack],
):
    playback.play().get()
    assert_next_tl_track_is(tracklist, tl_tracks[1])


def test_about_to_finish_after_previous(
    audio: AudioProxy,
    playback: PlaybackControllerProxy,
    tracklist: TracklistControllerProxy,
    tl_tracks: list[TlTrack],
):
    playback.play().get()
    trigger_about_to_finish(audio, playback)
    playback.previous().get()
    assert_next_tl_track_is(tracklist, tl_tracks[1])


def test_end_of_track_track_empty_playlist(tracklist: TracklistControllerProxy):
    assert_next_tl_track_is(tracklist, None)


@pytest.mark.usefixtures("tl_tracks")
def test_end_of_track_track_at_end_of_playlist(
    audio: AudioProxy,
    playback: PlaybackControllerProxy,
    tracklist: TracklistControllerProxy,
):
    playback.play().get()
    for _ in TRACKS[1:]:
        trigger_about_to_finish(audio, playback)

    assert_next_tl_track_is(tracklist, None)


def test_end_of_track_track_at_end_of_playlist_with_repeat(
    audio: AudioProxy,
    playback: PlaybackControllerProxy,
    tracklist: TracklistControllerProxy,
    tl_tracks: list[TlTrack],
):
    tracklist.set_repeat(True)
    playback.play().get()
    for _ in TRACKS[1:]:
        trigger_about_to_finish(audio, playback)

    assert_next_tl_track_is(tracklist, tl_tracks[0])


@mock.patch("random.shuffle")
def test_end_of_track_track_with_random(
    shuffle_mock: mock.Mock,
    tracklist: TracklistControllerProxy,
    tl_tracks: list[TlTrack],
):
    shuffle_mock.side_effect = lambda tracks: tracks.reverse()

    tracklist.set_random(True)
    assert_next_tl_track_is(tracklist, tl_tracks[-1])


@pytest.mark.usefixtures("tl_tracks")
def test_end_of_track_with_consume(
    audio: AudioProxy,
    playback: PlaybackControllerProxy,
    tracklist: TracklistControllerProxy,
):
    tracklist.set_consume(True)
    playback.play().get()
    trigger_about_to_finish(audio, playback)
    assert TRACKS[0] not in tracklist.get_tracks().get()


@mock.patch("random.shuffle")
@pytest.mark.usefixtures("tl_tracks")
def test_end_of_track_with_random(
    shuffle_mock: mock.Mock,
    audio: AudioProxy,
    playback: PlaybackControllerProxy,
    tracklist: TracklistControllerProxy,
):
    shuffle_mock.side_effect = lambda tracks: tracks.reverse()

    tracklist.set_random(True)
    playback.play().get()
    assert_current_track_is(playback, TRACKS[-1])
    trigger_about_to_finish(audio, playback)
    assert_current_track_is(playback, TRACKS[-2])


@mock.patch("random.shuffle")
@pytest.mark.usefixtures("tl_tracks")
def test_end_of_track_track_with_random_after_append_playlist(
    shuffle_mock: mock.Mock, tracklist: TracklistControllerProxy
):
    shuffle_mock.side_effect = lambda tracks: tracks.reverse()

    tracklist.set_random(True)

    expected_tl_track = tracklist.get_tl_tracks().get()[-1]
    eot_tlid = tracklist.get_eot_tlid().get()

    # Baseline checking that first eot_track is last tl track per our fake
    # shuffle.
    assert eot_tlid == expected_tl_track.tlid

    tracklist.add(TRACKS[:1])

    old_eot_tlid = eot_tlid
    expected_tl_track = tracklist.get_tl_tracks().get()[-1]
    eot_tlid = tracklist.get_eot_tlid().get()

    # Verify that first next track has changed since we added to the
    # playlist.
    assert eot_tlid == expected_tl_track.tlid
    assert eot_tlid != old_eot_tlid


@pytest.mark.usefixtures("tl_tracks")
def test_previous_track_before_play(tracklist: TracklistControllerProxy):
    assert_previous_tl_track_is(tracklist, None)


@pytest.mark.usefixtures("tl_tracks")
def test_previous_track_after_play(
    playback: PlaybackControllerProxy, tracklist: TracklistControllerProxy
):
    playback.play().get()
    assert_previous_tl_track_is(tracklist, None)


def test_previous_track_after_next(
    playback: PlaybackControllerProxy,
    tracklist: TracklistControllerProxy,
    tl_tracks: list[TlTrack],
):
    playback.play().get()
    playback.next().get()
    assert_previous_tl_track_is(tracklist, tl_tracks[0])


def test_previous_track_after_previous(
    playback: PlaybackControllerProxy,
    tracklist: TracklistControllerProxy,
    tl_tracks: list[TlTrack],
):
    playback.play().get()  # At track 0
    playback.next().get()  # At track 1
    playback.next().get()  # At track 2
    playback.previous().get()  # At track 1
    assert_previous_tl_track_is(tracklist, tl_tracks[0])


def test_previous_track_empty_playlist(tracklist: TracklistControllerProxy):
    assert_previous_tl_track_is(tracklist, None)


@pytest.mark.usefixtures("tl_tracks")
def test_previous_track_with_consume(
    playback: PlaybackControllerProxy, tracklist: TracklistControllerProxy
):
    tracklist.set_consume(True)
    for _ in TRACKS:
        playback.next()
        current = playback.get_current_tl_track().get()
        assert_previous_tl_track_is(tracklist, current)


@pytest.mark.usefixtures("tl_tracks")
def test_previous_track_with_random(
    playback: PlaybackControllerProxy, tracklist: TracklistControllerProxy
):
    tracklist.set_random(True)
    for _ in TRACKS:
        playback.next()
        current = playback.get_current_tl_track().get()
        assert_previous_tl_track_is(tracklist, current)


@pytest.mark.usefixtures("tl_tracks")
def test_initial_current_track(playback: PlaybackControllerProxy):
    assert_current_track_is(playback, None)


@pytest.mark.usefixtures("tl_tracks")
def test_current_track_during_play(playback: PlaybackControllerProxy):
    playback.play().get()
    assert_current_track_is(playback, TRACKS[0])


@pytest.mark.usefixtures("tl_tracks")
def test_current_track_after_next(playback: PlaybackControllerProxy):
    playback.play()
    playback.next().get()
    assert_current_track_is(playback, TRACKS[1])


@pytest.mark.usefixtures("tl_tracks")
def test_initial_tracklist_position(tracklist: TracklistControllerProxy):
    assert tracklist.index().get() is None


@pytest.mark.usefixtures("tl_tracks")
def test_tracklist_position_during_play(
    playback: PlaybackControllerProxy, tracklist: TracklistControllerProxy
):
    playback.play().get()
    assert_current_track_index_is(tracklist, 0)


@pytest.mark.usefixtures("tl_tracks")
def test_tracklist_position_after_next(
    playback: PlaybackControllerProxy, tracklist: TracklistControllerProxy
):
    playback.play().get()
    playback.next().get()
    assert_current_track_index_is(tracklist, 1)


def test_tracklist_position_at_end_of_playlist(
    audio: AudioProxy,
    playback: PlaybackControllerProxy,
    tracklist: TracklistControllerProxy,
    tl_tracks: list[TlTrack],
):
    playback.play(tlid=tl_tracks[-1].tlid).get()
    trigger_about_to_finish(audio, playback)
    # EOS should have triggered
    assert_current_track_index_is(tracklist, None)


@mock.patch.object(PlaybackController, "_on_tracklist_change")
def test_on_tracklist_change_gets_called(
    change_mock: mock.Mock, tracklist: TracklistControllerProxy
):
    tracklist.add([Track(uri="a")]).get()
    change_mock.assert_called_once_with()


@pytest.mark.usefixtures("tl_tracks")
def test_on_tracklist_change_when_playing(
    playback: PlaybackControllerProxy, tracklist: TracklistControllerProxy
):
    playback.play().get()
    current_track = playback.get_current_track().get()
    tracklist.add([TRACKS[2]])
    assert_state_is(playback, PlaybackState.PLAYING)
    assert_current_track_is(playback, current_track)


@pytest.mark.usefixtures("tl_tracks")
def test_on_tracklist_change_when_stopped(
    playback: PlaybackControllerProxy, tracklist: TracklistControllerProxy
):
    tracklist.add([TRACKS[2]])
    assert_state_is(playback, PlaybackState.STOPPED)
    assert_current_track_is(playback, None)


@pytest.mark.usefixtures("tl_tracks")
def test_on_tracklist_change_when_paused(
    playback: PlaybackControllerProxy, tracklist: TracklistControllerProxy
):
    playback.play().get()
    playback.pause()
    current_track = playback.get_current_track().get()
    tracklist.add([TRACKS[2]])
    assert_state_is(playback, PlaybackState.PAUSED)
    assert_current_track_is(playback, current_track)


@pytest.mark.usefixtures("tl_tracks")
def test_pause_when_stopped(playback: PlaybackControllerProxy):
    playback.pause()
    assert_state_is(playback, PlaybackState.PAUSED)


@pytest.mark.usefixtures("tl_tracks")
def test_pause_when_playing(playback: PlaybackControllerProxy):
    playback.play().get()
    playback.pause()
    assert_state_is(playback, PlaybackState.PAUSED)


@pytest.mark.usefixtures("tl_tracks")
def test_pause_when_paused(playback: PlaybackControllerProxy):
    playback.play().get()
    playback.pause()
    playback.pause()
    assert_state_is(playback, PlaybackState.PAUSED)


@pytest.mark.usefixtures("tl_tracks")
def test_pause_return_value(playback: PlaybackControllerProxy):
    playback.play().get()
    assert playback.pause().get() is None


@pytest.mark.usefixtures("tl_tracks")
def test_resume_when_stopped(playback: PlaybackControllerProxy):
    playback.resume()
    assert_state_is(playback, PlaybackState.STOPPED)


@pytest.mark.usefixtures("tl_tracks")
def test_resume_when_playing(playback: PlaybackControllerProxy):
    playback.play().get()
    playback.resume()
    assert_state_is(playback, PlaybackState.PLAYING)


@pytest.mark.usefixtures("tl_tracks")
def test_resume_when_paused(playback: PlaybackControllerProxy):
    playback.play().get()
    playback.pause()
    playback.resume()
    assert_state_is(playback, PlaybackState.PLAYING)


@pytest.mark.usefixtures("tl_tracks")
def test_resume_return_value(playback: PlaybackControllerProxy):
    playback.play().get()
    playback.pause()
    assert playback.resume().get() is None


@pytest.mark.skip(reason="Uses sleep and might not work with LocalBackend")
@pytest.mark.usefixtures("tl_tracks")
def test_resume_continues_from_right_position(playback: PlaybackControllerProxy):
    playback.play().get()
    time.sleep(0.2)
    playback.pause()
    playback.resume()
    assert playback.get_time_position() != 0


@pytest.mark.usefixtures("tl_tracks")
def test_seek_when_stopped(playback: PlaybackControllerProxy):
    result = playback.seek(1000)
    assert result


@pytest.mark.skip(reason="tkem doesn't know what's going on here")
@pytest.mark.usefixtures("tl_tracks")
def test_seek_when_stopped_updates_position(playback: PlaybackControllerProxy):
    playback.seek(1000).get()
    position = playback.get_time_position()
    assert position >= 990


def test_seek_on_empty_playlist(playback: PlaybackControllerProxy):
    assert not playback.seek(0).get()


def test_seek_on_empty_playlist_updates_position(playback: PlaybackControllerProxy):
    playback.seek(0).get()
    assert_state_is(playback, PlaybackState.STOPPED)


@pytest.mark.usefixtures("tl_tracks")
def test_seek_when_stopped_triggers_play(playback: PlaybackControllerProxy):
    playback.seek(0).get()
    assert_state_is(playback, PlaybackState.PLAYING)


@pytest.mark.usefixtures("tl_tracks")
def test_seek_when_playing(playback: PlaybackControllerProxy):
    playback.play().get()
    result = playback.seek(TRACKS[0].length - 1000)
    assert result


@pytest.mark.usefixtures("tl_tracks")
def test_seek_when_playing_updates_position(playback: PlaybackControllerProxy):
    length = TRACKS[0].length
    playback.play().get()
    playback.seek(length - 1000).get()
    position = playback.get_time_position().get()
    assert position >= (length - 1010)


@pytest.mark.usefixtures("tl_tracks")
def test_seek_when_paused(playback: PlaybackControllerProxy):
    playback.play().get()
    playback.pause()
    result = playback.seek(TRACKS[0].length - 1000)
    assert result
    assert_state_is(playback, PlaybackState.PAUSED)


@pytest.mark.usefixtures("tl_tracks")
def test_seek_when_paused_updates_position(playback: PlaybackControllerProxy):
    length = TRACKS[0].length
    playback.play().get()
    playback.pause()
    playback.seek(length - 1000)
    position = playback.get_time_position().get()
    assert position >= (length - 1010)


@pytest.mark.skip
@pytest.mark.usefixtures("tl_tracks")
def test_seek_beyond_end_of_song(playback: PlaybackControllerProxy):
    # TODO: need to decide return value
    playback.play().get()
    result = playback.seek(TRACKS[0].length * 100)
    assert not result


@pytest.mark.usefixtures("tl_tracks")
def test_seek_beyond_end_of_song_jumps_to_next_song(playback: PlaybackControllerProxy):
    playback.play().get()
    playback.seek(TRACKS[0].length * 100).get()
    assert_current_track_is(playback, TRACKS[1])


def test_seek_beyond_end_of_song_for_last_track(
    playback: PlaybackControllerProxy, tl_tracks: list[TlTrack]
):
    playback.play(tlid=tl_tracks[-1].tlid).get()
    playback.seek(TRACKS[-1].length * 100)
    assert_state_is(playback, PlaybackState.STOPPED)


@pytest.mark.usefixtures("tl_tracks")
def test_stop_when_stopped(playback: PlaybackControllerProxy):
    playback.stop()
    assert_state_is(playback, PlaybackState.STOPPED)


@pytest.mark.usefixtures("tl_tracks")
def test_stop_when_playing(playback: PlaybackControllerProxy):
    playback.play().get()
    playback.stop()
    assert_state_is(playback, PlaybackState.STOPPED)


@pytest.mark.usefixtures("tl_tracks")
def test_stop_when_paused(playback: PlaybackControllerProxy):
    playback.play().get()
    playback.pause()
    playback.stop()
    assert_state_is(playback, PlaybackState.STOPPED)


def test_stop_return_value(playback: PlaybackControllerProxy):
    playback.play().get()
    assert playback.stop().get() is None


def test_time_position_when_stopped(playback: PlaybackControllerProxy):
    assert playback.get_time_position().get() == 0


@pytest.mark.usefixtures("tl_tracks")
def test_time_position_when_stopped_with_playlist(playback: PlaybackControllerProxy):
    assert playback.get_time_position().get() == 0


@pytest.mark.skip(reason="Uses sleep and does might not work with LocalBackend")
@pytest.mark.usefixtures("tl_tracks")
def test_time_position_when_playing(playback: PlaybackControllerProxy):
    playback.play().get()
    first = playback.get_time_position().get()
    time.sleep(1)
    second = playback.get_time_position().get()
    assert second > first


@pytest.mark.usefixtures("tl_tracks")
def test_time_position_when_paused(playback: PlaybackControllerProxy):
    playback.play().get()
    playback.pause().get()
    first = playback.get_time_position().get()
    second = playback.get_time_position().get()
    assert first == second


@pytest.mark.usefixtures("tl_tracks")
def test_play_with_consume(
    playback: PlaybackControllerProxy, tracklist: TracklistControllerProxy
):
    tracklist.set_consume(True)
    playback.play().get()
    assert_current_track_is(playback, TRACKS[0])


@pytest.mark.usefixtures("tl_tracks")
def test_playlist_is_empty_after_all_tracks_are_played_with_consume(
    audio: AudioProxy,
    playback: PlaybackControllerProxy,
    tracklist: TracklistControllerProxy,
):
    tracklist.set_consume(True)
    playback.play().get()

    for _ in TRACKS:
        trigger_about_to_finish(audio, playback)
    # EOS should have trigger

    assert len(tracklist.get_tracks().get()) == 0


@mock.patch("random.shuffle")
@pytest.mark.usefixtures("tl_tracks")
def test_play_with_random(
    shuffle_mock: mock.Mock,
    playback: PlaybackControllerProxy,
    tracklist: TracklistControllerProxy,
):
    shuffle_mock.side_effect = lambda tracks: tracks.reverse()

    tracklist.set_random(True)
    playback.play().get()
    assert_current_track_is(playback, TRACKS[-1])


@mock.patch("random.shuffle")
@pytest.mark.usefixtures("tl_tracks")
def test_previous_with_random(
    shuffle_mock: mock.Mock,
    playback: PlaybackControllerProxy,
    tracklist: TracklistControllerProxy,
):
    shuffle_mock.side_effect = lambda tracks: tracks.reverse()

    tracklist.set_random(True)
    playback.play().get()
    playback.next().get()
    current_track = playback.get_current_track().get()
    playback.previous()
    assert_current_track_is(playback, current_track)


@pytest.mark.usefixtures("tl_tracks")
def test_end_of_song_starts_next_track(
    audio: AudioProxy, playback: PlaybackControllerProxy
):
    playback.play().get()
    trigger_about_to_finish(audio, playback)
    assert_current_track_is(playback, TRACKS[1])


@pytest.mark.usefixtures("tl_tracks")
def test_end_of_song_with_single_and_repeat_starts_same(
    audio: AudioProxy,
    playback: PlaybackControllerProxy,
    tracklist: TracklistControllerProxy,
):
    tracklist.set_single(True)
    tracklist.set_repeat(True)
    playback.play().get()
    assert_current_track_is(playback, TRACKS[0])
    trigger_about_to_finish(audio, playback)
    assert_current_track_is(playback, TRACKS[0])


@pytest.mark.usefixtures("tl_tracks")
def test_end_of_song_with_single_random_and_repeat_starts_same(
    audio: AudioProxy,
    playback: PlaybackControllerProxy,
    tracklist: TracklistControllerProxy,
):
    tracklist.set_single(True)
    tracklist.set_repeat(True)
    tracklist.set_random(True)
    playback.play().get()
    current_track = playback.get_current_track().get()
    trigger_about_to_finish(audio, playback)
    assert_current_track_is(playback, current_track)


@pytest.mark.usefixtures("tl_tracks")
def test_end_of_song_with_single_stops(
    audio: AudioProxy,
    playback: PlaybackControllerProxy,
    tracklist: TracklistControllerProxy,
):
    tracklist.set_single(True)
    playback.play().get()
    assert_current_track_is(playback, TRACKS[0])
    trigger_about_to_finish(audio, playback)
    assert_current_track_is(playback, None)
    # EOS should have triggered
    assert_state_is(playback, PlaybackState.STOPPED)


@pytest.mark.usefixtures("tl_tracks")
def test_end_of_song_with_single_and_random_stops(
    audio: AudioProxy,
    playback: PlaybackControllerProxy,
    tracklist: TracklistControllerProxy,
):
    tracklist.set_single(True)
    tracklist.set_random(True)
    playback.play().get()
    trigger_about_to_finish(audio, playback)
    # EOS should have triggered
    assert_current_track_is(playback, None)
    assert_state_is(playback, PlaybackState.STOPPED)


def test_end_of_playlist_stops(
    audio: AudioProxy, playback: PlaybackControllerProxy, tl_tracks: list[TlTrack]
):
    playback.play(tlid=tl_tracks[-1].tlid).get()
    trigger_about_to_finish(audio, playback)
    # EOS should have triggered
    assert_state_is(playback, PlaybackState.STOPPED)


def test_repeat_off_by_default(tracklist: TracklistControllerProxy):
    assert tracklist.get_repeat().get() is False


def test_random_off_by_default(tracklist: TracklistControllerProxy):
    assert tracklist.get_random().get() is False


def test_consume_off_by_default(tracklist: TracklistControllerProxy):
    assert tracklist.get_consume().get() is False


@pytest.mark.usefixtures("tl_tracks")
def test_random_until_end_of_playlist(
    playback: PlaybackControllerProxy, tracklist: TracklistControllerProxy
):
    tracklist.set_random(True)
    playback.play().get()
    for _ in TRACKS[1:]:
        playback.next().get()
    assert_next_tl_track_is(tracklist, None)


@pytest.mark.usefixtures("tl_tracks")
def test_random_with_eot_until_end_of_playlist(
    audio: AudioProxy,
    playback: PlaybackControllerProxy,
    tracklist: TracklistControllerProxy,
):
    tracklist.set_random(True)
    playback.play().get()
    for _ in TRACKS[1:]:
        trigger_about_to_finish(audio, playback)

    assert_eot_tl_track_is(tracklist, None)


@pytest.mark.usefixtures("tl_tracks")
def test_random_until_end_of_playlist_and_play_from_start(
    playback: PlaybackControllerProxy, tracklist: TracklistControllerProxy
):
    tracklist.set_random(True)
    playback.play().get()
    for _ in TRACKS:
        playback.next().get()
    assert_next_tl_track_is_not(tracklist, None)
    assert_state_is(playback, PlaybackState.STOPPED)
    playback.play().get()
    assert_state_is(playback, PlaybackState.PLAYING)


@pytest.mark.usefixtures("tl_tracks")
def test_random_with_eot_until_end_of_playlist_and_play_from_start(
    audio: AudioProxy,
    playback: PlaybackControllerProxy,
    tracklist: TracklistControllerProxy,
):
    tracklist.set_random(True)
    playback.play().get()
    for _ in TRACKS:
        trigger_about_to_finish(audio, playback)
    # EOS should have triggered

    assert_eot_tl_track_is_not(tracklist, None)
    assert_state_is(playback, PlaybackState.STOPPED)
    playback.play().get()
    assert_state_is(playback, PlaybackState.PLAYING)


@pytest.mark.usefixtures("tl_tracks")
def test_random_until_end_of_playlist_with_repeat(
    playback: PlaybackControllerProxy, tracklist: TracklistControllerProxy
):
    tracklist.set_repeat(True)
    tracklist.set_random(True)
    playback.play().get()
    for _ in TRACKS[1:]:
        playback.next()
    assert_next_tl_track_is_not(tracklist, None)


@pytest.mark.usefixtures("tl_tracks")
def test_played_track_during_random_not_played_again(
    playback: PlaybackControllerProxy, tracklist: TracklistControllerProxy
):
    tracklist.set_random(True)
    playback.play().get()
    played = []
    for _ in TRACKS:
        track = playback.get_current_track().get()
        assert track not in played
        played.append(track)
        playback.next().get()


@mock.patch("random.shuffle")
def test_play_track_then_enable_random(
    shuffle_mock: mock.Mock,
    playback: PlaybackControllerProxy,
    tracklist: TracklistControllerProxy,
    tl_tracks: list[TlTrack],
):
    # Covers underlying issue IssueGH17RegressionTest tests for.
    shuffle_mock.side_effect = lambda tracks: tracks.reverse()

    expected = [*tl_tracks[::-1], None]
    actual = []

    playback.play().get()
    tracklist.set_random(True)
    while playback.get_state().get() != PlaybackState.STOPPED:
        playback.next().get()
        actual.append(playback.get_current_tl_track().get())
        if len(actual) > len(expected):
            break
    assert actual == expected
