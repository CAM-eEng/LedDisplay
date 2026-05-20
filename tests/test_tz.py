import tz


def test_weekday_returns_monday_for_known_monday():
    # 2024-01-01 was a Monday
    assert tz._weekday(2024, 1, 1) == 0


def test_weekday_returns_sunday_for_known_sunday():
    # 2024-03-10 was a Sunday (2nd Sunday of March 2024)
    assert tz._weekday(2024, 3, 10) == 6


def test_weekday_returns_friday_for_first_of_march_2024():
    # 2024-03-01 was a Friday
    assert tz._weekday(2024, 3, 1) == 4


def test_weekday_handles_january_correctly():
    # Zeller treats Jan/Feb as months 13/14 of previous year; verify the wrap.
    # 2025-01-01 was a Wednesday
    assert tz._weekday(2025, 1, 1) == 2


def test_weekday_handles_century_boundary():
    # 2000-01-01 was a Saturday
    assert tz._weekday(2000, 1, 1) == 5
