#!/usr/bin/env python3
import sys, argparse
from pathlib import Path
from PIL import Image

OUT_DIR = Path("./out")
VIEWER_DIR = Path("./viewer")
SPRITE_NAME = "optimized.jpg"

def load_frame(path: Path) -> Image.Image:
    img = Image.open(path)
    if img.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        return bg
    return img.convert("RGB")

def main():
    parser = argparse.ArgumentParser(description="Create horizontal sprite from out/*.jpg frames.")
    parser.add_argument("--step", type=int, default=30, help="Angle step width (1–360). Must match generated frames.")
    args = parser.parse_args()

    if args.step <= 0 or args.step > 360:
        print("ERROR: --step must be 1..360", file=sys.stderr)
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

    # Load all frames and ensure consistent size by adopting the first one's size
    imgs = [load_frame(p) for p in frames]
    base_w, base_h = imgs[0].size
    normalized = []
    for i, im in enumerate(imgs):
        if im.size != (base_w, base_h):
            im = im.resize((base_w, base_h), Image.LANCZOS)
        normalized.append(im)

    # Compose horizontally
    total_w = base_w * len(normalized)
    sprite = Image.new("RGB", (total_w, base_h), (255, 255, 255))
    x = 0
    for im in normalized:
        sprite.paste(im, (x, 0))
        x += base_w

    VIEWER_DIR.mkdir(parents=True, exist_ok=True)
    dest = VIEWER_DIR / SPRITE_NAME
    sprite.save(dest, format="JPEG", quality=90, optimize=True)
    print(f"[ok] wrote {dest.resolve()}  ({len(normalized)} frames, frame={base_w}x{base_h}, width={total_w})")

if __name__ == "__main__":
    main()


