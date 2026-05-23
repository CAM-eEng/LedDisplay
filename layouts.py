"""Named display layouts. Each entry describes a panel chain and the
quadrant rectangles within it. Add new entries here when adding new
panel configurations; no other code changes required for content
modules that already support the requested sizes.

Quadrant rect tuples: (module_name, x, y, width, height).
Append order = displayio z-order (later = drawn on top).
"""


LAYOUTS = {
    "64x64": {
        "width": 64,
        "height": 64,
        "tile_rows": 1,
        "serpentine": False,
        "quadrants": [
            ("clock",    0,  0, 32, 32),
            ("weather", 32,  0, 32, 32),
            ("sun",      0, 32, 32, 32),
            ("logo",    32, 32, 32, 32),
            ("spotify",  0, 32, 32, 32),  # same rect as sun; swapped via set_hidden
        ],
    },
    "128x64": {
        "width": 128,
        "height": 64,
        "tile_rows": 1,
        "serpentine": False,
        "quadrants": [
            ("logo",     0,  0, 64, 64),
            ("clock",   64,  0, 32, 32),
            ("weather", 96,  0, 32, 32),
            ("sun",     64, 32, 64, 32),
            ("spotify", 64, 32, 64, 32),  # same rect as sun; swapped via set_hidden
        ],
    },
}

DEFAULT_LAYOUT = "64x64"
