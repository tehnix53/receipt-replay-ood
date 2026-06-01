#!/usr/bin/env python3
"""Pick 12 random dataset images and update the README 3×4 preview grid."""

from __future__ import annotations

import random
from pathlib import Path

README = Path(__file__).resolve().parent.parent / "README.md"
DATA_ROOT = Path(__file__).resolve().parent.parent / "data"
MARKER_START = "<!-- dataset-preview-start -->"
MARKER_END = "<!-- dataset-preview-end -->"

COLS, ROWS = 4, 3
SEED = 42


def _md_path(path: Path) -> str:
    rel = path.relative_to(DATA_ROOT.parent).as_posix()
    return rel.replace(" ", "%20")


def _markdown_grid(image_paths: list[Path]) -> str:
    lines = [MARKER_START]
    for r in range(ROWS):
        cells = []
        for c in range(COLS):
            src = image_paths[r * COLS + c]
            cells.append(f"![preview]({_md_path(src)})")
        lines.append(" ".join(cells))
        lines.append("")
    lines.append(MARKER_END)
    return "\n".join(lines)


def _patch_readme(image_paths: list[Path]) -> None:
    block = _markdown_grid(image_paths)
    text = README.read_text(encoding="utf-8")
    if MARKER_START not in text or MARKER_END not in text:
        raise SystemExit(f"README missing preview markers.")
    before = text.split(MARKER_START)[0]
    after = text.split(MARKER_END)[1]
    README.write_text(before + block + after, encoding="utf-8")


def main() -> None:
    images = sorted(DATA_ROOT.rglob("*.jpeg"))
    live = [p for p in images if "/LIVE/" in p.as_posix()]
    replay = [p for p in images if "/REPLAY/" in p.as_posix()]
    rng = random.Random(SEED)
    picks = rng.sample(live, 6) + rng.sample(replay, 6)
    rng.shuffle(picks)
    _patch_readme(picks)
    print("Updated README preview with 12 image(s) from data/")


if __name__ == "__main__":
    main()
