"""Receipt Replay OOD — metadata labeling viewer (Streamlit)."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from typing import Any

import cv2
import numpy as np
import streamlit as st
from PIL import Image

from metadata_viewer.canvas_compat import patch_streamlit_image_for_drawable_canvas, st_canvas
from metadata_viewer.corners import count_polygon_vertices, extract_polygon_canvas_pixels
from metadata_viewer.io import (
    CSV_COLUMNS,
    box_points_image_space,
    default_metadata_path,
    ensure_metadata_csv,
    load_metadata,
    make_box_json,
    parse_box_json,
    rel_path,
    scan_images,
    write_metadata,
)
from metadata_viewer.layout import (
    canvas_background,
    canvas_points_to_image,
    draw_polygon_on_bgr,
    overlay_polygon_on_frame,
    polygon_initial_drawing,
    viewer_layout,
)
from metadata_viewer.keyboard_nav import consume_nav_query_param, render_keyboard_nav
from metadata_viewer.ui_styles import inject_app_styles

patch_streamlit_image_for_drawable_canvas()

st.set_page_config(page_title="Receipt Replay Metadata", layout="wide", initial_sidebar_state="expanded")

THUMB_MAX_SIDE = 180
CACHE_DIR = Path(__file__).resolve().parent / ".thumbnail_cache"

ENV_LABELS = ["(not set)", "indoor", "outdoor"]
ENV_LABEL_TO_VALUE = {"(not set)": "", "indoor": "indoor", "outdoor": "outdoor"}
FINGERS_LABELS = ["(not set)", "fingers", "without_fingers"]
FINGERS_LABEL_TO_VALUE = {
    "(not set)": "",
    "fingers": "fingers",
    "without_fingers": "without_fingers",
}


def _safe_key(text: str) -> str:
    """Stable unique widget key (full path hashed — no truncation collisions)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


def _label_to_env(value: str) -> str:
    return ENV_LABEL_TO_VALUE.get(value, "")


def _env_to_label(value: str) -> str:
    for label, stored in ENV_LABEL_TO_VALUE.items():
        if stored == value:
            return label
    return "(not set)"


def _label_to_fingers(value: str) -> str:
    return FINGERS_LABEL_TO_VALUE.get(value, "")


def _fingers_to_label(value: str) -> str:
    for label, stored in FINGERS_LABEL_TO_VALUE.items():
        if stored == value:
            return label
    return "(not set)"


def _short_label(text: str, max_len: int = 36) -> str:
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _init_state() -> None:
    defaults: dict[str, Any] = {
        "dataset_root": "",
        "metadata_csv": "",
        "metadata_rows": [],
        "folder_scan_index": [],
        "image_index": 0,
        "current_image_path": "",
        "current_rel_path": "",
        "polygon_epoch": 0,
        "apply_polygon_initial": False,
        "pending_polygon_initial": None,
        "last_label_draft": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _choose_folder_native() -> str | None:
    if sys.platform == "darwin":
        script = 'POSIX path of (choose folder with prompt "Choose image folder")'
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                check=False,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except Exception:
            result = None
        if result is not None and result.returncode == 0:
            path = result.stdout.strip()
            if path:
                return path
    code = r"""
import tkinter as tk
from tkinter import filedialog
root = tk.Tk()
root.withdraw()
root.attributes("-topmost", True)
path = filedialog.askdirectory(title="Choose image folder")
root.destroy()
print(path)
"""
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except Exception:
        return None
    if result is None or result.returncode != 0:
        return None
    path = result.stdout.strip()
    return path or None


def _thumbnail_cache_path(image_path: Path, box_json: str = "") -> Path:
    stat = image_path.stat()
    box_tag = hashlib.sha1(box_json.encode("utf-8")).hexdigest()[:12] if box_json else "nobox"
    raw = f"{image_path.resolve()}::{stat.st_mtime_ns}::{stat.st_size}::{box_tag}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{digest}.jpg"


def _create_cached_thumbnail(image_path: Path, row: dict[str, str] | None = None) -> Path | None:
    box_json = (row or {}).get("box", "")
    thumb_path = _thumbnail_cache_path(image_path, box_json)
    if thumb_path.exists():
        return thumb_path
    bgr = cv2.imread(str(image_path))
    if bgr is None:
        return None
    h, w = bgr.shape[:2]
    pts = box_points_image_space(parse_box_json(box_json))
    scale = min(THUMB_MAX_SIDE / max(h, w), 1.0)
    if scale < 1.0:
        nh, nw = int(h * scale), int(w * scale)
        bgr = cv2.resize(bgr, (nw, nh), interpolation=cv2.INTER_AREA)
        if pts:
            pts = [(x * scale, y * scale) for x, y in pts]
    if pts:
        bgr = draw_polygon_on_bgr(bgr, pts)
    thumb_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(thumb_path), bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
    return thumb_path


def _scan_folder_for_thumbnails(folder: str) -> list[dict[str, str]]:
    root = Path(folder).expanduser().resolve()
    rows = _rows_by_rel_path() if st.session_state.get("metadata_rows") else {}
    results: list[dict[str, str]] = []
    for image_path in scan_images(root):
        rel = rel_path(image_path, root)
        thumb_path = _create_cached_thumbnail(image_path, rows.get(rel))
        if thumb_path is None:
            continue
        results.append(
            {
                "path": str(image_path.resolve()),
                "rel_path": rel_path(image_path, root),
                "thumb_path": str(thumb_path),
                "name": image_path.name,
            }
        )
    return results


def _rows_by_rel_path() -> dict[str, dict[str, str]]:
    return {row["path"]: row for row in st.session_state.metadata_rows}


def _current_row() -> dict[str, str] | None:
    rel = st.session_state.get("current_rel_path", "")
    if not rel:
        return None
    return _rows_by_rel_path().get(rel)


def _open_folder(folder: str) -> None:
    root = Path(folder).expanduser().resolve()
    csv_path, rows = ensure_metadata_csv(root)
    st.session_state.dataset_root = str(root)
    st.session_state.metadata_csv = str(csv_path)
    st.session_state.metadata_rows = rows
    st.session_state.folder_scan_index = _scan_folder_for_thumbnails(str(root))
    st.session_state.image_index = 0
    if st.session_state.folder_scan_index:
        _set_image_index(0)
    else:
        st.session_state.current_image_path = ""
        st.session_state.current_rel_path = ""


def _persist_metadata() -> None:
    csv_path = Path(st.session_state.metadata_csv)
    write_metadata(csv_path, st.session_state.metadata_rows)


def _update_current_row(**fields: str) -> None:
    rel = st.session_state.get("current_rel_path", "")
    if not rel:
        return
    rows = st.session_state.metadata_rows
    for i, row in enumerate(rows):
        if row["path"] == rel:
            rows[i] = {**row, **fields}
            break
    _persist_metadata()


def _fields_from_canvas(
    objs: list[dict[str, Any]],
    layout: Any,
    w0: int,
    h0: int,
    *,
    env_label: str,
    fingers_label: str,
    existing_box: str = "",
) -> dict[str, str]:
    """Build metadata fields from the current canvas and radio selections."""
    raw = extract_polygon_canvas_pixels(objs, layout.viewer_w, layout.viewer_h)
    box_json = existing_box
    if raw is not None and len(raw) >= 3:
        img_pts = canvas_points_to_image(raw, layout)
        box_json = make_box_json(img_pts, image_width=w0, image_height=h0)
    return {
        "box": box_json,
        "environment": _label_to_env(env_label),
        "fingers_presence": _label_to_fingers(fingers_label),
    }


def _refresh_label_draft(
    objs: list[dict[str, Any]],
    layout: Any,
    w0: int,
    h0: int,
    *,
    env_label: str,
    fingers_label: str,
    row: dict[str, str],
) -> None:
    rel = st.session_state.get("current_rel_path", "")
    if not rel:
        return
    st.session_state.last_label_draft = {
        "rel_path": rel,
        **_fields_from_canvas(
            objs,
            layout,
            w0,
            h0,
            env_label=env_label,
            fingers_label=fingers_label,
            existing_box=row.get("box", ""),
        ),
    }


def _autosave_draft() -> bool:
    """Persist the last in-memory draft for the current image (before navigating away)."""
    draft = st.session_state.get("last_label_draft")
    rel = st.session_state.get("current_rel_path", "")
    if not draft or not rel or draft.get("rel_path") != rel:
        return False
    _update_current_row(
        box=draft.get("box", ""),
        environment=draft.get("environment", ""),
        fingers_presence=draft.get("fingers_presence", ""),
    )
    return True


def _set_image_index(idx: int) -> None:
    _autosave_draft()
    items = st.session_state.folder_scan_index
    if not items:
        return
    idx = max(0, min(idx, len(items) - 1))
    st.session_state.image_index = idx
    item = items[idx]
    st.session_state.current_image_path = item["path"]
    st.session_state.current_rel_path = item["rel_path"]
    st.session_state.polygon_epoch = int(st.session_state.polygon_epoch) + 1
    row = _rows_by_rel_path().get(item["rel_path"], {})
    box = parse_box_json(row.get("box", ""))
    pts = box_points_image_space(box)
    if pts:
        st.session_state.pending_polygon_initial = pts
        st.session_state.apply_polygon_initial = True
    else:
        st.session_state.pending_polygon_initial = None
        st.session_state.apply_polygon_initial = False


def _nav_delta(delta: int) -> None:
    _set_image_index(int(st.session_state.image_index) + delta)


def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown("##### Dataset folder")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Choose folder", key="btn_choose_folder", use_container_width=True):
                selected = _choose_folder_native()
                if selected:
                    with st.spinner("Scanning images…"):
                        _open_folder(selected)
                    st.rerun()
                else:
                    st.warning("No folder selected.")
        with c2:
            if st.button("Clear", key="btn_clear_folder", use_container_width=True):
                st.session_state.dataset_root = ""
                st.session_state.metadata_csv = ""
                st.session_state.metadata_rows = []
                st.session_state.folder_scan_index = []
                st.session_state.current_image_path = ""
                st.session_state.current_rel_path = ""
                st.rerun()

        if st.session_state.dataset_root:
            st.caption(f"Root: `{st.session_state.dataset_root}`")
            st.caption(f"CSV: `{st.session_state.metadata_csv}`")
            labeled = sum(
                1
                for r in st.session_state.metadata_rows
                if r.get("box") or r.get("environment") or r.get("fingers_presence")
            )
            st.caption(
                f"{len(st.session_state.folder_scan_index)} images · "
                f"{labeled} with any label"
            )

        if st.session_state.folder_scan_index:
            total_thumbs = len(st.session_state.folder_scan_index)
            with st.container(height=720, border=True, key="thumb_list"):
                current_rel = st.session_state.get("current_rel_path", "")
                for i, item in enumerate(st.session_state.folder_scan_index):
                    is_active = item["rel_path"] == current_rel
                    row = _rows_by_rel_path().get(item["rel_path"], {})
                    flags = []
                    if row.get("box"):
                        flags.append("box")
                    if row.get("environment"):
                        flags.append(row["environment"][:3])
                    if row.get("fingers_presence"):
                        flags.append("fin" if row["fingers_presence"] == "fingers" else "no-fin")
                    flag_txt = f" [{', '.join(flags)}]" if flags else ""
                    thumb = Path(item["thumb_path"])
                    with st.container(border=is_active):
                        if thumb.exists():
                            st.image(str(thumb), use_container_width=True)
                        btn_label = f"{i + 1}/{total_thumbs} · {_short_label(item['name'])}{flag_txt}"
                        if st.button(
                            btn_label,
                            key=f"thumb_{i}_{_safe_key(item['path'])}",
                            use_container_width=True,
                            type="primary" if is_active else "secondary",
                            help=item["rel_path"],
                        ):
                            _set_image_index(i)
                            st.rerun()


def _render_main() -> None:
    if not st.session_state.current_image_path:
        st.info("Choose a folder in the sidebar to start labeling.")
        return

    image_path = Path(st.session_state.current_image_path)
    bgr = cv2.imread(str(image_path))
    if bgr is None:
        st.error(f"Could not read image: {image_path}")
        return

    h0, w0 = bgr.shape[:2]
    layout = viewer_layout(w0, h0)
    row = _current_row() or {}
    idx = int(st.session_state.image_index)
    total = len(st.session_state.folder_scan_index)

    rel_display = row.get("path", image_path.name)
    st.markdown(f"### {idx + 1} / {total}")
    st.caption(rel_display)

    consume_nav_query_param(
        image_index=idx,
        total=total,
        on_index_change=_set_image_index,
    )
    render_keyboard_nav()

    nav1, nav2, nav3, nav4 = st.columns([1, 1, 2, 1])
    with nav1:
        if st.button("← Previous (A)", key="btn_prev_image", disabled=idx <= 0):
            _nav_delta(-1)
            st.rerun()
    with nav2:
        if st.button("Next (D)", key="btn_next_image", disabled=idx >= total - 1):
            _nav_delta(1)
            st.rerun()
    with nav3:
        st.caption(
            "Hotkeys: **←** **→** or **A** **D**. "
            "Labels auto-save when you go to another image."
        )
    with nav4:
        jump = st.number_input(
            "Go to #",
            min_value=1,
            max_value=max(1, total),
            value=idx + 1,
            step=1,
            key="jump_to_index",
        )
        if int(jump) - 1 != idx and st.button("Go", key="btn_jump"):
            _set_image_index(int(jump) - 1)
            st.rerun()

    saved_pts = box_points_image_space(parse_box_json(row.get("box", "")))

    with st.container(border=True, key="receipt_viewer_panel"):
        env_label, fingers_label = _render_env_fingers_section(row)

        with st.container(key="canvas_wrap"):
            frame = canvas_background(bgr, layout)
            if saved_pts:
                frame = overlay_polygon_on_frame(frame, layout, saved_pts)
            canvas_key = _safe_key(
                f"poly_{st.session_state.current_rel_path}_{st.session_state.polygon_epoch}"
            )
            canvas_kwargs: dict[str, Any] = {
                "fill_color": "rgba(0, 229, 255, 0.18)",
                "stroke_width": 3,
                "stroke_color": "#00e5ff",
                "background_image": frame,
                "update_streamlit": True,
                "height": layout.viewer_h,
                "width": layout.viewer_w,
                "drawing_mode": "polygon",
                "display_toolbar": False,
                "polygon_realtime": True,
                "key": canvas_key,
            }
            if st.session_state.apply_polygon_initial and st.session_state.pending_polygon_initial:
                canvas_kwargs["initial_drawing"] = polygon_initial_drawing(
                    st.session_state.pending_polygon_initial,
                    layout,
                )
                st.session_state.apply_polygon_initial = False
            canvas_result = st_canvas(**canvas_kwargs)

        objs_raw = (canvas_result.json_data or {}).get("objects") or []
        objs = [o for o in objs_raw if isinstance(o, dict)]
        vertex_count = count_polygon_vertices(objs, layout.viewer_w, layout.viewer_h)
        box_hint = " · saved box shown" if saved_pts else ""
        st.caption(f"Polygon vertices: {vertex_count} (double-click to close){box_hint}")
    _render_polygon_panel(objs, layout, row, w0, h0, env_label, fingers_label)
    _refresh_label_draft(
        objs,
        layout,
        w0,
        h0,
        env_label=env_label,
        fingers_label=fingers_label,
        row=row,
    )


def _render_env_fingers_section(row: dict[str, str]) -> tuple[str, str]:
    """Environment and fingers at the top of the receipt viewer panel."""
    rel_key = _safe_key(st.session_state.current_rel_path)
    r_env, r_fin = st.columns(2, gap="large")
    with r_env:
        st.markdown("**Environment**")
        env_label = st.radio(
            "Indoor / outdoor",
            options=ENV_LABELS,
            index=ENV_LABELS.index(_env_to_label(row.get("environment", ""))),
            key=f"env_{rel_key}",
            horizontal=True,
        )
    with r_fin:
        st.markdown("**Fingers**")
        fingers_label = st.radio(
            "Presence",
            options=FINGERS_LABELS,
            index=FINGERS_LABELS.index(_fingers_to_label(row.get("fingers_presence", ""))),
            key=f"fingers_{rel_key}",
            horizontal=True,
        )
    return env_label, fingers_label


def _render_polygon_panel(
    objs: list[dict[str, Any]],
    layout: Any,
    row: dict[str, str],
    w0: int,
    h0: int,
    env_label: str,
    fingers_label: str,
) -> None:
    """Polygon drawing actions below environment / fingers."""
    with st.container(border=True, key="label_panel"):
        st.markdown("**Receipt polygon**")
        if st.button("Save polygon", key="btn_save_polygon", use_container_width=True, type="primary"):
            raw = extract_polygon_canvas_pixels(objs, layout.viewer_w, layout.viewer_h)
            if raw is None or len(raw) < 3:
                st.warning("Draw a closed polygon with at least 3 points first.")
            else:
                fields = _fields_from_canvas(
                    objs,
                    layout,
                    w0,
                    h0,
                    env_label=env_label,
                    fingers_label=fingers_label,
                    existing_box=row.get("box", ""),
                )
                _update_current_row(**fields)
                st.session_state.last_label_draft = {
                    "rel_path": st.session_state.current_rel_path,
                    **fields,
                }
                st.success("Polygon saved.")
        if st.button("Clear polygon", key="btn_clear_polygon", use_container_width=True):
            _update_current_row(box="")
            st.session_state.pending_polygon_initial = None
            st.session_state.polygon_epoch = int(st.session_state.polygon_epoch) + 1
            st.session_state.apply_polygon_initial = False
            draft = st.session_state.get("last_label_draft") or {}
            if draft.get("rel_path") == st.session_state.current_rel_path:
                draft["box"] = ""
                st.session_state.last_label_draft = draft
            st.rerun()

        st.markdown("")
        if st.button("Save all fields", key="btn_save_all", use_container_width=False, type="primary"):
            fields = _fields_from_canvas(
                objs,
                layout,
                w0,
                h0,
                env_label=env_label,
                fingers_label=fingers_label,
                existing_box=row.get("box", ""),
            )
            _update_current_row(**fields)
            st.session_state.last_label_draft = {
                "rel_path": st.session_state.current_rel_path,
                **fields,
            }
            st.success("All fields saved.")

        with st.expander("Current CSV row"):
            st.json({k: row.get(k, "") for k in CSV_COLUMNS})


def main() -> None:
    _init_state()
    inject_app_styles()
    st.title("Receipt Replay OOD — Metadata Viewer")
    _render_sidebar()
    _render_main()


if __name__ == "__main__":
    main()
