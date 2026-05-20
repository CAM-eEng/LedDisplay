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


def test_second_sunday_of_march_2024():
    # 2nd Sunday of March 2024 = March 10
    assert tz._nth_sunday_of_month(2024, 3, 2) == 10


def test_first_sunday_of_november_2024():
    # 1st Sunday of November 2024 = November 3
    assert tz._nth_sunday_of_month(2024, 11, 1) == 3


def test_second_sunday_of_march_2026():
    # 2nd Sunday of March 2026 = March 8
    assert tz._nth_sunday_of_month(2026, 3, 2) == 8


def test_first_sunday_of_november_2026():
    # 1st Sunday of November 2026 = November 1
    assert tz._nth_sunday_of_month(2026, 11, 1) == 1


def test_first_sunday_when_month_starts_on_sunday():
    # November 2026 starts on a Sunday — the 1st Sunday is the 1st.
    assert tz._nth_sunday_of_month(2026, 11, 1) == 1
