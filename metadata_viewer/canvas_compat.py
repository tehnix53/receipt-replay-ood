"""Streamlit drawable canvas compatibility shim."""

from __future__ import annotations

from hashlib import md5

import numpy as np
import streamlit as st
import streamlit.elements.image as st_image
from PIL import Image
from streamlit_drawable_canvas import CanvasResult, _component_func, _data_url_to_image
from streamlit_drawable_canvas import st_canvas as _library_st_canvas


def patch_streamlit_image_for_drawable_canvas() -> None:
    if hasattr(st_image, "image_to_url"):
        return

    from streamlit.elements.lib import image_utils
    from streamlit.elements.lib.layout_utils import create_layout_config

    def image_to_url(
        image: object,
        width: int,
        clamp: bool,
        channels: str,
        output_format: str,
        image_id: str,
    ) -> str:
        layout_config = create_layout_config(width=width)
        return image_utils.image_to_url(
            image,
            layout_config,
            clamp,
            channels,
            output_format,
            image_id,
        )

    st_image.image_to_url = image_to_url  # type: ignore[attr-defined]


def _resize_img(img: Image.Image, new_height: int, new_width: int) -> Image.Image:
    w_ratio = new_width / img.width
    h_ratio = new_height / img.height
    return img.resize((int(img.width * w_ratio), int(img.height * h_ratio)))


def st_canvas(
    fill_color: str = "#eee",
    stroke_width: int = 20,
    stroke_color: str = "black",
    background_color: str = "",
    background_image: Image.Image | None = None,
    update_streamlit: bool = True,
    height: int = 400,
    width: int = 600,
    drawing_mode: str = "freedraw",
    initial_drawing: dict | None = None,
    display_toolbar: bool = True,
    point_display_radius: int = 3,
    key: str | None = None,
    *,
    polygon_realtime: bool = False,
) -> CanvasResult:
    if not polygon_realtime or drawing_mode != "polygon":
        return _library_st_canvas(
            fill_color=fill_color,
            stroke_width=stroke_width,
            stroke_color=stroke_color,
            background_color=background_color,
            background_image=background_image,
            update_streamlit=update_streamlit,
            height=height,
            width=width,
            drawing_mode=drawing_mode,
            initial_drawing=initial_drawing,
            display_toolbar=display_toolbar,
            point_display_radius=point_display_radius,
            key=key,
        )

    background_image_url = None
    if background_image:
        background_image = _resize_img(background_image, height, width)
        background_image_url = st_image.image_to_url(
            background_image,
            width,
            True,
            "RGB",
            "PNG",
            f"drawable-canvas-bg-{md5(background_image.tobytes()).hexdigest()}-{key}",
        )
        background_image_url = st._config.get_option("server.baseUrlPath") + background_image_url
        background_color = ""

    initial_drawing = {"version": "4.4.0"} if initial_drawing is None else initial_drawing
    initial_drawing["background"] = background_color

    component_value = _component_func(
        fillColor=fill_color,
        strokeWidth=stroke_width,
        strokeColor=stroke_color,
        backgroundColor=background_color,
        backgroundImageURL=background_image_url,
        realtimeUpdateStreamlit=update_streamlit,
        canvasHeight=height,
        canvasWidth=width,
        drawingMode=drawing_mode,
        initialDrawing=initial_drawing,
        displayToolbar=display_toolbar,
        displayRadius=point_display_radius,
        key=key,
        default=None,
    )
    if component_value is None:
        return CanvasResult()

    return CanvasResult(
        np.asarray(_data_url_to_image(component_value["data"])),
        component_value["raw"],
    )
