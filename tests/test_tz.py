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


import time


def _utc(year, month, day, hour=12, minute=0):
    """Build a struct_time with tm_year, tm_mon, tm_mday, tm_hour, tm_min set."""
    return time.struct_time((year, month, day, hour, minute, 0, 0, 0, 0))


def test_is_dst_returns_false_in_january():
    assert tz.is_dst(_utc(2026, 1, 15), "America/Los_Angeles") is False


def test_is_dst_returns_true_in_july():
    assert tz.is_dst(_utc(2026, 7, 4), "America/Los_Angeles") is True


def test_is_dst_just_before_spring_forward_boundary():
    # 2026 spring forward: 2nd Sun March = March 8; switch at 02:00 PST = 10:00 UTC
    # 09:59 UTC is still standard time.
    assert tz.is_dst(_utc(2026, 3, 8, 9, 59), "America/Los_Angeles") is False


def test_is_dst_at_spring_forward_boundary():
    # 10:00 UTC on March 8, 2026 = 02:00 PST = first moment of PDT
    assert tz.is_dst(_utc(2026, 3, 8, 10, 0), "America/Los_Angeles") is True


def test_is_dst_just_before_fall_back_boundary():
    # 2026 fall back: 1st Sun November = November 1; switch at 02:00 PDT = 09:00 UTC
    # 08:59 UTC is still daylight time.
    assert tz.is_dst(_utc(2026, 11, 1, 8, 59), "America/Los_Angeles") is True


def test_is_dst_at_fall_back_boundary():
    # 09:00 UTC on November 1, 2026 = 02:00 PDT = first moment of PST
    assert tz.is_dst(_utc(2026, 11, 1, 9, 0), "America/Los_Angeles") is False


def test_is_dst_unknown_zone_returns_false():
    assert tz.is_dst(_utc(2026, 7, 4), "Europe/Berlin") is False


def test_is_dst_eastern_time_boundary_differs_from_pacific():
    # March 8, 2026, 07:00 UTC = 02:00 EST → start of EDT
    # Same instant in Pacific = 23:00 UTC March 7 = still PST
    assert tz.is_dst(_utc(2026, 3, 8, 7, 0), "America/New_York") is True
    assert tz.is_dst(_utc(2026, 3, 8, 7, 0), "America/Los_Angeles") is False
