#!/usr/bin/env python3
import io, os, sys, subprocess, argparse, math
from pathlib import Path
import replicate, requests
from PIL import Image

IN_DIR = Path("./in")
OUT_DIR = Path("./out")
MODEL_VERSION = "bf913bc90e1c44ba288ba3942a538693b72e8cc7df576f3beebe56adc0a92b86"

# neutrale Werte
PITCH = 0.0
SKIP_EXISTING = True

def ensure_env():
    if not os.getenv("REPLICATE_API_TOKEN"):
        print("ERROR: REPLICATE_API_TOKEN not set.", file=sys.stderr)
        sys.exit(1)
    if not IN_DIR.exists():
        print(f"ERROR: input folder not found: {IN_DIR}", file=sys.stderr)
        sys.exit(1)
    has_inputs = any(p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"} for p in IN_DIR.iterdir())
    if not has_inputs:
        print(f"ERROR: no input images found in {IN_DIR} (expected .jpg/.jpeg/.png)", file=sys.stderr)
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

def generate_frames(step: int):
    if step <= 0 or step > 360:
        print("ERROR: --step muss 1..360 sein.", file=sys.stderr)
        sys.exit(1)

    ensure_env()
    angles = list(range(0, 360, step))

    print("initializing model… please wait (first call may take up to ~30s)")

    # Iterate over every image in ./in and generate prefixed frames per input
    input_files = [p for p in IN_DIR.iterdir() if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
    input_files.sort(key=lambda p: p.name)

    for input_path in input_files:
        prefix = input_path.stem  # e.g., my_face, my_face_cowboy
        print(f"\n[gen] source={input_path} → prefix={prefix}_<angle>.jpg")

        for deg in angles:
            fname = f"{prefix}_{deg}.jpg"
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
                with input_path.open("rb") as f:
                    outputs = run_expression_editor(
                        image_input=f,
                        pupil_x=pupil_x,
                        pupil_y=pupil_y,
                        rotate_yaw=rotate_yaw,
                        rotate_pitch=rotate_pitch,
                    )
                if not outputs:
                    print(f"[warn] no output for {prefix} {deg}°"); continue
                raw = fetch_bytes(outputs[0])
                save_as_jpg(raw, target)
                print(f"[ok] {target}  (pupil_x={pupil_x:.1f}, pupil_y={pupil_y:.1f})")
            except Exception as e:
                print(f"[error] {prefix} {deg}°: {e}", file=sys.stderr)

    print(f"Done. Files in: {OUT_DIR.resolve()}")

def run_optimize(step: int, max_width: int):
    # Delegate to optimize.py to keep logic there
    optimize_path = (Path(__file__).parent / "optimize.py").resolve()
    cmd = [sys.executable, str(optimize_path), "--step", str(step), "--max-width", str(max_width)]
    print(f"[run] {' '.join(cmd)}")
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: optimize failed with code {e.returncode}", file=sys.stderr)
        sys.exit(e.returncode)

def main():
    parser = argparse.ArgumentParser(description="Face Looker - generate frames and optimize into an atlas")
    sub = parser.add_subparsers(dest="command", required=True)

    p_gen = sub.add_parser("generate", help="Generate JPG frames into ./out")
    p_gen.add_argument("--step", type=int, default=30, help="Grad-Schrittweite (1–360, Standard 30)")

    p_opt = sub.add_parser("optimize", help="Build tiled atlas (delegates to optimize.py)")
    p_opt.add_argument("--step", type=int, default=30, help="Grad-Schrittweite (1–360, Standard 30)")
    p_opt.add_argument("--max-width", type=int, default=256, help="Maximale Atlasbreite in Pixel (Standard 256)")

    p_all = sub.add_parser("all", help="Generate frames and then optimize into atlas")
    p_all.add_argument("--step", type=int, default=30, help="Grad-Schrittweite (1–360, Standard 30)")
    p_all.add_argument("--max-width", type=int, default=256, help="Maximale Atlasbreite in Pixel (Standard 256)")

    args = parser.parse_args()

    if args.command == "generate":
        generate_frames(step=args.step)
    elif args.command == "optimize":
        run_optimize(step=args.step, max_width=args.__dict__["max_width"])
    elif args.command == "all":
        generate_frames(step=args.step)
        run_optimize(step=args.step, max_width=args.__dict__["max_width"])
    else:
        parser.error("Unknown command")

if __name__ == "__main__":
    main()
