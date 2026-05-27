"""Viewer layout helpers (object-fit contain canvas frame)."""

from __future__ import annotations

from typing import NamedTuple

import cv2
import numpy as np
from PIL import Image

MAX_VIEWER_W = 780
MAX_VIEWER_H = 620
VIEWER_BG_RGB = (245, 246, 248)


class ViewerLayout(NamedTuple):
    viewer_w: int
    viewer_h: int
    content_w: int
    content_h: int
    offset_x: int
    offset_y: int
    img_w: int
    img_h: int


def viewer_layout(img_w: int, img_h: int) -> ViewerLayout:
    vw, vh = MAX_VIEWER_W, MAX_VIEWER_H
    if img_w < 1 or img_h < 1:
        cw, ch = 800, 600
    else:
        scale = min(vw / img_w, vh / img_h)
        cw = max(1, int(round(img_w * scale)))
        ch = max(1, int(round(img_h * scale)))
    ox = max(0, (vw - cw) // 2)
    oy = max(0, (vh - ch) // 2)
    return ViewerLayout(vw, vh, cw, ch, ox, oy, img_w, img_h)


def canvas_background(bgr: np.ndarray, layout: ViewerLayout) -> Image.Image:
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)
    if layout.content_w != layout.img_w or layout.content_h != layout.img_h:
        pil = pil.resize((layout.content_w, layout.content_h), Image.Resampling.LANCZOS)
    frame = Image.new("RGB", (layout.viewer_w, layout.viewer_h), VIEWER_BG_RGB)
    frame.paste(pil, (layout.offset_x, layout.offset_y))
    return frame


def canvas_points_to_image(
    pts: list[tuple[float, float]],
    layout: ViewerLayout,
) -> list[tuple[float, float]]:
    from metadata_viewer.corners import scale_points_to_image

    content_pts = [(x - layout.offset_x, y - layout.offset_y) for x, y in pts]
    return scale_points_to_image(
        content_pts,
        layout.content_w,
        layout.content_h,
        layout.img_w,
        layout.img_h,
    )


def image_points_to_canvas(
    pts: list[tuple[float, float]],
    layout: ViewerLayout,
) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for x, y in pts:
        cx = layout.offset_x + x * layout.content_w / max(layout.img_w, 1)
        cy = layout.offset_y + y * layout.content_h / max(layout.img_h, 1)
        out.append((cx, cy))
    return out


def polygon_initial_drawing(
    image_points: list[tuple[float, float]],
    layout: ViewerLayout,
) -> dict:
    canvas_pts = image_points_to_canvas(image_points, layout)
    if len(canvas_pts) < 3:
        return {"version": "4.4.0", "objects": []}

    min_x = min(x for x, _ in canvas_pts)
    min_y = min(y for _, y in canvas_pts)
    max_x = max(x for x, _ in canvas_pts)
    max_y = max(y for _, y in canvas_pts)
    path: list[list[float | str]] = []
    for i, (x, y) in enumerate(canvas_pts):
        path.append(["M" if i == 0 else "L", x - min_x, y - min_y])
    path.append(["Z"])

    obj = {
        "type": "path",
        "version": "4.4.0",
        "originX": "left",
        "originY": "top",
        "left": min_x,
        "top": min_y,
        "width": max(1.0, max_x - min_x),
        "height": max(1.0, max_y - min_y),
        "fill": "rgba(0, 229, 255, 0.12)",
        "stroke": "#00e5ff",
        "strokeWidth": 2,
        "path": path,
    }
    return {"version": "4.4.0", "objects": [obj]}
