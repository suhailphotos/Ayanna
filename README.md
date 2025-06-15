# imgSeg — Modular Image Segmentation API (BRIA RMBG-2.0)

**imgSeg** is a production-ready, containerized API for image background removal using the [BRIA RMBG-2.0](https://huggingface.co/briaai/RMBG-2.0) model (Hugging Face, gated access). Designed for VFX, post-production, and creative automation workflows.

> This project is part of the [Ayanna](https://github.com/suhailece/ayanna) platform, structured for easy extension and plug-and-play support of additional models.

---

## Features

* **API-first:** Deployable as a FastAPI microservice (Docker or Conda/Poetry)
* **Plug-and-Play:** Modular design to swap or fine-tune segmentation/matting models
* **GPU-ready:** Optimized for NVIDIA CUDA environments
* **Reproducible:** All dependencies and environments are fully specified
* **Demonstrates:** Practical model integration for production pipelines in VFX/data-centric teams

---

## Model Details

* **Default model:** [BRIA RMBG-2.0 (Hugging Face)](https://huggingface.co/briaai/RMBG-2.0)
* **Note:** This model is **gated**—you must request permission on Hugging Face and set your `HF_TOKEN` in `.env` for access.
* **Fine-tuning:** The framework supports adding your own checkpoints and fine-tuning via `src/imgseg/train/`.

---

## Project Layout

```
imgSeg/
├── data/           # Datasets (not required for inference)
│   ├── processed/
│   └── raw/
├── docker/
│   └── Dockerfile
├── docker-compose.yml
├── environment.yml
├── images/         # Input/output test images (not used by API)
├── models/         # Model weights/checkpoints
│   └── rmbg2.0/
├── notebooks/      # Research & analysis
├── src/
│   └── imgseg/
│       ├── app/
│       │   └── main.py         # FastAPI app
│       ├── inference/
│       │   └── segment.py      # Model loading/inference
│       └── train/
│           └── train.py        # Fine-tuning entrypoint (stub)
├── tests/          # Example/test clients
│   └── rmBg.py     # Example: remote API call
├── .env            # Secrets (.gitignored): Hugging Face token, model/data paths
├── requirements.txt
├── pyproject.toml
└── README.md
```

* **Model files/cache** are mounted into the container using Docker Compose, typically at `/mnt/ai/models` (see `docker-compose.yml` for overrides).
* **Results**: The API streams output PNGs; no files persist inside the container.

---

## Quick Start

### **1. Setup**

**Clone and configure:**

```sh
git clone git@github.com:suhailece/ayanna.git
cd ayanna
git worktree add -b imgSeg ../imgSeg origin/main
cd ../imgSeg

# .env example (see below)
cp .env.example .env
# Edit your HF_TOKEN in .env after requesting model access on Hugging Face
```

**Edit `.env` for your Hugging Face token:**

```
HF_TOKEN=hf_xxx...
```

### **2. Build and Run (Docker)**

```sh
docker compose up -d  # API available on port 8000
```

### **3. Local Dev (Conda + Poetry)**

```sh
conda env create -f environment.yml
conda activate imgseg
poetry config virtualenvs.create false
poetry install --no-interaction
```

---

## API Usage

* **GET `/health`** — quick status check (`{"status": "ok"}`)
* **POST `/segment`** — send an image (`file` in `form-data`), receive a processed PNG (alpha-matted, streamed directly).

**Example:**

```sh
curl -F "file=@/path/to/image.jpg" http://localhost:8000/segment --output no_bg_image.png
```

**Python client example (see `tests/rmBg.py`):**

```python
import os, requests, sys

api_url = "http://<host>:8000/segment"
image_path = os.path.expanduser("~/Desktop/your.jpg")
output_path = os.path.expanduser("~/Desktop/no_bg_your.png")

with open(image_path, "rb") as f:
    files = {"file": (os.path.basename(image_path), f, "image/jpeg")}
    response = requests.post(api_url, files=files)
    if response.ok and response.headers.get("content-type", "").startswith("image/png"):
        with open(output_path, "wb") as out:
            out.write(response.content)
```

---

## Fine-tuning / Training

* **Fine-tuning code** is stubbed in `src/imgseg/train/train.py`
* Designed to integrate PEFT/LoRA or custom pipelines.
* Place your custom models or weights in `models/` and update `inference/segment.py` as needed.

---

## Environment & Model Storage

* **Default model cache**: `/mnt/ai/models/huggingface` (see `.env` and `docker-compose.yml`)
* All environment variables are managed via `.env` (never commit secrets).
* **You may need to adjust data/model paths** for your setup.

---

## Security & Access

* Model download requires a Hugging Face account **with permission for [BRIA RMBG-2.0](https://huggingface.co/briaai/RMBG-2.0)**
* API requires no authentication for local/network use by default; add auth middleware for production.

---

## TL;DR

* **imgSeg** is a plug-and-play FastAPI microservice for background removal using [BRIA RMBG-2.0](https://huggingface.co/briaai/RMBG-2.0)
* Built for VFX/AI pipelines: ready to fine-tune, swap models, or serve as a template
* Requires gated Hugging Face access and a valid token in `.env`
* Runs on Docker (preferred) or locally with Conda/Poetry
* See `tests/rmBg.py` for end-to-end API example

---

*For integration questions or to discuss ML deployment best practices, open an issue or contact via the main Ayanna repo.*

