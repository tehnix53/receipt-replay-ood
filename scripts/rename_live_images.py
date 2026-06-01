#!/usr/bin/env python3
"""Rename LIVE/*.jpeg from replay_* to live_* and update metadata CSV paths."""

from __future__ import annotations

import csv
import re
from pathlib import Path

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"
LIVE_ROOT = DATA_ROOT / "LIVE"
REPLAY_NAME = re.compile(r"^replay_(\d+)(\.jpe?g)$", re.IGNORECASE)

PATH_COLUMNS = ("path", "old_path", "new_path", "images", "id")


def _live_new_name(name: str) -> str | None:
    m = REPLAY_NAME.match(name)
    if not m:
        return None
    return f"live_{m.group(1)}{m.group(2).lower()}"


def _replace_live_path(text: str) -> str:
    if not text:
        return text
    # Only paths under LIVE/ (or bare filenames when updating a LIVE subfolder csv).
    if "LIVE/" in text:
        return re.sub(r"(^|/)replay_(\d+)(\.jpe?g)$", r"\1live_\2\3", text, flags=re.IGNORECASE)
    return text


def _replace_live_basename(text: str) -> str:
    """For metadata.csv inside LIVE/<device>/ where path is just the filename."""
    if not text or "/" in text or "\\" in text:
        return _replace_live_path(text)
    m = REPLAY_NAME.match(text)
    if m:
        return f"live_{m.group(1)}{m.group(2).lower()}"
    return text


def rename_live_files() -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []
    for src in sorted(LIVE_ROOT.rglob("replay_*.jpeg")):
        if not src.is_file():
            continue
        new_name = _live_new_name(src.name)
        if not new_name:
            continue
        dst = src.with_name(new_name)
        pairs.append((src, dst))
    for src, dst in pairs:
        if dst.exists() and dst.resolve() != src.resolve():
            raise FileExistsError(f"Target already exists: {dst}")
    for src, dst in pairs:
        src.rename(dst)
        json_src = src.with_suffix(".json")
        if json_src.exists():
            json_src.rename(dst.with_suffix(".json"))
    return pairs


def _path_rewriter(csv_path: Path):
    rel = csv_path.relative_to(DATA_ROOT)
    in_live_subfolder = rel.parts[:1] == ("LIVE",) and len(rel.parts) >= 3

    def rewrite(text: str) -> str:
        if in_live_subfolder:
            return _replace_live_basename(text)
        return _replace_live_path(text)

    return rewrite


def update_csv_file(csv_path: Path) -> int:
    if not csv_path.is_file():
        return 0
    rewrite = _path_rewriter(csv_path)
    changed = 0
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = []
        for row in reader:
            new_row = dict(row)
            for col in PATH_COLUMNS:
                if col in new_row and new_row[col]:
                    updated = rewrite(new_row[col])
                    if updated != new_row[col]:
                        new_row[col] = updated
                        changed += 1
            rows.append(new_row)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return changed


def main() -> None:
    pairs = rename_live_files()
    print(f"Renamed {len(pairs)} image file(s) under LIVE/")

    csv_files = list(DATA_ROOT.rglob("*.csv"))
    total_changes = 0
    for csv_path in sorted(csv_files):
        n = update_csv_file(csv_path)
        if n:
            print(f"  {csv_path.relative_to(DATA_ROOT)}: {n} cell(s) updated")
            total_changes += n
    print(f"Total CSV cell updates: {total_changes}")


if __name__ == "__main__":
    main()
