from __future__ import annotations

import atexit
import random
import shutil
import signal
import sys
import time
from pathlib import Path
from typing import Iterable


FPS = 20
FRAME_DELAY = 1 / FPS
RAIN_SECONDS = 1.3
CONVERGENCE_SECONDS = 2.0
REVEAL_HOLD_SECONDS = 3.0
MIN_WIDTH = 40
MIN_HEIGHT = 20
TAGLINE = "gotcha you nosey little 💩   check out https://clandestinalabs.com/"

RESET = "\033[0m"
CLEAR = "\033[2J\033[H"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
WHITE = "\033[37m"
DIM_WHITE = "\033[2;37m"
BRIGHT_WHITE = "\033[1;97m"


class TerminalGuard:
    def __init__(self) -> None:
        self.active = False

    def __enter__(self) -> "TerminalGuard":
        self.active = True
        sys.stdout.write(HIDE_CURSOR + CLEAR)
        sys.stdout.flush()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.restore()

    def restore(self) -> None:
        if not self.active:
            return
        self.active = False
        sys.stdout.write(RESET + SHOW_CURSOR)
        sys.stdout.flush()


def load_finger_art() -> list[str]:
    asset_path = Path(__file__).resolve().parent / "finger_art.txt"
    if not asset_path.exists():
        return []
    return [line.rstrip("\n") for line in asset_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_finger_map() -> list[str]:
    asset_path = Path(__file__).resolve().parent / "finger_map.txt"
    if not asset_path.exists():
        return []
    return [line.strip() for line in asset_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def scaled_target_art(width: int, height: int, finger_art: list[str]) -> dict[tuple[int, int], str]:
    map_height = len(finger_art)
    map_width = max(len(row) for row in finger_art)

    scale = 1

    rendered_width = map_width * scale
    rendered_height = map_height * scale
    origin_x = max((width - rendered_width) // 2, 0)
    origin_y = max((height - rendered_height) // 2, 0)

    cells: dict[tuple[int, int], str] = {}
    for row_index, row in enumerate(finger_art):
        for column_index, char in enumerate(row):
            if char == " ":
                continue
            for dy in range(scale):
                for dx in range(scale):
                    x = origin_x + (column_index * scale) + dx
                    y = origin_y + (row_index * scale) + dy
                    if 0 <= x < width and 0 <= y < height - 2:
                        cells[(x, y)] = char
    return cells


def scaled_target_cells(width: int, height: int, finger_map: list[str]) -> set[tuple[int, int]]:
    if not finger_map:
        return set()

    map_height = len(finger_map)
    map_width = max(len(row) for row in finger_map)

    scale = 1

    rendered_width = map_width * scale
    rendered_height = map_height * scale
    origin_x = max((width - rendered_width) // 2, 0)
    origin_y = max((height - rendered_height) // 2, 0)

    cells: set[tuple[int, int]] = set()
    for row_index, row in enumerate(finger_map):
        for column_index, char in enumerate(row):
            if char != "1":
                continue
            for dy in range(scale):
                for dx in range(scale):
                    x = origin_x + (column_index * scale) + dx
                    y = origin_y + (row_index * scale) + dy
                    if 0 <= x < width and 0 <= y < height - 2:
                        cells.add((x, y))
    return cells


def initial_columns(width: int, height: int) -> list[dict[str, int]]:
    columns: list[dict[str, int]] = []
    for _ in range(width):
        columns.append(
            {
                "head": random.randint(-height, 0),
                "speed": random.randint(1, 3),
                "trail": random.randint(max(4, height // 5), max(8, height // 2)),
            }
        )
    return columns


def draw_frame(
    width: int,
    height: int,
    columns: list[dict[str, int]],
    target_art: dict[tuple[int, int], str],
    progress: float,
    locked_cells: set[tuple[int, int]],
    tagline_progress: int = 0,
    reveal_art: bool = False,
) -> str:
    target_cells = set(target_art)
    grid = [[" " for _ in range(width)] for _ in range(height)]
    style = [["" for _ in range(width)] for _ in range(height)]

    for x, column in enumerate(columns):
        column["head"] += column["speed"]
        if column["head"] - column["trail"] > height + random.randint(0, height // 2):
            column["head"] = random.randint(-height // 2, 0)

        head = column["head"]
        trail = column["trail"]
        for offset in range(trail):
            y = head - offset
            if not (0 <= y < height):
                continue
            cell = (x, y)
            if cell in locked_cells:
                continue
            grid[y][x] = str(random.randint(0, 9))
            style[y][x] = WHITE if offset < 2 else DIM_WHITE

    if progress > 0:
        target_list = sorted(target_cells, key=lambda cell: (cell[1], cell[0]))
        target_count = int(len(target_list) * progress)
        locked_cells.update(target_list[:target_count])

    for x, y in locked_cells:
        if 0 <= x < width and 0 <= y < height:
            if reveal_art:
                grid[y][x] = target_art.get((x, y), str((x + y) % 10))
                char = grid[y][x]
                if char == "░":
                    style[y][x] = DIM_WHITE
                elif char == "▒":
                    style[y][x] = WHITE
                else:
                    style[y][x] = BRIGHT_WHITE
            else:
                grid[y][x] = str((x + y) % 10)
                style[y][x] = BRIGHT_WHITE

    tagline_y = min(height - 2, max(y for _, y in target_cells) + 3) if target_cells else height - 2
    visible_tagline = TAGLINE[:tagline_progress]
    tagline_x = max((width - len(TAGLINE)) // 2, 0)
    for index, char in enumerate(visible_tagline):
        x = tagline_x + index
        if 0 <= x < width and 0 <= tagline_y < height:
            grid[tagline_y][x] = char
            style[tagline_y][x] = WHITE

    lines = []
    for row, row_style in zip(grid, style):
        current_style = ""
        line_parts: list[str] = []
        for char, char_style in zip(row, row_style):
            target_style = char_style or RESET
            if target_style != current_style:
                line_parts.append(target_style)
                current_style = target_style
            line_parts.append(char)
        line_parts.append(RESET)
        lines.append("".join(line_parts))
    return CLEAR + "\n".join(lines)


def phase_frames(seconds: float) -> int:
    return max(1, int(seconds * FPS))


def run_animation(width: int, height: int) -> None:
    finger_art = load_finger_art()
    if finger_art:
        target_art = scaled_target_art(width, height, finger_art)
    else:
        fallback_cells = scaled_target_cells(width, height, load_finger_map())
        target_art = {cell: str((cell[0] + cell[1]) % 10) for cell in fallback_cells}
    target_cells = set(target_art)
    columns = initial_columns(width, height)
    locked_cells: set[tuple[int, int]] = set()

    rain_frames = phase_frames(RAIN_SECONDS)
    convergence_frames = phase_frames(CONVERGENCE_SECONDS)
    tagline_frames = min(len(TAGLINE), phase_frames(1.6))
    hold_frames = phase_frames(REVEAL_HOLD_SECONDS)

    for _ in range(rain_frames):
        sys.stdout.write(draw_frame(width, height, columns, target_art, 0, locked_cells))
        sys.stdout.flush()
        time.sleep(FRAME_DELAY)

    for frame in range(convergence_frames):
        progress = (frame + 1) / convergence_frames
        sys.stdout.write(draw_frame(width, height, columns, target_art, progress, locked_cells))
        sys.stdout.flush()
        time.sleep(FRAME_DELAY)

    for frame in range(tagline_frames):
        tagline_progress = int(((frame + 1) / tagline_frames) * len(TAGLINE))
        sys.stdout.write(draw_frame(width, height, columns, target_art, 1.0, locked_cells, tagline_progress, True))
        sys.stdout.flush()
        time.sleep(FRAME_DELAY)

    for _ in range(hold_frames):
        sys.stdout.write(draw_frame(width, height, columns, target_art, 1.0, locked_cells, len(TAGLINE), True))
        sys.stdout.flush()
        time.sleep(FRAME_DELAY)


def install_signal_handlers(guard: TerminalGuard) -> None:
    def handle_interrupt(signum, frame) -> None:  # type: ignore[unused-argument]
        guard.restore()
        sys.stdout.write(CLEAR)
        sys.stdout.flush()
        raise SystemExit(130)

    signal.signal(signal.SIGINT, handle_interrupt)
    signal.signal(signal.SIGTERM, handle_interrupt)


def run() -> None:
    if not sys.stdout.isatty():
        print(TAGLINE)
        return

    size = shutil.get_terminal_size(fallback=(80, 24))
    if size.columns < MIN_WIDTH or size.lines < MIN_HEIGHT:
        print("Make your terminal bigger. You'll want to see this.")
        return

    guard = TerminalGuard()
    atexit.register(guard.restore)
    install_signal_handlers(guard)

    with guard:
        run_animation(size.columns, size.lines)


if __name__ == "__main__":
    run()
