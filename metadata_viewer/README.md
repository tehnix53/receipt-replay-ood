# Metadata viewer

Label receipt polygons and metadata for Receipt Replay OOD.

## Run

Use **Python 3.10+** (`python` on macOS is often 3.7 and will fail). Prefer `python3`:

```bash
cd metadata_viewer
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

If `python3` is still old, use Homebrew explicitly:

```bash
/opt/homebrew/bin/python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Workflow

1. Click **Choose folder** and select your dataset root (e.g. `data/`).
2. The app scans all nested `jpg` / `jpeg` / `png` / `webp` files and writes **`metadata.csv`** in that folder.
3. Navigate with **← / →** or **A / D** (also **Alt+← / Alt+→**).
4. Draw a polygon around the receipt, then **Save polygon** (JSON in the `box` column).
5. Set **indoor** / **outdoor** and **fingers** / **without_fingers**, then save.

## CSV columns

| Column | Description |
|--------|-------------|
| `path` | Path relative to dataset root |
| `box` | JSON polygon in image pixel coordinates |
| `environment` | `indoor` or `outdoor` |
| `fingers_presence` | `fingers` or `without_fingers` |

Example `box` value:

```json
{"label": "receipt", "shape_type": "polygon", "points": [[120.5, 80.0], ...], "image_width": 960, "image_height": 1280}
```
