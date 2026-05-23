from spotify import marquee_window, parse_now_playing


def test_empty_string_returns_empty():
    assert marquee_window("", 0) == ""


def test_string_shorter_than_window_returns_as_is():
    assert marquee_window("Hey", 0) == "Hey"
    assert marquee_window("Hey", 42) == "Hey"


def test_string_exactly_window_returns_as_is():
    assert marquee_window("123456", 0) == "123456"


def test_offset_zero_returns_first_window_chars_padded():
    # "Bohemian Rhapsody" + "   " = 20 chars total; first 6 at offset 0
    assert marquee_window("Bohemian Rhapsody", 0) == "Bohemi"


def test_offset_one_advances_by_one_char():
    assert marquee_window("Bohemian Rhapsody", 1) == "ohemia"


def test_window_wraps_at_end_of_padded_text():
    # Padded text length = 17 + 3 = 20. At offset 18, we read positions
    # 18, 19 (end of gap), then wrap to 0, 1, 2, 3 — "  Bohe"
    assert marquee_window("Bohemian Rhapsody", 18) == "  Bohe"


def test_large_offset_wraps_modulo_padded_length():
    # offset 38 = 38 % 20 = 18 -> same window as offset 18
    assert marquee_window("Bohemian Rhapsody", 38) == "  Bohe"


def test_custom_window_size():
    assert marquee_window("Bohemian Rhapsody", 0, window=4) == "Bohe"


def test_custom_gap():
    # Gap is "*" — padded = "ABCDE*" length 6; offset 0 returns first 4 chars
    # of padded: "ABCD". At offset 2: "CDE*". At offset 4: "E*AB" (wraps).
    assert marquee_window("ABCDE", 0, window=4, gap="*") == "ABCD"
    assert marquee_window("ABCDE", 2, window=4, gap="*") == "CDE*"
    assert marquee_window("ABCDE", 4, window=4, gap="*") == "E*AB"


def test_short_string_with_short_gap_still_does_not_scroll():
    # Regression guard: "U2" + default gap "   " = 5 chars, less than window=6.
    # Despite padded being shorter than window, len(text) <= window so we don't scroll.
    assert marquee_window("U2", 0) == "U2"
    assert marquee_window("U2", 42) == "U2"
    assert marquee_window("OK", 0) == "OK"


def _track_payload(name="Bohemian Rhapsody", artists=("Queen",), is_playing=True):
    return {
        "is_playing": is_playing,
        "currently_playing_type": "track",
        "item": {
            "name": name,
            "artists": [{"name": a} for a in artists],
        },
    }


def _episode_payload(name="Hard Fork", show="The New York Times", is_playing=True):
    return {
        "is_playing": is_playing,
        "currently_playing_type": "episode",
        "item": {
            "name": name,
            "show": {"name": show},
        },
    }


def test_parse_returns_none_for_empty_payload():
    assert parse_now_playing({}) is None


def test_parse_returns_none_for_none_payload():
    assert parse_now_playing(None) is None


def test_parse_returns_none_when_item_missing():
    assert parse_now_playing({"is_playing": True}) is None


def test_parse_track_returns_track_artist_is_playing():
    data = parse_now_playing(_track_payload())
    assert data == {
        "track": "Bohemian Rhapsody",
        "artist": "Queen",
        "is_playing": True,
    }


def test_parse_paused_track_preserves_is_playing_false():
    data = parse_now_playing(_track_payload(is_playing=False))
    assert data["is_playing"] is False


def test_parse_multi_artist_joins_with_comma_space():
    data = parse_now_playing(_track_payload(artists=("Daft Punk", "Pharrell Williams")))
    assert data["artist"] == "Daft Punk, Pharrell Williams"


def test_parse_episode_uses_show_name_as_artist():
    data = parse_now_playing(_episode_payload())
    assert data == {
        "track": "Hard Fork",
        "artist": "The New York Times",
        "is_playing": True,
    }


def test_parse_ad_returns_none():
    payload = {
        "is_playing": True,
        "currently_playing_type": "ad",
        "item": None,
    }
    assert parse_now_playing(payload) is None


def test_parse_unknown_type_returns_none():
    payload = {
        "is_playing": True,
        "currently_playing_type": "unknown_thing",
        "item": {"name": "x", "artists": [{"name": "y"}]},
    }
    assert parse_now_playing(payload) is None


def test_parse_track_with_missing_name_returns_none():
    payload = {
        "is_playing": True,
        "currently_playing_type": "track",
        "item": {"artists": [{"name": "Queen"}]},
    }
    assert parse_now_playing(payload) is None


def test_parse_track_with_no_artists_returns_none():
    payload = {
        "is_playing": True,
        "currently_playing_type": "track",
        "item": {"name": "x", "artists": []},
    }
    assert parse_now_playing(payload) is None


def test_parse_episode_with_missing_show_returns_none():
    payload = {
        "is_playing": True,
        "currently_playing_type": "episode",
        "item": {"name": "x"},
    }
    assert parse_now_playing(payload) is None


from spotify import _marquee_window_for


def test_marquee_window_for_32px_returns_6():
    assert _marquee_window_for(32) == 6


def test_marquee_window_for_64px_returns_12():
    assert _marquee_window_for(64) == 12


def test_marquee_window_for_very_small_widths_returns_at_least_1():
    assert _marquee_window_for(4) == 1
    assert _marquee_window_for(0) == 1


def test_marquee_window_for_128px_returns_25():
    # 128 // 5 = 25
    assert _marquee_window_for(128) == 25
