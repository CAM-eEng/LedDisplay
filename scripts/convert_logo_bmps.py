"""Convert RGB BMPs under images/arc_raiders_logo/ to indexed-palette mode.

displayio's adafruit_imageload returns a ColorConverter (not a Palette) for
direct-color BMPs, which prevents the dashboard from enumerating colors for
brightness dimming. Indexed-palette BMPs return a real Palette object.

Run on the host:  python3 scripts/convert_logo_bmps.py
"""
import glob
import os
from PIL import Image

LOGO_DIR = os.path.join(os.path.dirname(__file__), "..", "images", "arc_raiders_logo")


def main():
    paths = sorted(glob.glob(os.path.join(LOGO_DIR, "*.bmp")))
    if not paths:
        print("no BMPs found under", LOGO_DIR)
        return
    for path in paths:
        img = Image.open(path)
        if img.mode == "P":
            print("skip", path, "(already indexed)")
            continue
        indexed = img.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=256)
        indexed.save(path, "BMP")
        print("converted", path, "->", indexed.mode)


if __name__ == "__main__":
    main()
