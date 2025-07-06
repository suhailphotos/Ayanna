#!/usr/bin/env bash
set -e

export DCCMATE_SUPPRESS_ENV_WARN=1

# --- Only download model if it doesn't exist ---
poetry run python <<'PY'
import os, shutil, urllib.request, pathlib
from dccmate.config import MODEL_PATH, MODEL_NAME
URL = ("https://huggingface.co/TheBloke/"
       "Llama-2-7B-Chat-GGUF/resolve/main/"
       "llama-2-7b-chat.Q4_K_M.gguf")
if not MODEL_PATH.exists():
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {MODEL_NAME} …")
    with urllib.request.urlopen(URL) as r, open(MODEL_PATH, "wb") as f:
        shutil.copyfileobj(r, f)
else:
    print(f"Model {MODEL_PATH} already exists.")
PY

unset DCCMATE_SUPPRESS_ENV_WARN

# --- Dispatch ---
case "$1" in
  chat) exec poetry run dccmate chat --dcc "${DCC_TYPE:-Houdini}" ;;
  api|"") exec poetry run uvicorn dccmate.server:app --host 0.0.0.0 --port 8000 ;;
  *) exec "$@" ;;
esac
