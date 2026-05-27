"""Parse drawable-canvas polygon objects (from fraud_trend_viewer)."""

from __future__ import annotations

import math
from typing import Any


def _num(obj: dict[str, Any], key: str, default: float = 0.0) -> float:
    return float(obj.get(key, default) or default)


def _path_commands_to_points(path: Any) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    if not isinstance(path, list):
        return pts
    for cmd in path:
        if not isinstance(cmd, (list, tuple)):
            continue
        if len(cmd) >= 3:
            c0 = str(cmd[0]).upper() if cmd[0] is not None else ""
            if c0 in ("M", "L") and isinstance(cmd[1], (int, float)) and isinstance(cmd[2], (int, float)):
                pts.append((float(cmd[1]), float(cmd[2])))
            elif c0 == "Q" and len(cmd) >= 5:
                pts.append((float(cmd[3]), float(cmd[4])))
        elif len(cmd) == 2 and isinstance(cmd[0], (int, float)) and isinstance(cmd[1], (int, float)):
            pts.append((float(cmd[0]), float(cmd[1])))
    return pts


def _points_key_from_object(obj: dict[str, Any]) -> list[tuple[float, float]]:
    raw = obj.get("points")
    if not isinstance(raw, list):
        return []
    out: list[tuple[float, float]] = []
    for pt in raw:
        if isinstance(pt, dict):
            out.append((float(pt.get("x", 0)), float(pt.get("y", 0))))
    return out


def _near(a: tuple[float, float], b: tuple[float, float], eps: float = 2.0) -> bool:
    return math.hypot(a[0] - b[0], a[1] - b[1]) < eps


def _strip_closing_duplicate(pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if len(pts) > 1 and _near(pts[0], pts[-1]):
        return pts[:-1]
    return pts


def _translate(pts: list[tuple[float, float]], dx: float, dy: float) -> list[tuple[float, float]]:
    return [(x + dx, y + dy) for x, y in pts]


def _polygon_area(pts: list[tuple[float, float]]) -> float:
    if len(pts) < 3:
        return 0.0
    acc = 0.0
    for i, (x1, y1) in enumerate(pts):
        x2, y2 = pts[(i + 1) % len(pts)]
        acc += x1 * y2 - x2 * y1
    return abs(acc) / 2.0


def _overflow_penalty(pts: list[tuple[float, float]], canvas_w: int, canvas_h: int) -> float:
    penalty = 0.0
    for x, y in pts:
        penalty += max(0.0, -x) + max(0.0, x - canvas_w)
        penalty += max(0.0, -y) + max(0.0, y - canvas_h)
    return penalty


def _best_canvas_candidate(
    obj: dict[str, Any],
    raw_pts: list[tuple[float, float]],
    canvas_w: int | None,
    canvas_h: int | None,
) -> list[tuple[float, float]]:
    left = _num(obj, "left")
    top = _num(obj, "top")
    width = _num(obj, "width")
    height = _num(obj, "height")
    po = obj.get("pathOffset") if isinstance(obj.get("pathOffset"), dict) else {}
    path_x = float(po.get("x", 0) or 0) if isinstance(po, dict) else 0.0
    path_y = float(po.get("y", 0) or 0) if isinstance(po, dict) else 0.0

    candidates = [
        raw_pts,
        _translate(raw_pts, left, top),
        _translate(raw_pts, left + width / 2.0 - path_x, top + height / 2.0 - path_y),
        _translate(raw_pts, left - path_x, top - path_y),
    ]

    if canvas_w is None or canvas_h is None:
        return max(candidates, key=_polygon_area)

    def score(pts: list[tuple[float, float]]) -> float:
        overflow = _overflow_penalty(pts, canvas_w, canvas_h)
        min_x = min(x for x, _ in pts)
        min_y = min(y for _, y in pts)
        bbox_alignment = abs(min_x - left) + abs(min_y - top)
        return -overflow * 1_000_000.0 - bbox_alignment * 1_000.0 + _polygon_area(pts)

    return max(candidates, key=score)


def best_polygon_points(
    objects: list[dict[str, Any]] | None,
    canvas_w: int | None = None,
    canvas_h: int | None = None,
) -> list[tuple[float, float]] | None:
    if not objects:
        return None
    best: list[tuple[float, float]] = []
    for obj in objects:
        cand = _points_key_from_object(obj)
        if len(cand) < 3:
            cand = _path_commands_to_points(obj.get("path"))
        if len(cand) >= 3:
            cand = _best_canvas_candidate(obj, cand, canvas_w, canvas_h)
        cand = _strip_closing_duplicate(cand)
        if len(cand) >= len(best):
            best = cand
    if len(best) < 3:
        return None
    return best


def count_polygon_vertices(
    objects: list[dict[str, Any]] | None,
    canvas_w: int | None = None,
    canvas_h: int | None = None,
) -> int:
    if not objects:
        return 0
    best = 0
    for obj in objects:
        cand = _points_key_from_object(obj)
        if len(cand) < 1:
            cand = _path_commands_to_points(obj.get("path"))
        if not cand:
            continue
        if canvas_w is not None and canvas_h is not None and len(cand) >= 2:
            cand = _best_canvas_candidate(obj, cand, canvas_w, canvas_h)
        cand = _strip_closing_duplicate(cand)
        best = max(best, len(cand))
    return best


def scale_points_to_image(
    pts: list[tuple[float, float]],
    canvas_w: int,
    canvas_h: int,
    img_w: int,
    img_h: int,
) -> list[tuple[float, float]]:
    sx = img_w / max(canvas_w, 1)
    sy = img_h / max(canvas_h, 1)
    return [(x * sx, y * sy) for x, y in pts]


def extract_polygon_canvas_pixels(
    objects: list[dict[str, Any]] | None,
    canvas_w: int | None = None,
    canvas_h: int | None = None,
) -> list[tuple[float, float]] | None:
    return best_polygon_points(objects, canvas_w, canvas_h)
