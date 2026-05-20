from sun import next_event


# All times in this module are "minutes since start of day local".
SUNRISE = 6 * 60 + 30        # 06:30
SUNSET = 20 * 60 + 45        # 20:45


def test_before_sunrise_picks_sunrise():
    assert next_event(SUNRISE, SUNSET, now_minutes=5 * 60) == ("sunrise", SUNRISE)


def test_at_sunrise_picks_sunset():
    # Exactly at sunrise, the next event is sunset.
    assert next_event(SUNRISE, SUNSET, now_minutes=SUNRISE) == ("sunset", SUNSET)


def test_midday_picks_sunset():
    assert next_event(SUNRISE, SUNSET, now_minutes=12 * 60) == ("sunset", SUNSET)


def test_after_sunset_picks_tomorrow_sunrise():
    # After sunset, the next event is tomorrow's sunrise.
    label, when = next_event(SUNRISE, SUNSET, now_minutes=22 * 60)
    assert label == "sunrise"
    assert when == SUNRISE


def test_just_before_sunset():
    assert next_event(SUNRISE, SUNSET, now_minutes=SUNSET - 1) == ("sunset", SUNSET)
