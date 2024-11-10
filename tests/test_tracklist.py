import random
import unittest

import pykka
from mopidy import core
from mopidy.core import PlaybackState
from mopidy.models import Playlist, Track

from mopidy_local import actor
from tests import (
    dummy_audio,
    generate_song,
    path_to_data_dir,
    populate_tracklist,
)


class LocalTracklistProviderTest(unittest.TestCase):
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
    tracks = [Track(uri=generate_song(i), length=4464) for i in range(1, 4)]

    def setUp(self):
        self.audio = dummy_audio.create_proxy()
        self.backend = actor.LocalBackend.start(
            config=self.config,
            audio=self.audio,
        ).proxy()
        self.core = core.Core.start(
            audio=self.audio,
            backends=[self.backend],
            config=self.config,
        ).proxy()
        self.controller = self.core.tracklist
        self.playback = self.core.playback

        assert len(self.tracks) == 3, "Need three tracks to run tests."

    def tearDown(self):
        pykka.ActorRegistry.stop_all()

    def assert_state_is(self, state):
        assert self.playback.get_state().get() == state

    def assert_current_track_is(self, track):
        assert self.playback.get_current_track().get() == track

    def test_length(self):
        assert len(self.controller.get_tl_tracks().get()) == 0
        assert self.controller.get_length().get() == 0
        self.controller.add(self.tracks)
        assert len(self.controller.get_tl_tracks().get()) == 3
        assert self.controller.get_length().get() == 3

    def test_add(self):
        for track in self.tracks:
            added = self.controller.add([track]).get()
            tracks = self.controller.get_tracks().get()
            tl_tracks = self.controller.get_tl_tracks().get()

            assert track == tracks[(-1)]
            assert added[0] == tl_tracks[(-1)]
            assert track == added[0].track

    def test_add_at_position(self):
        for track in self.tracks[:-1]:
            added = self.controller.add([track], 0).get()
            tracks = self.controller.get_tracks().get()
            tl_tracks = self.controller.get_tl_tracks().get()

            assert track == tracks[0]
            assert added[0] == tl_tracks[0]
            assert track == added[0].track

    @populate_tracklist
    def test_add_at_position_outside_of_playlist(self):
        for track in self.tracks:
            added = self.controller.add([track], len(self.tracks) + 2).get()
            tracks = self.controller.get_tracks().get()
            tl_tracks = self.controller.get_tl_tracks().get()

            assert track == tracks[(-1)]
            assert added[0] == tl_tracks[(-1)]
            assert track == added[0].track

    @populate_tracklist
    def test_filter_by_tlid(self):
        tl_track = self.controller.get_tl_tracks().get()[1]
        result = self.controller.filter({"tlid": [tl_track.tlid]}).get()
        assert [tl_track] == result

    @populate_tracklist
    def test_filter_by_uri(self):
        tl_track = self.controller.get_tl_tracks().get()[1]
        result = self.controller.filter({"uri": [tl_track.track.uri]}).get()
        assert [tl_track] == result

    @populate_tracklist
    def test_filter_by_uri_returns_nothing_for_invalid_uri(self):
        assert self.controller.filter({"uri": ["foobar"]}).get() == []

    def test_filter_by_uri_returns_single_match(self):
        t = Track(uri="a")
        self.controller.add([Track(uri="z"), t, Track(uri="y")])

        result = self.controller.filter({"uri": ["a"]}).get()
        assert t == result[0].track

    def test_filter_by_uri_returns_multiple_matches(self):
        track = Track(uri="a")
        self.controller.add([Track(uri="z"), track, track])
        tl_tracks = self.controller.filter({"uri": ["a"]}).get()
        assert track == tl_tracks[0].track
        assert track == tl_tracks[1].track

    def test_filter_by_uri_returns_nothing_if_no_match(self):
        self.controller.playlist = Playlist(tracks=[Track(uri="z"), Track(uri="y")])
        assert self.controller.filter({"uri": ["a"]}).get() == []

    def test_filter_by_multiple_criteria_returns_elements_matching_all(self):
        t1 = Track(uri="a", name="x")
        t2 = Track(uri="b", name="x")
        t3 = Track(uri="b", name="y")
        self.controller.add([t1, t2, t3])

        result1 = self.controller.filter({"uri": ["a"], "name": ["x"]}).get()
        assert t1 == result1[0].track

        result2 = self.controller.filter({"uri": ["b"], "name": ["x"]}).get()
        assert t2 == result2[0].track

        result3 = self.controller.filter({"uri": ["b"], "name": ["y"]}).get()
        assert t3 == result3[0].track

    def test_filter_by_criteria_that_is_not_present_in_all_elements(self):
        track1 = Track()
        track2 = Track(uri="b")
        track3 = Track()

        self.controller.add([track1, track2, track3])
        result = self.controller.filter({"uri": ["b"]}).get()
        assert track2 == result[0].track

    @populate_tracklist
    def test_clear(self):
        self.controller.clear().get()
        assert len(self.controller.get_tracks().get()) == 0

    def test_clear_empty_playlist(self):
        self.controller.clear().get()
        assert len(self.controller.get_tracks().get()) == 0

    @populate_tracklist
    def test_clear_when_playing(self):
        self.playback.play().get()
        self.assert_state_is(PlaybackState.PLAYING)
        self.controller.clear().get()
        self.assert_state_is(PlaybackState.STOPPED)

    def test_add_appends_to_the_tracklist(self):
        self.controller.add([Track(uri="a"), Track(uri="b")])

        tracks = self.controller.get_tracks().get()
        assert len(tracks) == 2

        self.controller.add([Track(uri="c"), Track(uri="d")])

        tracks = self.controller.get_tracks().get()
        assert len(tracks) == 4
        assert tracks[0].uri == "a"
        assert tracks[1].uri == "b"
        assert tracks[2].uri == "c"
        assert tracks[3].uri == "d"

    def test_add_does_not_reset_version(self):
        version = self.controller.get_version().get()
        self.controller.add([])
        assert self.controller.get_version().get() == version

    @populate_tracklist
    def test_add_preserves_playing_state(self):
        self.playback.play().get()

        track = self.playback.get_current_track().get()
        tracks = self.controller.get_tracks().get()
        self.controller.add(tracks[1:2]).get()

        self.assert_state_is(PlaybackState.PLAYING)
        self.assert_current_track_is(track)

    @populate_tracklist
    def test_add_preserves_stopped_state(self):
        tracks = self.controller.get_tracks().get()
        self.controller.add(tracks[1:2]).get()

        self.assert_state_is(PlaybackState.STOPPED)
        self.assert_current_track_is(None)

    @populate_tracklist
    def test_add_returns_the_tl_tracks_that_was_added(self):
        tracks = self.controller.get_tracks().get()

        added = self.controller.add(tracks[1:2]).get()
        tracks = self.controller.get_tracks().get()
        assert added[0].track == tracks[1]

    @populate_tracklist
    def test_move_single(self):
        self.controller.move(0, 0, 2)

        tracks = self.controller.get_tracks().get()
        assert tracks[2] == self.tracks[0]

    @populate_tracklist
    def test_move_group(self):
        self.controller.move(0, 2, 1)

        tracks = self.controller.get_tracks().get()
        assert tracks[1] == self.tracks[0]
        assert tracks[2] == self.tracks[1]

    @populate_tracklist
    def test_moving_track_outside_of_playlist(self):
        num_tracks = len(self.controller.get_tracks().get())
        with self.assertRaises(AssertionError):
            self.controller.move(0, 0, num_tracks + 5).get()

    @populate_tracklist
    def test_move_group_outside_of_playlist(self):
        num_tracks = len(self.controller.get_tracks().get())
        with self.assertRaises(AssertionError):
            self.controller.move(0, 2, num_tracks + 5).get()

    @populate_tracklist
    def test_move_group_out_of_range(self):
        num_tracks = len(self.controller.get_tracks().get())
        with self.assertRaises(AssertionError):
            self.controller.move(num_tracks + 2, num_tracks + 3, 0).get()

    @populate_tracklist
    def test_move_group_invalid_group(self):
        with self.assertRaises(AssertionError):
            self.controller.move(2, 1, 0).get()

    def test_tracks_attribute_is_immutable(self):
        tracks1 = self.controller.get_tracks().get()
        tracks2 = self.controller.get_tracks().get()
        assert id(tracks1) != id(tracks2)

    @populate_tracklist
    def test_remove(self):
        track1 = self.controller.get_tracks().get()[1]
        track2 = self.controller.get_tracks().get()[2]
        version = self.controller.get_version().get()
        self.controller.remove({"uri": [track1.uri]})
        assert version < self.controller.get_version().get()
        assert track1 not in self.controller.get_tracks().get()
        assert track2 == self.controller.get_tracks().get()[1]

    @populate_tracklist
    def test_removing_track_that_does_not_exist_does_nothing(self):
        self.controller.remove({"uri": ["/nonexistant"]}).get()

    def test_removing_from_empty_playlist_does_nothing(self):
        self.controller.remove({"uri": ["/nonexistant"]}).get()

    @populate_tracklist
    def test_remove_lists(self):
        version = self.controller.get_version().get()
        tracks = self.controller.get_tracks().get()
        track0 = tracks[0]
        track1 = tracks[1]
        track2 = tracks[2]

        self.controller.remove({"uri": [track0.uri, track2.uri]})

        tracks = self.controller.get_tracks().get()
        assert version < self.controller.get_version().get()
        assert track0 not in tracks
        assert track2 not in tracks
        assert track1 == tracks[0]

    @populate_tracklist
    def test_shuffle(self):
        random.seed(1)
        self.controller.shuffle()

        shuffled_tracks = self.controller.get_tracks().get()

        assert self.tracks != shuffled_tracks
        assert set(self.tracks) == set(shuffled_tracks)

    @populate_tracklist
    def test_shuffle_subset(self):
        random.seed(1)
        self.controller.shuffle(1, 3)

        shuffled_tracks = self.controller.get_tracks().get()

        assert self.tracks != shuffled_tracks
        assert self.tracks[0] == shuffled_tracks[0]
        assert set(self.tracks) == set(shuffled_tracks)

    @populate_tracklist
    def test_shuffle_invalid_subset(self):
        with self.assertRaises(AssertionError):
            self.controller.shuffle(3, 1).get()

    @populate_tracklist
    def test_shuffle_superset(self):
        num_tracks = len(self.controller.get_tracks().get())
        with self.assertRaises(AssertionError):
            self.controller.shuffle(1, num_tracks + 5).get()

    @populate_tracklist
    def test_shuffle_open_subset(self):
        random.seed(1)
        self.controller.shuffle(1)

        shuffled_tracks = self.controller.get_tracks().get()

        assert self.tracks != shuffled_tracks
        assert self.tracks[0] == shuffled_tracks[0]
        assert set(self.tracks) == set(shuffled_tracks)

    @populate_tracklist
    def test_slice_returns_a_subset_of_tracks(self):
        track_slice = self.controller.slice(1, 3).get()
        assert len(track_slice) == 2
        assert self.tracks[1] == track_slice[0].track
        assert self.tracks[2] == track_slice[1].track

    @populate_tracklist
    def test_slice_returns_empty_list_if_indexes_outside_tracks_list(self):
        assert len(self.controller.slice(7, 8).get()) == 0
        assert len(self.controller.slice((-1), 1).get()) == 0

    def test_version_does_not_change_when_adding_nothing(self):
        version = self.controller.get_version().get()
        self.controller.add([])
        assert version == self.controller.get_version().get()

    def test_version_increases_when_adding_something(self):
        version = self.controller.get_version().get()
        self.controller.add([Track()])
        assert version < self.controller.get_version().get()
