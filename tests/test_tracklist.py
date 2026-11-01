from __future__ import annotations

import random
import warnings
from typing import TYPE_CHECKING

import pytest
from mopidy.models import Playlist, TlTrack, Track
from mopidy.types import PlaybackState

from tests import generate_song

if TYPE_CHECKING:
    from mopidy.core import (
        PlaybackControllerProxy,
        TracklistControllerProxy,
    )

TRACKS = [Track(uri=generate_song(i), length=4464) for i in range(1, 4)]

assert len(TRACKS) == 3, "Need three tracks to run tests."


@pytest.fixture
def tl_tracks(tracklist: TracklistControllerProxy) -> list[TlTrack]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return tracklist.add(TRACKS).get()


def assert_state_is(playback: PlaybackControllerProxy, state: PlaybackState):
    assert playback.get_state().get() == state


def assert_current_track_is(playback: PlaybackControllerProxy, track: Track | None):
    assert playback.get_current_track().get() == track


def test_length(tracklist: TracklistControllerProxy):
    assert len(tracklist.get_tl_tracks().get()) == 0
    assert tracklist.get_length().get() == 0
    tracklist.add(TRACKS)
    assert len(tracklist.get_tl_tracks().get()) == 3
    assert tracklist.get_length().get() == 3


def test_add(tracklist: TracklistControllerProxy):
    for track in TRACKS:
        added = tracklist.add([track]).get()
        tracks = tracklist.get_tracks().get()
        tl_tracks = tracklist.get_tl_tracks().get()

        assert track == tracks[(-1)]
        assert added[0] == tl_tracks[(-1)]
        assert track == added[0].track


def test_add_at_position(tracklist: TracklistControllerProxy):
    for track in TRACKS[:-1]:
        added = tracklist.add(
            tracks=[track],
            at_position=0,
        ).get()
        tracks = tracklist.get_tracks().get()
        tl_tracks = tracklist.get_tl_tracks().get()

        assert track == tracks[0]
        assert added[0] == tl_tracks[0]
        assert track == added[0].track


@pytest.mark.usefixtures("tl_tracks")
def test_add_at_position_outside_of_playlist(tracklist: TracklistControllerProxy):
    for track in TRACKS:
        added = tracklist.add(
            tracks=[track],
            at_position=len(TRACKS) + 2,
        ).get()
        tracks = tracklist.get_tracks().get()
        tl_tracks = tracklist.get_tl_tracks().get()

        assert track == tracks[(-1)]
        assert added[0] == tl_tracks[(-1)]
        assert track == added[0].track


@pytest.mark.usefixtures("tl_tracks")
def test_filter_by_tlid(tracklist: TracklistControllerProxy):
    tl_track = tracklist.get_tl_tracks().get()[1]
    result = tracklist.filter({"tlid": [tl_track.tlid]}).get()
    assert [tl_track] == result


@pytest.mark.usefixtures("tl_tracks")
def test_filter_by_uri(tracklist: TracklistControllerProxy):
    tl_track = tracklist.get_tl_tracks().get()[1]
    result = tracklist.filter({"uri": [tl_track.track.uri]}).get()
    assert [tl_track] == result


@pytest.mark.usefixtures("tl_tracks")
def test_filter_by_uri_returns_nothing_for_invalid_uri(
    tracklist: TracklistControllerProxy,
):
    assert tracklist.filter({"uri": ["foobar"]}).get() == []


def test_filter_by_uri_returns_single_match(tracklist: TracklistControllerProxy):
    t = Track(uri="a")
    tracklist.add([Track(uri="z"), t, Track(uri="y")])

    result = tracklist.filter({"uri": ["a"]}).get()
    assert t == result[0].track


def test_filter_by_uri_returns_multiple_matches(tracklist: TracklistControllerProxy):
    track = Track(uri="a")
    tracklist.add([Track(uri="z"), track, track])
    tl_tracks = tracklist.filter({"uri": ["a"]}).get()
    assert track == tl_tracks[0].track
    assert track == tl_tracks[1].track


def test_filter_by_uri_returns_nothing_if_no_match(tracklist: TracklistControllerProxy):
    tracklist.playlist = Playlist(
        uri="pl",
        tracks=[
            Track(uri="z"),
            Track(uri="y"),
        ],
    )
    assert tracklist.filter({"uri": ["a"]}).get() == []


def test_filter_by_multiple_criteria_returns_elements_matching_all(
    tracklist: TracklistControllerProxy,
):
    t1 = Track(uri="a", name="x")
    t2 = Track(uri="b", name="x")
    t3 = Track(uri="b", name="y")
    tracklist.add([t1, t2, t3])

    result1 = tracklist.filter({"uri": ["a"], "name": ["x"]}).get()
    assert t1 == result1[0].track

    result2 = tracklist.filter({"uri": ["b"], "name": ["x"]}).get()
    assert t2 == result2[0].track

    result3 = tracklist.filter({"uri": ["b"], "name": ["y"]}).get()
    assert t3 == result3[0].track


def test_filter_by_criteria_that_is_not_present_in_all_elements(
    tracklist: TracklistControllerProxy,
):
    track1 = Track(uri="a")
    track2 = Track(uri="b")
    track3 = Track(uri="c")

    tracklist.add([track1, track2, track3])
    result = tracklist.filter({"uri": ["b"]}).get()
    assert track2 == result[0].track


@pytest.mark.usefixtures("tl_tracks")
def test_clear(tracklist: TracklistControllerProxy):
    tracklist.clear().get()
    assert len(tracklist.get_tracks().get()) == 0


def test_clear_empty_playlist(tracklist: TracklistControllerProxy):
    tracklist.clear().get()
    assert len(tracklist.get_tracks().get()) == 0


@pytest.mark.usefixtures("tl_tracks")
def test_clear_when_playing(
    playback: PlaybackControllerProxy, tracklist: TracklistControllerProxy
):
    playback.play().get()
    assert_state_is(playback, PlaybackState.PLAYING)
    tracklist.clear().get()
    assert_state_is(playback, PlaybackState.STOPPED)


def test_add_appends_to_the_tracklist(tracklist: TracklistControllerProxy):
    tracklist.add([Track(uri="a"), Track(uri="b")])

    tracks = tracklist.get_tracks().get()
    assert len(tracks) == 2

    tracklist.add([Track(uri="c"), Track(uri="d")])

    tracks = tracklist.get_tracks().get()
    assert len(tracks) == 4
    assert tracks[0].uri == "a"
    assert tracks[1].uri == "b"
    assert tracks[2].uri == "c"
    assert tracks[3].uri == "d"


def test_add_does_not_reset_version(tracklist: TracklistControllerProxy):
    version = tracklist.get_version().get()
    tracklist.add([])
    assert tracklist.get_version().get() == version


@pytest.mark.usefixtures("tl_tracks")
def test_add_preserves_playing_state(
    playback: PlaybackControllerProxy, tracklist: TracklistControllerProxy
):
    playback.play().get()

    track = playback.get_current_track().get()
    tracks = tracklist.get_tracks().get()
    tracklist.add(tracks[1:2]).get()

    assert_state_is(playback, PlaybackState.PLAYING)
    assert_current_track_is(playback, track)


@pytest.mark.usefixtures("tl_tracks")
def test_add_preserves_stopped_state(
    playback: PlaybackControllerProxy, tracklist: TracklistControllerProxy
):
    tracks = tracklist.get_tracks().get()
    tracklist.add(tracks[1:2]).get()

    assert_state_is(playback, PlaybackState.STOPPED)
    assert_current_track_is(playback, None)


@pytest.mark.usefixtures("tl_tracks")
def test_add_returns_the_tl_tracks_that_was_added(tracklist: TracklistControllerProxy):
    tracks = tracklist.get_tracks().get()

    added = tracklist.add(tracks[1:2]).get()
    tracks = tracklist.get_tracks().get()
    assert added[0].track == tracks[1]


@pytest.mark.usefixtures("tl_tracks")
def test_move_single(tracklist: TracklistControllerProxy):
    tracklist.move(0, 0, 2)

    tracks = tracklist.get_tracks().get()
    assert tracks[2] == TRACKS[0]


@pytest.mark.usefixtures("tl_tracks")
def test_move_group(tracklist: TracklistControllerProxy):
    tracklist.move(0, 2, 1)

    tracks = tracklist.get_tracks().get()
    assert tracks[1] == TRACKS[0]
    assert tracks[2] == TRACKS[1]


@pytest.mark.usefixtures("tl_tracks")
def test_moving_track_outside_of_playlist(tracklist: TracklistControllerProxy):
    num_tracks = len(tracklist.get_tracks().get())
    with pytest.raises(AssertionError):
        tracklist.move(0, 0, num_tracks + 5).get()


@pytest.mark.usefixtures("tl_tracks")
def test_move_group_outside_of_playlist(tracklist: TracklistControllerProxy):
    num_tracks = len(tracklist.get_tracks().get())
    with pytest.raises(AssertionError):
        tracklist.move(0, 2, num_tracks + 5).get()


@pytest.mark.usefixtures("tl_tracks")
def test_move_group_out_of_range(tracklist: TracklistControllerProxy):
    num_tracks = len(tracklist.get_tracks().get())
    with pytest.raises(AssertionError):
        tracklist.move(num_tracks + 2, num_tracks + 3, 0).get()


@pytest.mark.usefixtures("tl_tracks")
def test_move_group_invalid_group(tracklist: TracklistControllerProxy):
    with pytest.raises(AssertionError):
        tracklist.move(2, 1, 0).get()


def test_tracks_attribute_is_immutable(tracklist: TracklistControllerProxy):
    tracks1 = tracklist.get_tracks().get()
    tracks2 = tracklist.get_tracks().get()
    assert id(tracks1) != id(tracks2)


@pytest.mark.usefixtures("tl_tracks")
def test_remove(tracklist: TracklistControllerProxy):
    track1 = tracklist.get_tracks().get()[1]
    track2 = tracklist.get_tracks().get()[2]
    version = tracklist.get_version().get()
    tracklist.remove({"uri": [track1.uri]})
    assert version < tracklist.get_version().get()
    assert track1 not in tracklist.get_tracks().get()
    assert track2 == tracklist.get_tracks().get()[1]


@pytest.mark.usefixtures("tl_tracks")
def test_removing_track_that_does_not_exist_does_nothing(
    tracklist: TracklistControllerProxy,
):
    tracklist.remove({"uri": ["/nonexistant"]}).get()


def test_removing_from_empty_playlist_does_nothing(tracklist: TracklistControllerProxy):
    tracklist.remove({"uri": ["/nonexistant"]}).get()


@pytest.mark.usefixtures("tl_tracks")
def test_remove_lists(tracklist: TracklistControllerProxy):
    version = tracklist.get_version().get()
    tracks = tracklist.get_tracks().get()
    track0 = tracks[0]
    track1 = tracks[1]
    track2 = tracks[2]

    tracklist.remove({"uri": [track0.uri, track2.uri]})

    tracks = tracklist.get_tracks().get()
    assert version < tracklist.get_version().get()
    assert track0 not in tracks
    assert track2 not in tracks
    assert track1 == tracks[0]


@pytest.mark.usefixtures("tl_tracks")
def test_shuffle(tracklist: TracklistControllerProxy):
    random.seed(1)
    tracklist.shuffle()

    shuffled_tracks = tracklist.get_tracks().get()

    assert shuffled_tracks != TRACKS
    assert set(TRACKS) == set(shuffled_tracks)


@pytest.mark.usefixtures("tl_tracks")
def test_shuffle_subset(tracklist: TracklistControllerProxy):
    random.seed(1)
    tracklist.shuffle(1, 3)

    shuffled_tracks = tracklist.get_tracks().get()

    assert shuffled_tracks != TRACKS
    assert TRACKS[0] == shuffled_tracks[0]
    assert set(TRACKS) == set(shuffled_tracks)


@pytest.mark.usefixtures("tl_tracks")
def test_shuffle_invalid_subset(tracklist: TracklistControllerProxy):
    with pytest.raises(AssertionError):
        tracklist.shuffle(3, 1).get()


@pytest.mark.usefixtures("tl_tracks")
def test_shuffle_superset(tracklist: TracklistControllerProxy):
    num_tracks = len(tracklist.get_tracks().get())
    with pytest.raises(AssertionError):
        tracklist.shuffle(1, num_tracks + 5).get()


@pytest.mark.usefixtures("tl_tracks")
def test_shuffle_open_subset(tracklist: TracklistControllerProxy):
    random.seed(1)
    tracklist.shuffle(1)

    shuffled_tracks = tracklist.get_tracks().get()

    assert shuffled_tracks != TRACKS
    assert TRACKS[0] == shuffled_tracks[0]
    assert set(TRACKS) == set(shuffled_tracks)


@pytest.mark.usefixtures("tl_tracks")
def test_slice_returns_a_subset_of_tracks(tracklist: TracklistControllerProxy):
    track_slice = tracklist.slice(1, 3).get()
    assert len(track_slice) == 2
    assert TRACKS[1] == track_slice[0].track
    assert TRACKS[2] == track_slice[1].track


@pytest.mark.usefixtures("tl_tracks")
def test_slice_returns_empty_list_if_indexes_outside_tracks_list(
    tracklist: TracklistControllerProxy,
):
    assert len(tracklist.slice(7, 8).get()) == 0
    assert len(tracklist.slice((-1), 1).get()) == 0


def test_version_does_not_change_when_adding_nothing(
    tracklist: TracklistControllerProxy,
):
    version = tracklist.get_version().get()
    tracklist.add([])
    assert version == tracklist.get_version().get()


def test_version_increases_when_adding_something(tracklist: TracklistControllerProxy):
    version = tracklist.get_version().get()
    tracklist.add([Track(uri="a")])
    assert version < tracklist.get_version().get()
