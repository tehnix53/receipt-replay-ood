#!/usr/bin/env python3
"""Merge box (and related fields) from nested metadata.csv into data/metadata.csv."""

from __future__ import annotations

import csv
from pathlib import Path

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"
ROOT_CSV = DATA_ROOT / "metadata.csv"
MERGE_COLUMNS = ("box", "environment", "fingers_presence")


def load_nested() -> dict[str, dict[str, str]]:
    by_path: dict[str, dict[str, str]] = {}
    for csv_path in sorted(DATA_ROOT.rglob("metadata.csv")):
        if csv_path == ROOT_CSV:
            continue
        prefix = csv_path.parent.relative_to(DATA_ROOT).as_posix()
        with csv_path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                full_path = f"{prefix}/{row['path']}"
                by_path[full_path] = row
    return by_path


def main() -> None:
    nested = load_nested()
    with ROOT_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or list(MERGE_COLUMNS)
        rows = list(reader)

    updated = 0
    for row in rows:
        src = nested.get(row["path"])
        if not src:
            continue
        for col in MERGE_COLUMNS:
            val = (src.get(col) or "").strip()
            if val and row.get(col) != val:
                row[col] = val
                updated += 1

    with ROOT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with_box = sum(1 for r in rows if (r.get("box") or "").strip())
    print(f"Merged from {len(nested)} nested row(s)")
    print(f"Root metadata: {len(rows)} row(s), {with_box} with box")


if __name__ == "__main__":
    main()
