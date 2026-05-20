from brightness import scale


def test_scale_full_brightness_returns_unchanged():
    assert scale(0xFFAA00, 1.0) == 0xFFAA00


def test_scale_zero_brightness_returns_black():
    assert scale(0xFFAA00, 0.0) == 0x000000


def test_scale_half_brightness_halves_each_channel():
    # 0xFFAA00 = (255, 170, 0); 0.5 = (127, 85, 0)
    assert scale(0xFFAA00, 0.5) == 0x7F5500


def test_scale_clamps_high_bound():
    # Defensive: caller passing > 1.0 should not overflow into other channels.
    result = scale(0xFFFFFF, 1.5)
    assert result == 0xFFFFFF


def test_scale_clamps_low_bound():
    assert scale(0xFFFFFF, -0.5) == 0x000000


def test_scale_pure_blue():
    assert scale(0x0000FF, 0.5) == 0x00007F
