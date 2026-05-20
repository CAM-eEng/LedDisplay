# 4-Panel Expansion — Todo

Forward-looking checklist for chaining four 64×64 HUB75 panels into a single display. Not a design doc yet — open questions captured inline; resolve them before writing a real spec.

## Decisions to make first

- [ ] **Pick a physical layout.** Each affects coordinate math, content density, and the Matrix() init.
  - **2×2 grid → 128×128 px.** Most natural for a dashboard; biggest content area; easiest to redesign quadrants as 64×64 each.
  - **1×4 strip → 256×64 px.** Wide-format ticker / timeline / long clock.
  - **4×1 column → 64×256 px.** Unusual; useful for vertical content.

- [ ] **Decide whether the new content layout is "scale up what's there" or "rethink it."**
  - Scale-up: same four quadrants, just larger (and larger fonts/icons). Lowest design effort.
  - Rethink: more quadrants, or one feature area + sidebars, or a big clock with stats. Higher payoff, more work.

## Hardware

- [ ] Source HUB75 ribbon cables for daisy-chaining (panels chain OUT → IN).
- [ ] Source a 5V supply rated for the new draw. Worst case ~4A per panel at full white → budget ~20A total. Mean Well LRS-150-5 (30A) is generous; LRS-100-5 (20A) is tight. Don't reuse the existing single-panel brick.
- [ ] Build a power harness with **per-panel injection** points. Long chains drop voltage; injecting power at each panel keeps colors consistent across the array.
- [ ] Common-ground all 5V feeds and the MatrixPortal's USB ground.
- [ ] Plan physical mounting (frame, magnets, T-slot). Panels have a small bezel gap when butted together — be aware that text crossing the seam will look broken.

## Driver / Matrix config

- [ ] Update `test_panel.py` first — set new `WIDTH`/`HEIGHT`/`TILE_ROWS`/`SERPENTINE` and confirm all four panels light up in the correct order before touching `code.py`. The corner labels in `test_panel.py` will surface chain/orientation mistakes immediately.
- [ ] Update `code.py`'s `Matrix(...)` init with the new dimensions and tiling parameters. For a 2×2 grid the typical config is `width=128, height=64, tile_rows=2` with `serpentine=True` (rotate every other row of panels 180°) — but verify on hardware; HUB75 chain layouts are finicky.
- [ ] Audit `bit_depth`. At 4× pixel count the matrix refresh budget is tighter; `bit_depth=4` may still work but expect flicker if other work in the loop runs long. Be ready to drop to 3.

## Software changes

- [ ] Make panel dimensions configurable in `settings.toml`:
  ```toml
  PANEL_WIDTH = "128"
  PANEL_HEIGHT = "128"
  TILE_ROWS = "2"
  SERPENTINE = "true"
  ```
  Read them in `code.py` and pass through to `Matrix(...)`.
- [ ] Refactor `code.py`'s quadrant wiring to compute quadrant rectangles from panel dimensions instead of hardcoded `0, 32, 32, 32` literals.
- [ ] Audit `clock.build`, `weather.build`, `sun.build`, `logo.build` — they have hardcoded label offsets that assume a 32×32 quadrant. Parameterize off `width`/`height`.

## Assets

- [ ] Add larger BDF fonts to `lib/fonts/` (e.g., `10x20.bdf`, `7x14.bdf` from the X11 misc-misc set — same source as the existing 5x8 / 6x10).
- [ ] Parameterize `scripts/make_weather_icons.py` to take a `SIZE` argument; regenerate icons at 32×32 or 48×48 indexed-palette BMPs.
- [ ] Switch `logo.py`'s default to `/images/arc_raiders_logo/logo64.bmp` (the 64×64 BMP is already in the repo).

## Performance / power

- [ ] After first boot at the new size, run for ~10 minutes and check for:
  - Refresh flicker (drop `bit_depth`)
  - Brownout / lockup (power supply undersized or droop across the chain)
  - Excessive heat on the MatrixPortal regulator (sign that something is back-feeding through the HUB75 logic rail — recheck the USB/DC jumper).
- [ ] Re-measure current draw at white-max across all quadrants. The existing software-brightness scaling still works to cap power.

## Testing

- [ ] Existing pytest suite (`tz`, `brightness`, `weather.code_to_icon`, `sun.next_event`) stays valid — no zone/icon/picker logic changes. Run `python3 -m pytest` after the refactor to confirm.
- [ ] Re-run the on-device smoke checklist from the original PR (cold boot, Wi-Fi fail, weather fail, brightness buttons, missing logo). Add one new check: visual continuity across panel seams.

## Out of scope (defer)

- Touch input or remote control beyond the existing UP/DOWN buttons.
- Animation / scrolling text (need to confirm baseline refresh holds first).
- Power-down / low-brightness "night mode" with PIR sensor.
- Persisting brightness across reboots (still requires NVM storage and was scoped out of v1).
