from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_MAP = ROOT / "aboutme" / "finger_map.txt"
OUTPUT_ART = ROOT / "aboutme" / "finger_art.txt"
LEGACY_OUTPUT_MAP = ROOT / "assets" / "finger_map.txt"
TARGET_W = 24
TARGET_H = 34
ART_WIDTH = 30
ART_PALETTE = " ░▒▓█"


def default_source_image() -> Path:
    candidates = [
        Path("/Users/jana/Desktop/fingertransparent.png"),
        Path("/Users/jana/Desktop/finger.png"),
        Path("/Users/jana/Desktop/finger"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def subject_points(image: Image.Image) -> list[tuple[int, int]]:
    image = image.convert("RGBA")
    width, height = image.size
    pixels = image.load()
    points: list[tuple[int, int]] = []

    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if a > 10:
                brightness = (r + g + b) / 3
                maxc = max(r, g, b)
                minc = min(r, g, b)
                saturation = 0 if maxc == 0 else (maxc - minc) / maxc

                if brightness < 242 and (brightness < 230 or saturation > 0.08):
                    if brightness > 55:
                        points.append((x, y))

    if points:
        return points

    for y in range(height):
        for x in range(width):
            if pixels[x, y][3] > 10:
                points.append((x, y))
    return points


def build_mask(image: Image.Image) -> list[str]:
    image = image.convert("RGBA")
    width, height = image.size
    pixels = image.load()
    points = subject_points(image)
    if not points:
        return []

    minx = min(x for x, _ in points)
    maxx = max(x for x, _ in points)
    miny = min(y for _, y in points)
    maxy = max(y for _, y in points)

    mask = [[0] * width for _ in range(height)]
    use_alpha_fill = all((pixels[x, y][3] > 10) for x, y in points)

    if use_alpha_fill:
        for x, y in points:
            mask[y][x] = 1
    else:
        for x, y in points:
            mask[y][x] = 1

    crop_width = maxx - minx + 1
    crop_height = maxy - miny + 1
    scale = min(TARGET_W / crop_width, TARGET_H / crop_height)
    out_w = max(1, int(crop_width * scale))
    out_h = max(1, int(crop_height * scale))

    rows: list[str] = []
    for out_y in range(out_h):
        source_y0 = miny + out_y * crop_height / out_h
        source_y1 = miny + (out_y + 1) * crop_height / out_h
        row = []
        for out_x in range(out_w):
            source_x0 = minx + out_x * crop_width / out_w
            source_x1 = minx + (out_x + 1) * crop_width / out_w
            count = 0
            total = 0
            for y in range(int(source_y0), min(int(source_y1) + 1, height)):
                for x in range(int(source_x0), min(int(source_x1) + 1, width)):
                    total += 1
                    count += mask[y][x]
            row.append("1" if total and count / total > 0.24 else "0")
        rows.append("".join(row))

    while rows and set(rows[0]) == {"0"}:
        rows.pop(0)
    while rows and set(rows[-1]) == {"0"}:
        rows.pop()

    left = 0
    right = len(rows[0]) - 1
    while left < len(rows[0]) and all(row[left] == "0" for row in rows):
        left += 1
    while right >= 0 and all(row[right] == "0" for row in rows):
        right -= 1

    return [row[left:right + 1] for row in rows]


def build_art(image: Image.Image) -> list[str]:
    image = image.convert("RGBA")
    points = subject_points(image)
    if not points:
        return []

    minx = min(x for x, _ in points)
    maxx = max(x for x, _ in points)
    miny = min(y for _, y in points)
    maxy = max(y for _, y in points)

    image = image.crop((minx, miny, maxx + 1, maxy + 1))
    new_height = max(1, int((image.height / image.width) * ART_WIDTH * 0.55))
    image = image.resize((ART_WIDTH, new_height))

    rows: list[str] = []
    for y in range(image.height):
        row = []
        for x in range(image.width):
            r, g, b, a = image.getpixel((x, y))
            brightness = (r + g + b) / 3
            if a < 10:
                row.append(" ")
            elif brightness < 40:
                row.append("█")
            elif brightness < 90:
                row.append("▓")
            elif brightness < 180:
                row.append("▒")
            else:
                row.append("░")
        rows.append("".join(row).rstrip())
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the About Me terminal mask from a source image.")
    parser.add_argument("source", nargs="?", default=str(default_source_image()), help="Path to the source image.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = Path(args.source).expanduser().resolve()
    image = Image.open(source)
    rows = build_mask(image)
    payload = "\n".join(rows) + "\n"
    OUTPUT_MAP.write_text(payload, encoding="utf-8")
    if LEGACY_OUTPUT_MAP.parent.exists():
        LEGACY_OUTPUT_MAP.write_text(payload, encoding="utf-8")
    art_rows = build_art(image)
    OUTPUT_ART.write_text("\n".join(art_rows) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_MAP} and {OUTPUT_ART} from {source}")


if __name__ == "__main__":
    main()
