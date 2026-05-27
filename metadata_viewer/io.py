"""CSV metadata and folder scanning for Receipt Replay OOD labeling."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}

CSV_COLUMNS = ("path", "box", "environment", "fingers_presence")


def default_metadata_path(folder: str | Path) -> Path:
    return Path(folder).expanduser().resolve() / "metadata.csv"


def scan_images(folder: str | Path) -> list[Path]:
    root = Path(folder).expanduser().resolve()
    if not root.is_dir():
        return []
    return sorted(
        [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES],
        key=lambda p: str(p).lower(),
    )


def rel_path(image_path: Path, root: Path) -> str:
    try:
        return str(image_path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(image_path.resolve())


def load_metadata(csv_path: Path) -> dict[str, dict[str, str]]:
    if not csv_path.is_file():
        return {}
    rows: dict[str, dict[str, str]] = {}
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            path = (row.get("path") or "").strip()
            if not path:
                continue
            rows[path] = {col: (row.get(col) or "").strip() for col in CSV_COLUMNS}
    return rows


def write_metadata(csv_path: Path, rows: list[dict[str, str]]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(CSV_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in CSV_COLUMNS})


def build_rows(
    image_paths: list[Path],
    root: Path,
    existing: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for image_path in image_paths:
        key = rel_path(image_path, root)
        prev = existing.get(key, {})
        rows.append(
            {
                "path": key,
                "box": prev.get("box", ""),
                "environment": prev.get("environment", ""),
                "fingers_presence": prev.get("fingers_presence", ""),
            }
        )
    return rows


def ensure_metadata_csv(folder: str | Path) -> tuple[Path, list[dict[str, str]]]:
    root = Path(folder).expanduser().resolve()
    csv_path = default_metadata_path(root)
    images = scan_images(root)
    existing = load_metadata(csv_path) if csv_path.is_file() else {}
    rows = build_rows(images, root, existing)
    write_metadata(csv_path, rows)
    return csv_path, rows


def parse_box_json(raw: str) -> dict[str, Any] | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def box_points_image_space(box: dict[str, Any] | None) -> list[tuple[float, float]] | None:
    if not box:
        return None
    pts = box.get("points")
    if not isinstance(pts, list) or len(pts) < 3:
        return None
    out: list[tuple[float, float]] = []
    for pt in pts:
        if isinstance(pt, (list, tuple)) and len(pt) >= 2:
            out.append((float(pt[0]), float(pt[1])))
    return out if len(out) >= 3 else None


def make_box_json(
    points: list[tuple[float, float]],
    *,
    image_width: int,
    image_height: int,
    label: str = "receipt",
) -> str:
    payload = {
        "label": label,
        "shape_type": "polygon",
        "points": [[round(x, 2), round(y, 2)] for x, y in points],
        "image_width": image_width,
        "image_height": image_height,
    }
    return json.dumps(payload, ensure_ascii=False)
