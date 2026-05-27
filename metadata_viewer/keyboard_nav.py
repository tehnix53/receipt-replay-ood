"""Keyboard shortcuts for image prev/next navigation."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components


def consume_nav_query_param(
    *,
    image_index: int,
    total: int,
    on_index_change,
) -> None:
    """Apply ?nav=prev|next then clear the param (fallback when JS cannot click buttons)."""
    nav = (st.query_params.get("nav") or "").strip().lower()
    if nav not in ("prev", "next"):
        return
    if "nav" in st.query_params:
        del st.query_params["nav"]
    if nav == "prev" and image_index > 0:
        on_index_change(image_index - 1)
        st.rerun()
    elif nav == "next" and image_index < total - 1:
        on_index_change(image_index + 1)
        st.rerun()


def render_keyboard_nav() -> None:
    """Install parent-document key listeners for prev/next Streamlit buttons."""
    components.html(
        """
        <script>
        (function () {
          const win = window.parent;
          const doc = win.document;

          function clickBtn(key) {
            const selectors = [
              '[data-testid="stBaseButton-' + key + '"]',
              'div[class*="st-key-' + key + '"] button',
              '.st-key-' + key + ' button',
            ];
            for (const sel of selectors) {
              const btn = doc.querySelector(sel);
              if (btn && !btn.disabled) {
                btn.click();
                return true;
              }
            }
            return false;
          }

          function navigate(dir) {
            const key = dir < 0 ? "btn_prev_image" : "btn_next_image";
            if (clickBtn(key)) return;
            const url = new URL(win.location.href);
            url.searchParams.set("nav", dir < 0 ? "prev" : "next");
            win.location.assign(url.toString());
          }

          function onKeyDown(e) {
            const t = e.target;
            const tag = (t && t.tagName) || "";
            if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
            if (t && t.isContentEditable) return;

            const key = e.key;
            const alt = e.altKey;
            const low = key.length === 1 ? key.toLowerCase() : key;

            let dir = 0;
            if (key === "ArrowLeft" || low === "a") dir = -1;
            if (key === "ArrowRight" || low === "d") dir = 1;
            if (alt && key === "ArrowLeft") dir = -1;
            if (alt && key === "ArrowRight") dir = 1;

            if (!dir) return;
            e.preventDefault();
            navigate(dir);
          }

          if (win._rrMetaNavHandler) {
            doc.removeEventListener("keydown", win._rrMetaNavHandler, true);
          }
          win._rrMetaNavHandler = onKeyDown;
          doc.addEventListener("keydown", win._rrMetaNavHandler, true);
        })();
        </script>
        """,
        height=0,
    )
