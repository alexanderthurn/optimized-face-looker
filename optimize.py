#!/usr/bin/env python3
import sys, argparse, json, math
from pathlib import Path
from PIL import Image

OUT_DIR = Path("./out")
VIEWER_DIR = Path("./viewer")
SPRITE_NAME = "anim-face.jpg"
MANIFEST_NAME = "anim-face.json"

def load_frame(path: Path) -> Image.Image:
    img = Image.open(path)
    if img.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        return bg
    return img.convert("RGB")

def main():
    parser = argparse.ArgumentParser(description="Create tiled atlas from out/*.jpg frames and a manifest for the viewer.")
    parser.add_argument("--step", type=int, default=30, help="Angle step width (1–360). Must match generated frames.")
    parser.add_argument("--max-width", type=int, default=256, help="Maximum atlas width in pixels. Frames are downscaled if needed to fit. Default 256.")
    args = parser.parse_args()

    if args.step <= 0 or args.step > 360:
        print("ERROR: --step must be 1..360", file=sys.stderr)
        sys.exit(1)
    if args.max_width <= 0:
        print("ERROR: --max-width must be > 0", file=sys.stderr)
        sys.exit(1)

    angles = list(range(0, 360, args.step))

    frames = []
    for a in angles:
        p = OUT_DIR / f"{a}.jpg"
        if p.exists():
            frames.append(p)
        else:
            print(f"[warn] missing frame: {p}", file=sys.stderr)

    if not frames:
        print(f"ERROR: no frames found in {OUT_DIR.resolve()} for step={args.step}", file=sys.stderr)
        sys.exit(1)

    # Load frames and normalize to consistent size (based on the first frame),
    # then optionally downscale to respect per-frame width if needed to fit max atlas width.
    imgs = [load_frame(p) for p in frames]
    base_w, base_h = imgs[0].size
    normalized = []
    for im in imgs:
        if im.size != (base_w, base_h):
            im = im.resize((base_w, base_h), Image.LANCZOS)
        normalized.append(im)

    # Determine target per-frame dimensions to satisfy max atlas width.
    # Start with original base size; downscale if a single frame is already wider than max_width.
    if base_w > args.max_width:
        target_w = args.max_width
        target_h = int(round(base_h * (target_w / base_w)))
    else:
        target_w = base_w
        target_h = base_h

    # Choose columns to make atlas roughly square, then clamp to max_width
    # Target: columns^2 ≈ frame_count * (frame_height / frame_width)
    ideal_cols = int(round(math.sqrt(len(normalized) * (target_h / target_w))))
    ideal_cols = max(1, min(len(normalized), ideal_cols))
    columns = ideal_cols
    # Enforce max atlas width if necessary
    if columns * target_w > args.max_width:
        columns = max(1, args.max_width // target_w)
    if columns < 1:
        columns = 1

    # Resize to target frame size if needed
    if (target_w, target_h) != (base_w, base_h):
        resized = []
        for im in normalized:
            resized.append(im.resize((target_w, target_h), Image.LANCZOS))
        normalized = resized

    frame_count = len(normalized)
    rows = int(math.ceil(frame_count / columns))
    atlas_w = columns * target_w
    atlas_h = rows * target_h

    sprite = Image.new("RGB", (atlas_w, atlas_h), (255, 255, 255))
    for idx, im in enumerate(normalized):
        row = idx // columns
        col = idx % columns
        x = col * target_w
        y = row * target_h
        sprite.paste(im, (x, y))

    VIEWER_DIR.mkdir(parents=True, exist_ok=True)
    dest = VIEWER_DIR / SPRITE_NAME
    sprite.save(dest, format="JPEG", quality=90, optimize=True)

    manifest = {
        "step": args.step,
        "frameCount": frame_count,
        "frameWidth": target_w,
        "frameHeight": target_h,
        "columns": columns,
        "rows": rows,
        "image": SPRITE_NAME,
    }
    (VIEWER_DIR / MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")

    print(
        f"[ok] wrote {dest.resolve()} and { (VIEWER_DIR / MANIFEST_NAME).resolve() } "
        f"({frame_count} frames, frame={target_w}x{target_h}, atlas={atlas_w}x{atlas_h}, cols={columns}, rows={rows})"
    )

if __name__ == "__main__":
    main()


