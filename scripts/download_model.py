#!/usr/bin/env python
"""
Fetch a GGUF model and place it in $NEBULA_AI_MODELS/dccmate/.

Usage
-----
poetry run python scripts/download_model.py \
    [--model llama-2-7b-chat.Q4_K_M.gguf] \
    [--url  https://…/llama-2-7b-chat.Q4_K_M.gguf]
"""
from __future__ import annotations
import argparse, shutil, urllib.request, tempfile
from pathlib import Path
from dccmate.config import MODEL_PATH, MODEL_NAME

HF_URL = (
    "https://huggingface.co/TheBloke/"
    "Llama-2-7B-Chat-GGUF/resolve/main/"
    "llama-2-7b-chat.Q4_K_M.gguf"
)

def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as r, tempfile.NamedTemporaryFile(
        "wb", delete=False, dir=dest.parent
    ) as tmp:
        shutil.copyfileobj(r, tmp)
        tmp_path = Path(tmp.name)
    tmp_path.replace(dest)  # atomic move

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument("--url",   default=HF_URL)
    args = parser.parse_args()

    target = MODEL_PATH.parent / args.model
    if target.exists():
        print(f"✔ Model already present → {target}")
        return

    print(f"⬇ Downloading model to {target} …")
    download(args.url, target)
    print("✅ Done.")

if __name__ == "__main__":
    main()
