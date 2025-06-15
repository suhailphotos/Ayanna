import os
import sys
import requests

api_url = "http://10.29.25.245:8000/segment"

if len(sys.argv) < 3:
    print("Usage: python test_api_call.py <input_image_path> <output_folder>")
    sys.exit(1)

# Expand ~ to home, then get absolute path
image_path = os.path.abspath(os.path.expanduser(sys.argv[1]))
output_folder = os.path.abspath(os.path.expanduser(sys.argv[2]))
image_name = os.path.basename(image_path)
output_filename = f"no_bg_{os.path.splitext(image_name)[0]}.png"
output_path = os.path.join(output_folder, output_filename)

if not os.path.isfile(image_path):
    print(f"Error: Input image not found: {image_path}")
    sys.exit(1)

if not os.path.isdir(output_folder):
    print(f"Error: Output folder does not exist: {output_folder}")
    sys.exit(1)

with open(image_path, "rb") as f:
    files = {"file": (image_name, f, "image/jpeg")}
    response = requests.post(api_url, files=files)

    if response.ok and response.headers.get("content-type", "").startswith("image/png"):
        with open(output_path, "wb") as out:
            out.write(response.content)
        print(f"Saved: {output_path}")
    else:
        print("Error:", response.text)
