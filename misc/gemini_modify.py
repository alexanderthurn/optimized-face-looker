from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import argparse
from pathlib import Path

client = genai.Client()

# Parse optional postfix argument
parser = argparse.ArgumentParser()
parser.add_argument(
    "--postfix",
    type=str,
    default="2",
    help="Postfix to append to output filename; pass without leading '_' (e.g., 2)",
)
parser.add_argument(
    "--style",
    type=str,
    default="make him look like a hippie",
    help="Clause to insert into the prompt (e.g., 'make him look like a cowboy')",
)
args = parser.parse_args()
raw_postfix = args.postfix if args.postfix is not None else "2"
normalized_postfix = raw_postfix.lstrip("_")
postfix = f"_{normalized_postfix}" if normalized_postfix else "_2"

raw_style = args.style if args.style is not None else "make him look like a hippie"
style_clause = (raw_style.strip() or "make him look like a hippie")

project_root = Path(__file__).resolve().parent.parent
input_path = project_root / "in" / "my_face.jpg"
output_path = project_root / "in" / f"my_face{postfix}.jpg"

# Base image prompt: "A photorealistic picture of a fluffy ginger cat sitting on a wooden floor, looking directly at the camera. Soft, natural light from a window."
image_input = Image.open(input_path)
text_input = f"""Using the provided image of a portrait of a person, {style_clause}. Ensure the person's face and features remain completely unchanged. Preserve the ratio and stuff. The background has to be white"""

# Generate an image from a text prompt
response = client.models.generate_content(
    model="gemini-2.5-flash-image",
    contents=[text_input, image_input],
)

image_parts = [
    part.inline_data.data
    for part in response.candidates[0].content.parts
    if part.inline_data
]

if image_parts:
    image = Image.open(BytesIO(image_parts[0]))
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    image.save(output_path, format="JPEG")
    image.show()