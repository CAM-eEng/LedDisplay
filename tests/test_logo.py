from logo import _default_logo_path


def test_returns_32_for_32x32():
    assert _default_logo_path(32, 32) == "/images/arc_raiders_logo/logo32.bmp"


def test_returns_64_for_64x64():
    assert _default_logo_path(64, 64) == "/images/arc_raiders_logo/logo64.bmp"


def test_returns_64_when_either_dim_is_64():
    assert _default_logo_path(64, 32) == "/images/arc_raiders_logo/logo64.bmp"
    assert _default_logo_path(32, 64) == "/images/arc_raiders_logo/logo64.bmp"


def test_returns_64_for_larger_sizes():
    assert _default_logo_path(96, 96) == "/images/arc_raiders_logo/logo64.bmp"


def test_returns_32_for_smaller_sizes():
    assert _default_logo_path(16, 16) == "/images/arc_raiders_logo/logo32.bmp"
