# Stable Diffusion WebUI (AUTOMATIC1111) Dockerized Setup

## Project Structure and Setup

* This repository uses [git worktree](https://git-scm.com/docs/git-worktree) and [git subtree](https://git-scm.com/docs/git-subtree) to organize different branches and external codebases efficiently.
* The AUTOMATIC1111 Stable Diffusion WebUI source is added as a **subtree** in a dedicated worktree branch (`sD`). Example layout:

```bash
repo-root/
├── ayanna/     # main repo (main branch)
├── sD/        # worktree for branch 'sD'
├── deepFake/  # worktree for branch 'deepFake'
```

* To add AUTOMATIC1111 as a subtree, use:

  ```bash
  git subtree add --prefix=auto1111 https://github.com/AUTOMATIC1111/stable-diffusion-webui.git master --squash
  ```
* To pull updates from upstream AUTOMATIC1111:

  ```bash
  git subtree pull --prefix=auto1111 https://github.com/AUTOMATIC1111/stable-diffusion-webui.git master --squash
  ```

---

## Docker Image Build Instructions

* The Dockerfile for building the Stable Diffusion WebUI image can be found at:

  ```bash
  <repo-root>/docker/auto1111/Dockerfile
  ```

  *(Replace `<repo-root>` with your clone location). Eg: `/mnt/ai/projects/sD/docker/auto1111/Dockerfile`*

### Example Dockerfile Overview

```yml
FROM nvidia/cuda:12.6.2-runtime-ubuntu22.04

# System dependencies
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive \
    apt-get install -y --no-install-recommends \
        git python3 python3-pip python3-venv python3-dev \
        build-essential ninja-build \
        libgl1 libc++-dev libc++abi-dev \
        google-perftools libgoogle-perftools4 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

ENV LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libtcmalloc_minimal.so.4

WORKDIR /workspace
RUN git clone --depth 1 https://github.com/AUTOMATIC1111/stable-diffusion-webui.git

# Patch pinned versions
RUN sed -i 's/^fastapi.*$/fastapi==0.90.1/'  \
        stable-diffusion-webui/requirements_versions.txt && \
    sed -i 's/^pytorch_lightning.*$/pytorch_lightning==1.6.5/' \
        stable-diffusion-webui/requirements_versions.txt && \
    echo "timm" >> stable-diffusion-webui/requirements_versions.txt

# Install python deps
RUN python3 -m pip install --upgrade pip==24.0 wheel==0.43.0
RUN pip install -r stable-diffusion-webui/requirements_versions.txt
RUN pip install --no-cache-dir \
        torch==2.3.0+cu121 torchvision==0.18.0+cu121 torchaudio==2.3.0+cu121 \
        --index-url https://download.pytorch.org/whl/cu121
RUN pip install --no-cache-dir xformers==0.0.26.post1

# Model & output bind-mount locations
RUN mkdir -p /models/Stable-diffusion /outputs
VOLUME ["/models/Stable-diffusion", "/outputs"]

EXPOSE 7860
WORKDIR /workspace/stable-diffusion-webui
CMD ["python3", "launch.py", "--listen", "--port", "7860", "--api", "--ckpt-dir", "/models/Stable-diffusion", "--xformers", "--no-half-vae"]
```

---

## Hardware & Software Requirements

* NVIDIA GPU (Ampere or newer recommended; 4GB+ VRAM minimum)
* Host system drivers for CUDA 12.6
* Docker Engine 20.10+
* [nvidia-docker](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) runtime installed
* Linux (recommended for best compatibility)
* 8GB+ system RAM (recommended)
* Storage for models and generated outputs

---

## Notes on Dependencies and Fixes

* **TCMalloc** is preloaded for lower RAM usage (see `LD_PRELOAD` in Dockerfile)
* `libglib2.0-0` is added to support OpenCV (`cv2`) runtime dependencies
* Pinned pip to <24.1 due to legacy metadata requirements with AUTOMATIC1111
* Patched FastAPI and PyTorch Lightning versions for compatibility
* **xformers** installed using version `0.0.26.post1` (required for PyTorch 2.3.x)
* CUDA toolkit, PyTorch, and TorchAudio are installed via official NVIDIA/PyTorch wheels for cu121

---

## Building the Docker Image

From your Dockerfile folder:

```bash
docker build --no-cache -t suhailphotos/sdwebui:cuda12.6-torch2.3-xf26 .
```

You may push your image to a registry (optional):

```bash
docker push suhailphotos/sdwebui:cuda12.6-torch2.3-xf26
```

---

## Running with Docker Compose

Example `docker-compose.yml`:

```yml
services:
  sdwebui:
    image: suhailphotos/sdwebui:cuda12.6-torch2.3-xf26
    container_name: sdwebui
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
    volumes:
      - /path/to/your/models:/models/Stable-diffusion
      - /path/to/your/outputs:/outputs
    ports:
      - "7860:7860"
    networks:
      - everest
    restart: unless-stopped

networks:
  everest:
    external: true
```

Replace `/path/to/your/models` and `/path/to/your/outputs` with your actual model and output directories.

---

## Connecting to Open Web UI

If you would like to access the Stable Diffusion API via Open Web UI (OpenWebUI), see [OPENWEBUI.md](./OPENWEBUI.md) for detailed instructions on integrating with your SD container.

---

