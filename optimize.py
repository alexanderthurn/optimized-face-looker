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
    parser.add_argument("--tile-width", type=int, default=None, help="Maximum width per tile/frame. If set, frames are downscaled to this width (keeping aspect).")
    args = parser.parse_args()

    if args.step <= 0 or args.step > 360:
        print("ERROR: --step must be 1..360", file=sys.stderr)
        sys.exit(1)
    if args.max_width <= 0:
        print("ERROR: --max-width must be > 0", file=sys.stderr)
        sys.exit(1)
    if args.tile_width is not None and args.tile_width <= 0:
        print("ERROR: --tile-width must be > 0", file=sys.stderr)
        sys.exit(1)

    angles = list(range(0, 360, args.step))

    # Discover frames grouped by prefix: <prefix>_<angle>.jpg
    # e.g., my_face_0.jpg, my_face_30.jpg, my_face_cowboy_0.jpg, ...
    groups = {}  # prefix -> list of (angle, Path)
    for p in sorted(OUT_DIR.glob("*.jpg")):
        name = p.stem  # e.g., my_face_0
        if "_" not in name:
            # Ignore legacy files like "0.jpg"
            continue
        try:
            prefix, angle_str = name.rsplit("_", 1)
            angle = int(angle_str)
        except ValueError:
            continue
        if angle not in angles:
            continue
        groups.setdefault(prefix, {}).setdefault(angle, p)

    if not groups:
        print(f"ERROR: no prefixed frames found in {OUT_DIR.resolve()} (expected <prefix>_<angle>.jpg)", file=sys.stderr)
        sys.exit(1)

    # Determine ordering of sections (prefixes)
    def section_sort_key(prefix: str):
        # Prefer "my_face" first, then "my_face_*", then others alphabetically
        if prefix == "my_face":
            return (0, "")
        if prefix.startswith("my_face_"):
            return (1, prefix)
        return (2, prefix)

    ordered_prefixes = sorted(groups.keys(), key=section_sort_key)

    # Build a flat list of frames in section order, and capture per-section indices
    flat_paths = []
    sections = []  # { name, startIndex, frameCount }

    # Determine a base frame for size
    first_path = None
    for pr in ordered_prefixes:
        for a in angles:
            if a in groups[pr]:
                first_path = groups[pr][a]
                break
        if first_path:
            break
    if first_path is None:
        print("ERROR: could not determine a base frame for sizing", file=sys.stderr)
        sys.exit(1)
    base_w, base_h = load_frame(first_path).size

    # For each section, collect frames in angle order
    for prefix in ordered_prefixes:
        start_index = len(flat_paths)
        count = 0
        for a in angles:
            path = groups[prefix].get(a)
            if path is None:
                print(f"[warn] missing frame for section '{prefix}' angle {a}", file=sys.stderr)
                continue
            flat_paths.append(path)
            count += 1
        if count > 0:
            sections.append({
                "name": prefix,
                "startIndex": start_index,
                "frameCount": count,
            })

    if not flat_paths:
        print(f"ERROR: no frames found to pack after grouping", file=sys.stderr)
        sys.exit(1)

    # Load frames and normalize to consistent size (based on the first frame),
    # then optionally downscale to respect per-frame width if needed to fit max atlas width.
    imgs = [load_frame(p) for p in flat_paths]
    normalized = []
    for im in imgs:
        if im.size != (base_w, base_h):
            im = im.resize((base_w, base_h), Image.LANCZOS)
        normalized.append(im)

    # Determine target per-frame dimensions.
    # If --tile-width was provided, downscale frames to that width (keeping aspect).
    # Otherwise, leave original size unless a single frame would exceed atlas max-width by itself.
    target_w = base_w
    target_h = base_h
    if args.tile_width is not None:
        if base_w > args.tile_width:
            target_w = args.tile_width
            target_h = int(round(base_h * (target_w / base_w)))
    else:
        if base_w > args.max_width:
            target_w = args.max_width
            target_h = int(round(base_h * (target_w / base_w)))

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

    # Add display names derived from prefix for convenience in the viewer
    def display_name(prefix: str) -> str:
        if prefix == "my_face":
            return "default"
        if prefix.startswith("my_face_"):
            return prefix[len("my_face_"):]
        return prefix

    manifest = {
        "step": args.step,
        "frameCount": frame_count,
        "frameWidth": target_w,
        "frameHeight": target_h,
        "columns": columns,
        "rows": rows,
        "image": SPRITE_NAME,
        "sections": [
            {"name": s["name"], "displayName": display_name(s["name"]), "startIndex": s["startIndex"], "frameCount": s["frameCount"]}
            for s in sections
        ],
    }
    (VIEWER_DIR / MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")

    print(
        f"[ok] wrote {dest.resolve()} and { (VIEWER_DIR / MANIFEST_NAME).resolve() } "
        f"({frame_count} frames, frame={target_w}x{target_h}, atlas={atlas_w}x{atlas_h}, cols={columns}, rows={rows})"
    )

if __name__ == "__main__":
    main()


