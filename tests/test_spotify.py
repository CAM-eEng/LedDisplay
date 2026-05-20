from spotify import marquee_window


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
    # Gap is "*" — padded = "AB*" length 3; offset 0 returns first 4 chars
    # wrapping: "AB*A"
    assert marquee_window("AB", 0, window=4, gap="*") == "AB*A"
