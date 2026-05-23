# 4-Panel Expansion — Todo

Forward-looking checklist for chaining four 64×64 HUB75 panels into a single display. The data-driven layout system from the 128×64 build (`layouts.py` + `LAYOUT_NAME`) does most of the heavy lifting — most of what's left is a single new layout entry, content sizing audit, hardware, and smoke testing.

## Already in place (no new work)

The 128×64 expansion landed these capabilities, so the 4-panel build inherits them:

- **`layouts.py` catalogue** — named layouts as dicts containing driver fields (width/height/tile_rows/serpentine) and quadrant rect tuples. Add a new entry; everything downstream (`code.py`, `test_panel.py`) picks it up automatically.
- **`LAYOUT_NAME` selection** — single key in `settings.toml`. Unknown names fall back to the default with a serial warning.
- **Layout-aware `test_panel.py`** — sources dimensions from the same layout dict; corner markers (`TL`/`TR`/`BL`/`BR`) appear at the four physical corners of the chosen layout.
- **`logo.py` auto-size picker** — `logo32.bmp` vs `logo64.bmp` based on the passed width. A 4-panel layout that gives the logo a 128×128 hero would need a third BMP (`logo128.bmp` or similar) and a corresponding branch.
- **`spotify.py` dynamic marquee** — `_marquee_window_for(width)` derives the character window from quadrant width (`width // 5`).
- **`sun.py` dimension stash** — `_state["width"]` / `_state["height"]` are recorded at build time; the rendering doesn't use them yet, but the hook is there.

## Decisions to make first

- [ ] **Pick a physical layout.** Each affects driver config and content density.
  - **2×2 grid → 128×128 px.** Most natural for a dashboard; biggest content area. Likely uses `tile_rows=2` with `serpentine=True` for HUB75 chains where every other row of panels is rotated 180°.
  - **1×4 strip → 256×64 px.** Wide-format ticker / timeline / long clock. `tile_rows=1`.
  - **4×1 column → 64×256 px.** Unusual; useful for stacked vertical content. `tile_rows=1` with custom orientation.

- [ ] **Decide whether the new content layout is "scale up what's there" or "rethink it."**
  - Scale-up: same conceptual widgets, just larger (e.g., a 2×2 layout with four 64×64 widgets). Lowest design effort.
  - Rethink: more widgets, or a single dominant area + sidebars, or split the array into themed zones (info / media / decoration). Higher payoff.

## Software work (much smaller than before)

- [ ] **Add the new entry to `layouts.py`.** Example for a 2×2 = 128×128 grid:
  ```python
  "128x128": {
      "width": 128,
      "height": 128,
      "tile_rows": 2,
      "serpentine": True,
      "quadrants": [
          # one widget per panel-sized cell, or any subdivision the design chooses
          ("logo",     0,   0, 64, 64),
          ("clock",   64,   0, 64, 64),
          ("weather",  0,  64, 64, 64),
          ("sun",     64,  64, 64, 64),    # overlay with spotify
          ("spotify", 64,  64, 64, 64),    # same rect as sun; swapped via set_hidden
      ],
  },
  ```
  Then set `LAYOUT_NAME = "128x128"` in `settings.toml`.

- [ ] **Audit `clock.build` and `weather.build` for hardcoded 32×32 assumptions.**
  These two modules still pin label positions to the 32×32 quadrant size (since both planned layouts only use them at 32×32). If a 4-panel layout sizes them larger, parameterize label `x` / `y` off the passed `width` / `height` — same pattern `spotify.py` and `sun.py` already use to stash dimensions. Either:
  - Keep them 32×32 in the new layout (no module change), or
  - Build them at a larger size and add coordinate math.

- [ ] **Update `logo.py` if the 4-panel layout gives it a slot larger than 64×64.**
  Currently `_default_logo_path(width, height)` returns `logo64.bmp` for any size ≥ 64. For a 128×128 logo slot you'd add a `logo128.bmp` asset and extend `_default_logo_path` with a third branch.

- [ ] **Audit `bit_depth`.** At 4× pixel count the matrix refresh budget is tighter. `BIT_DEPTH = 4` in `code.py` may still work but expect flicker if other work in the loop runs long. Be ready to drop to 3.

## Assets

- [ ] **Larger BDF fonts** under `lib/fonts/` if the new layout uses bigger widgets. The X11 misc-misc set (already the source of the existing 5×8 / 6×10) ships `10x20.bdf`, `7x14.bdf`, etc.

- [ ] **Parameterize `scripts/make_weather_icons.py`.** Currently hardcodes 16×16 output via `SIZE = 16`. Make `SIZE` a CLI argument so regenerating at 32×32 or 48×48 for bigger weather quadrants is one command.

- [ ] **Larger logo BMPs** if the 4-panel layout has a hero slot > 64×64. Add `logo128.bmp` (or whatever size) to `images/arc_raiders_logo/`. `scripts/convert_logo_bmps.py` already normalizes to indexed-palette mode.

## Hardware

- [ ] Source HUB75 ribbon cables for daisy-chaining (panels chain OUT → IN).
- [ ] Source a 5V supply rated for the new draw. Worst case ~4A per panel at full white → budget ~20A total. Mean Well LRS-150-5 (30A) is generous; LRS-100-5 (20A) is tight. Don't reuse the existing two-panel brick.
- [ ] Build a power harness with **per-panel injection** points. Long chains drop voltage; injecting power at each panel keeps colors consistent.
- [ ] Common-ground all 5V feeds and the MatrixPortal's USB ground.
- [ ] Plan physical mounting (frame, magnets, T-slot). Panels have a small bezel gap when butted together — text crossing the seam will look broken.

## Performance / power

- [ ] After first boot at the new size, run for ~10 minutes and check for:
  - Refresh flicker (drop `bit_depth`).
  - Brownout / lockup (power supply undersized or droop across the chain).
  - Excessive heat on the MatrixPortal regulator (sign that something is back-feeding through the HUB75 logic rail — recheck the USB/DC jumper).
- [ ] Re-measure current draw at white-max across all quadrants. The existing software-brightness scaling still works to cap power.

## Testing

- [ ] Existing pytest suite (`tz`, `brightness`, `weather.code_to_icon`, `sun.next_event`, `marquee_window`, `parse_now_playing`, `layouts` structural checks) stays valid — no logic changes there. Run `python3 -m pytest` after each module audit to confirm.
- [ ] Add layout-specific structural assertions to `tests/test_layouts.py` if the new entry has invariants worth pinning (e.g., "spotify renders on top of sun" — already enforced for every layout containing both).
- [ ] On-device smoke checklist:
  1. `./deploy.sh --with-settings` → serial logs `layout: 128x128 (128x128, N quadrants)` (or whatever name).
  2. `./deploy.sh --test` → corner markers land at the four physical corners.
  3. `./deploy.sh` → dashboard runs.
  4. Visual continuity across all panel seams (worst case: a 4-panel array has 4 seams).
  5. Brightness UP/DOWN affects every quadrant uniformly.
  6. Fall back: set `LAYOUT_NAME = "64x64"` or `"128x64"`, redeploy, confirm older layouts still render correctly on whichever panel they fit on.

## Out of scope (defer)

- Touch input or remote control beyond the existing UP/DOWN buttons.
- Animation / scrolling text beyond the existing Spotify marquee (need to confirm baseline refresh holds first at 4× pixel count).
- Power-down / low-brightness "night mode" with a PIR sensor.
- Persisting brightness across reboots (requires NVM storage; was scoped out of v1).
- A `"swap_pairs"` field in layout entries so `_apply_spotify_swap` becomes generic — only worth doing once a second swap pair exists.
