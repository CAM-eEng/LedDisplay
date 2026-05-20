"""Generate six 16x16 BMP weather icons under images/weather/.

Run on the host (not on the device):
    python scripts/make_weather_icons.py

Requires Pillow:  pip install Pillow
"""
import os
from PIL import Image, ImageDraw

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "images", "weather")
SIZE = 16


def _new():
    return Image.new("RGB", (SIZE, SIZE), (0, 0, 0))


def sun_icon():
    img = _new()
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 11, 11], fill=(255, 200, 0))
    for dx, dy in [(0, 8), (8, 0), (15, 8), (8, 15), (2, 2), (13, 2), (2, 13), (13, 13)]:
        d.point((dx, dy), fill=(255, 200, 0))
    return img


def cloud_icon():
    img = _new()
    d = ImageDraw.Draw(img)
    d.ellipse([2, 6, 9, 12], fill=(200, 200, 200))
    d.ellipse([6, 3, 13, 10], fill=(220, 220, 220))
    d.rectangle([3, 9, 13, 12], fill=(210, 210, 210))
    return img


def rain_icon():
    img = cloud_icon()
    d = ImageDraw.Draw(img)
    for x in (4, 8, 12):
        d.line([(x, 13), (x - 1, 15)], fill=(80, 160, 255))
    return img


def snow_icon():
    img = cloud_icon()
    d = ImageDraw.Draw(img)
    for x in (4, 8, 12):
        d.point((x, 13), fill=(255, 255, 255))
        d.point((x, 15), fill=(255, 255, 255))
    return img


def fog_icon():
    img = _new()
    d = ImageDraw.Draw(img)
    for y in (4, 7, 10, 13):
        d.line([(1, y), (14, y)], fill=(180, 180, 200))
    return img


def unknown_icon():
    img = _new()
    d = ImageDraw.Draw(img)
    d.text((5, 3), "?", fill=(255, 255, 255))
    return img


GENERATORS = {
    "sun": sun_icon,
    "cloud": cloud_icon,
    "rain": rain_icon,
    "snow": snow_icon,
    "fog": fog_icon,
    "unknown": unknown_icon,
}


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, gen in GENERATORS.items():
        path = os.path.join(OUT_DIR, name + ".bmp")
        gen().save(path, "BMP")
        print("wrote", path)


if __name__ == "__main__":
    main()
