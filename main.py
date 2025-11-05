#!/usr/bin/env python3
import io, os, sys, argparse, math
from pathlib import Path
import replicate, requests
from PIL import Image

IMAGE_PATH = Path("./in/my_face.jpg")
OUT_DIR = Path("./out")
MODEL_VERSION = "bf913bc90e1c44ba288ba3942a538693b72e8cc7df576f3beebe56adc0a92b86"

# neutrale Werte
PITCH = 0.0
SKIP_EXISTING = True

def ensure_env():
    if not os.getenv("REPLICATE_API_TOKEN"):
        print("ERROR: REPLICATE_API_TOKEN not set.", file=sys.stderr)
        sys.exit(1)
    if not IMAGE_PATH.exists():
        print(f"ERROR: input image not found: {IMAGE_PATH}", file=sys.stderr)
        sys.exit(1)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

def clamp(v, lo, hi): return max(lo, min(hi, v))

def run_expression_editor(image_input, pupil_x, pupil_y, rotate_yaw, rotate_pitch):
    payload = {
        "image": image_input,
        "pupil_x": float(clamp(pupil_x, -15, 15)),
        "pupil_y": float(clamp(pupil_y, -15, 15)),
        "rotate_yaw": float(clamp(rotate_yaw, -20, 20)),
        "rotate_pitch": float(clamp(rotate_pitch, -20, 20)),
    }
    return replicate.run(f"fofr/expression-editor:{MODEL_VERSION}", input=payload)

def fetch_bytes(maybe_url_or_filelike):
    if hasattr(maybe_url_or_filelike, "read"):
        return maybe_url_or_filelike.read()
    if isinstance(maybe_url_or_filelike, str):
        r = requests.get(maybe_url_or_filelike, timeout=120); r.raise_for_status()
        return r.content
    raise TypeError("Unsupported output type from Replicate")

def save_as_jpg(raw: bytes, dest: Path):
    img = Image.open(io.BytesIO(raw))
    if img.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    else:
        img = img.convert("RGB")
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, format="JPEG", quality=95, optimize=True)

def main():
    parser = argparse.ArgumentParser(description="360° pupil sweep (JPG, no resize).")
    parser.add_argument("--step", type=int, default=30, help="Grad-Schrittweite (1–360, Standard 10)")
    args = parser.parse_args()
    if args.step <= 0 or args.step > 360:
        print("ERROR: --step muss 1..360 sein.", file=sys.stderr)
        sys.exit(1)

    ensure_env()
    angles = list(range(0, 360, args.step))

    print("initializing model… please wait (first call may take up to ~30s)")

    for deg in angles:
        fname = f"{deg}.jpg"
        target = OUT_DIR / fname
        if SKIP_EXISTING and target.exists():
            print(f"[skip] {target}")
            continue

        # Kreispfad: 0° rechts, 90° unten, 180° links, 270° oben
        rad = math.radians(deg)
        pupil_x = 15 * math.cos(rad)   # rechts/links
        pupil_y = 15 * math.sin(rad)   # oben/unten
        rotate_yaw = (pupil_x / 15.0) * 10.0
        rotate_pitch = -(pupil_y / 15.0) * 10.0

        try:
            with IMAGE_PATH.open("rb") as f:
                outputs = run_expression_editor(
                    image_input=f,
                    pupil_x=pupil_x,
                    pupil_y=pupil_y,
                    rotate_yaw=rotate_yaw,
                    rotate_pitch=rotate_pitch,
                )
            if not outputs:
                print(f"[warn] no output for {deg}°"); continue
            raw = fetch_bytes(outputs[0])
            save_as_jpg(raw, target)
            print(f"[ok] {target}  (pupil_x={pupil_x:.1f}, pupil_y={pupil_y:.1f})")
        except Exception as e:
            print(f"[error] {deg}°: {e}", file=sys.stderr)

    print(f"Done. Files in: {OUT_DIR.resolve()}")

if __name__ == "__main__":
    main()
