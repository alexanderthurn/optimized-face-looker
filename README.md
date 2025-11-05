## Optimized Face Looker 👁️

Create an interactive, circular profile picture that “looks” toward your mouse/finger. Frames are generated with Replicate, then packed into a tiled atlas and displayed efficiently in the browser.

<div align="center">
<table border="0">
<tr>
 <td><img src="in/my_face.jpg" alt="Input" height="256" /></td>
 <td align="center" style="padding: 0 12px; font-size: 28px; vertical-align: middle;">→</td>
 <td><img src="viewer/anim-face.jpg" alt="Combined atlas preview" height="256" /></td>
 <td align="center" style="padding: 0 12px; font-size: 28px; vertical-align: middle;">→</td>
 <td><img src="misc/anim-face.gif" alt="Demo GIF placeholder" height="256" /></td>
</tr>
</table>
</div>

This is an optimized version: instead of shipping many individual images, it generates one large tiled JPG atlas plus a tiny JSON manifest. Fewer requests and better compression make page loads significantly faster.

[Live Demo](https://alexanderthurn.github.io/optimized-face-looker/)


## Requirements

- Python 3.9+
- [Replicate API account](https://replicate.com/) and API token
- Python packages: `replicate`, `requests`, `Pillow`

Quick install (recommended):
```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install replicate requests Pillow
```

Set your Replicate token:
```bash
export REPLICATE_API_TOKEN=your_token_here
```

Put your input images in `in/` (512×512 recommended), e.g. `my_face.jpg`, `my_face_cowboy.jpg`, `my_face_hippie.jpg`.

## Usage

### 1) Generate frames
Generates frames for every image in `in/` (`.jpg/.jpeg/.png`). Each input creates prefixed frames like `my_face_0.jpg`, `my_face_30.jpg`, …
Default step is 30 degrees (0..330):
```bash
python3 main.py generate --step 30
```

### 2) Build optimized atlas (tiled)
Packs all generated frames into one atlas. You can:
- limit the overall atlas width with `--max-width` (default 256)
- scale each tile (frame) with `--tile-width` (e.g., 128 to make each tile 128px wide; height is scaled proportionally)
The manifest includes sections for each input (prefix):
```bash
# overall width cap and per-tile scaling
python3 main.py optimize --step 30 --max-width 2048 --tile-width 128
```

This writes to `viewer/`:
- `anim-face.jpg` — the tiled atlas
- `anim-face.json` — manifest with layout (columns, rows, frame size) and `sections` (e.g., `default`, `cowboy`, `hippie`)

### 3) Do both in one step
```bash
python3 main.py all --step 30 --max-width 2048
```

### View in the browser
Open the viewer page:
- `viewer/index.html`

Start a simple dev server (recommended) from project root:
```bash
python3 -m http.server 8000
# then visit http://localhost:8000/viewer/
```

### Controls and mapping
- Move the mouse (or drag your finger) anywhere on the page; the face rotates to the nearest available frame.
- Double-click (desktop) or double-tap (mobile) to switch expression/section (wraps around).
- Angle convention: 0°=right, 90°=up, 180°=left, 270°=down.

### Defaults
- Generation step: `30` degrees (frames at 0,30,60,…,330)
- Atlas max width: `256` px (use a larger value for a more square atlas)
- Outputs: frames in `out/` as `<prefix>_<angle>.jpg` (e.g., `my_face_0.jpg`), optimized atlas and manifest in `viewer/`.

## Project structure
```
in/
  my_face.jpg
  my_face_cowboy.jpg
  my_face_hippie.jpg
out/
  my_face_0.jpg, my_face_30.jpg, ... 330.jpg
  my_face_cowboy_0.jpg, ...
  my_face_hippie_0.jpg, ...
viewer/
  index.html
  anim-face.jpg
  anim-face.json
main.py
optimize.py
```

## Troubleshooting
- Ensure `REPLICATE_API_TOKEN` is set: `echo $REPLICATE_API_TOKEN`
- Missing frames? Re-run `python3 main.py generate --step 30`
- Atlas looks like a tall column? Increase `--max-width` (e.g., 2048) and re-run optimize/all.

## 🙏 Credits

- Inspiration: This project is based on the great work of [kylan02](https://github.com/kylan02/face_looker). Huge thanks for the idea and approach.
- Face generation powered by [Replicate](https://replicate.com/)
- Uses [fofr/expression-editor](https://replicate.com/fofr/expression-editor) model
- Created with ❤️ by Open Source Fans

## License

MIT - feel free to use in personal and commercial projects!
 
## Optional: Modify portrait with Gemini

Create a stylized variant of `in/my_face.jpg` using Google's Gemini, while keeping facial features unchanged. The result is saved as a JPEG in `in/my_face_{postfix}.jpg`.

Requirements:
- Google AI Studio API key (`GOOGLE_API_KEY` environment variable)
- Python packages: `google-genai`, `Pillow`

Install (once):
```bash
pip install google-genai Pillow
```

Default (style: "make him look like a hippie", postfix `2`):
```bash
python3 misc/gemini_modify.py
# writes in/my_face_2.jpg
```

Custom style and postfix (pass postfix without the underscore):
```bash
python3 misc/gemini_modify.py --style "make him look like a cowboy" --postfix 3
# writes in/my_face_3.jpg
```

Notes:
- Postfix is normalized to start with a single underscore (e.g., `--postfix 7` → `my_face_7.jpg`).
- Output is always saved as JPEG.