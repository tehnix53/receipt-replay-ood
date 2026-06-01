# Receipt Replay OOD

A small out-of-domain benchmark for screen replay detection under domain shift.

## Overview

Receipt Replay OOD is a compact benchmark dataset for evaluating cross-domain robustness of document replay attack detection systems.

The dataset contains:
- bona fide receipt captures
- replay attack samples
- receipt localization annotations
- metadata for acquisition conditions

<!-- dataset-preview-start -->
![preview](data/LIVE/Huawei%20P30%20Lite/live_0380.jpeg) ![preview](data/LIVE/Honor%208A/live_0126.jpeg) ![preview](data/LIVE/Honor%208A/live_0013.jpeg) ![preview](data/LIVE/Honor%208A/live_0141.jpeg)

![preview](data/REPLAY/Phillips%20PHL%20271V8%20and%20MacBook%20Pro%20M1/replay_1190.jpeg) ![preview](data/REPLAY/Samsung%20Galaxy%20J3%20by%20Honor%208A/replay_1256.jpeg) ![preview](data/REPLAY/Huawei%20P30%20Lite%20by%20Honor%208A/replay_0640.jpeg) ![preview](data/LIVE/Huawei%20P30%20Lite/live_0328.jpeg)

![preview](data/REPLAY/Lenovo%20ThinkBook%2015%20G2%20by%20Honor%208A/replay_0726.jpeg) ![preview](data/REPLAY/Honor%208A%20by%20Samsung%20Galaxy%20J3/replay_0602.jpeg) ![preview](data/LIVE/Honor%208A/live_0058.jpeg) ![preview](data/REPLAY/Samsung%20Galaxy%20J3%20by%20Honor%208A/replay_1252.jpeg)

<!-- dataset-preview-end -->

## Motivation

Existing document anti-spoofing datasets mainly focus on identity documents. Receipt Replay OOD introduces receipt-based replay attacks as a lightweight and privacy-safe OOD benchmark.

## Status

Publication: [Receipt Replay OOD (arXiv)](https://arxiv.org/pdf/2605.26855)

## Metadata labeling tool

A small Streamlit app (same folder-browser pattern as `fraud_trend_viewer`) lives in `metadata_viewer/`:

```bash
cd metadata_viewer
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Requires **Python 3.10+** — do not use macOS `python` (often 3.7).

Run from the repo root if you prefer: `streamlit run metadata_viewer/app.py`

1. **Choose folder** — recursively indexes all images under the dataset root.
2. Creates or updates **`metadata.csv`** in that folder with columns: `path`, `box`, `environment`, `fingers_presence`.
3. **← / →** buttons or keyboard arrows to move between images.
4. Draw a **polygon** on the receipt and **Save polygon** (stored as JSON in `box`).
5. Set **indoor** / **outdoor** and **fingers** / **without_fingers**, then save.

Paths in the CSV are relative to the chosen dataset root (e.g. `LIVE/Honor 8A/live_0001.jpeg`).
