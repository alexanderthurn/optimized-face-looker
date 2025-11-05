## Optimized Face Looker 👁️

![Demo GIF placeholder](misc/anim-face.gif)

Create an interactive, circular profile picture that “looks” toward your mouse/finger. Frames are generated with Replicate, then packed into a tiled atlas and displayed efficiently in the browser.

This is an optimized version: instead of shipping many individual images, it generates one large tiled JPG atlas plus a tiny JSON manifest. Fewer requests and better compression make page loads significantly faster.

Combined atlas preview (appears after you run the optimize step):

![Combined atlas](viewer/anim-face.jpg)


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

Put your input image at `in/my_face.jpg` (512×512 recommended).

## Usage

### 1) Generate frames
Default step is 30 degrees (0..330):
```bash
python3 main.py generate --step 30
```

### 2) Build optimized atlas (tiled)
Packs frames into a near-square atlas (default max width 256px; raise this for bigger atlases like 2048):
```bash
python3 main.py optimize --step 30 --max-width 2048
```

This writes to `viewer/`:
- `anim-face.jpg` — the tiled atlas
- `anim-face.json` — manifest with layout (columns, rows, frame size)

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

Or view on GitHub Pages (if enabled for this repo):

- Optimized (atlas): https://alexanderthurn.github.io/optimized-face-looker/
  (Only the optimized viewer is deployed, served from viewer/index.html.)

### Controls and mapping
- Move the mouse (or drag your finger) anywhere on the page; the face rotates to the nearest available frame.
- Angle convention: 0°=right, 90°=up, 180°=left, 270°=down.

### Defaults
- Generation step: `30` degrees (frames at 0,30,60,…,330)
- Atlas max width: `256` px (use a larger value for a more square atlas)
- Outputs: frames in `out/`, optimized atlas and manifest in `viewer/`.

## Project structure
```
in/
  my_face.jpg
out/
  0.jpg, 30.jpg, ... 330.jpg
viewer/
  anim-face.html
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