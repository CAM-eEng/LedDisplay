import layouts


def test_layouts_dict_exists_and_is_a_dict():
    assert isinstance(layouts.LAYOUTS, dict)
    assert len(layouts.LAYOUTS) >= 2


def test_default_layout_is_a_key():
    assert layouts.DEFAULT_LAYOUT in layouts.LAYOUTS


def test_default_layout_is_64x64():
    assert layouts.DEFAULT_LAYOUT == "64x64"


def test_each_layout_has_required_keys():
    required = {"width", "height", "tile_rows", "serpentine", "quadrants"}
    for name, layout in layouts.LAYOUTS.items():
        missing = required - set(layout.keys())
        assert not missing, "{} missing keys: {}".format(name, missing)


def test_each_quadrant_rect_fits_within_layout_dimensions():
    for name, layout in layouts.LAYOUTS.items():
        w, h = layout["width"], layout["height"]
        for q in layout["quadrants"]:
            mod, x, y, qw, qh = q
            assert x >= 0 and y >= 0, "{}: negative origin {}".format(name, q)
            assert x + qw <= w, "{}: {} runs past width {}".format(name, q, w)
            assert y + qh <= h, "{}: {} runs past height {}".format(name, q, h)


def test_each_quadrant_tuple_has_five_elements():
    for name, layout in layouts.LAYOUTS.items():
        for q in layout["quadrants"]:
            assert len(q) == 5, "{}: bad quadrant tuple {}".format(name, q)


def test_128x64_layout_contains_expected_modules():
    quads = layouts.LAYOUTS["128x64"]["quadrants"]
    names = [q[0] for q in quads]
    assert set(names) == {"logo", "clock", "weather", "sun", "spotify"}


def test_128x64_logo_is_64x64_hero_at_origin():
    quads = layouts.LAYOUTS["128x64"]["quadrants"]
    logo = next(q for q in quads if q[0] == "logo")
    assert logo == ("logo", 0, 0, 64, 64)


def test_64x64_layout_matches_today_behavior():
    layout = layouts.LAYOUTS["64x64"]
    assert layout["width"] == 64 and layout["height"] == 64
    assert layout["tile_rows"] == 1
    assert layout["serpentine"] is False
    names = [q[0] for q in layout["quadrants"]]
    assert set(names) == {"clock", "weather", "sun", "logo", "spotify"}


def test_spotify_renders_on_top_of_sun_in_every_layout_that_has_both():
    for name, layout in layouts.LAYOUTS.items():
        names = [q[0] for q in layout["quadrants"]]
        if "sun" in names and "spotify" in names:
            assert names.index("sun") < names.index("spotify"), (
                "{}: spotify must appear after sun for correct z-order".format(name)
            )
