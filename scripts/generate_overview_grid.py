#!/usr/bin/env python3
"""Build 3×4 README preview: thumbnails + montage image."""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = REPO_ROOT / "data"
README = REPO_ROOT / "README.md"
PREVIEW_DIR = REPO_ROOT / "docs" / "preview"
GRID_IMAGE = REPO_ROOT / "docs" / "overview_grid.jpg"
MARKER_START = "<!-- dataset-preview-start -->"
MARKER_END = "<!-- dataset-preview-end -->"

COLS, ROWS = 4, 3
CELL_W, CELL_H = 280, 210
PAD = 6
BG = (245, 245, 245)
SEED = 42


def _fit_cell(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    cell = Image.new("RGB", size, BG)
    thumb = img.convert("RGB")
    thumb.thumbnail(size, Image.Resampling.LANCZOS)
    x = (size[0] - thumb.width) // 2
    y = (size[1] - thumb.height) // 2
    cell.paste(thumb, (x, y))
    return cell


def _montage(cells: list[Image.Image]) -> Image.Image:
    grid_w = COLS * CELL_W + (COLS + 1) * PAD
    grid_h = ROWS * CELL_H + (ROWS + 1) * PAD
    grid = Image.new("RGB", (grid_w, grid_h), BG)
    for idx, cell in enumerate(cells):
        row, col = divmod(idx, COLS)
        x = PAD + col * (CELL_W + PAD)
        y = PAD + row * (CELL_H + PAD)
        grid.paste(cell, (x, y))
    return grid


def _grid_block() -> str:
    return "\n".join(
        [
            MARKER_START,
            "![Dataset preview](docs/overview_grid.jpg)",
            MARKER_END,
            "",
        ]
    )


def _patch_readme() -> None:
    text = README.read_text(encoding="utf-8")
    if MARKER_START not in text or MARKER_END not in text:
        raise SystemExit("README missing preview markers.")
    before = text.split(MARKER_START)[0]
    after = text.split(MARKER_END)[1]
    README.write_text(before + _grid_block() + after, encoding="utf-8")


def main() -> None:
    images = sorted(DATA_ROOT.rglob("*.jpeg"))
    live = [p for p in images if "/LIVE/" in p.as_posix()]
    replay = [p for p in images if "/REPLAY/" in p.as_posix()]
    rng = random.Random(SEED)
    picks = rng.sample(live, 6) + rng.sample(replay, 6)
    rng.shuffle(picks)

    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    GRID_IMAGE.parent.mkdir(parents=True, exist_ok=True)
    for old in PREVIEW_DIR.glob("*.jpg"):
        old.unlink()

    cells: list[Image.Image] = []
    for i, path in enumerate(picks, start=1):
        cell = _fit_cell(Image.open(path), (CELL_W, CELL_H))
        cells.append(cell)
        cell.save(PREVIEW_DIR / f"{i:02d}.jpg", format="JPEG", quality=88, optimize=True)

    _montage(cells).save(GRID_IMAGE, format="JPEG", quality=90, optimize=True)
    _patch_readme()
    print(f"Wrote {GRID_IMAGE.name} (3×4) and docs/preview/01-12.jpg")


if __name__ == "__main__":
    main()
