# ───────────────────────────────────────────────────────────────
#  Stable-Diffusion WebUI  •  CUDA 12.6  •  Torch 2.3.0 + cu121
# ───────────────────────────────────────────────────────────────

FROM nvidia/cuda:12.6.2-runtime-ubuntu22.04

# ---- system dependencies ----
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive \
    apt-get install -y --no-install-recommends \
        git python3 python3-pip python3-venv python3-dev \
        build-essential ninja-build \
        libgl1 libc++-dev libc++abi-dev \
        google-perftools libgoogle-perftools4 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ---- TCMalloc for lower CPU RAM usage ----
ENV LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libtcmalloc_minimal.so.4

# ---- Clone AUTOMATIC1111 ----
WORKDIR /workspace
RUN git clone --depth 1 https://github.com/AUTOMATIC1111/stable-diffusion-webui.git

# ---- Patch version pins ----
RUN sed -i 's/^fastapi.*$/fastapi==0.90.1/'  \
        stable-diffusion-webui/requirements_versions.txt && \
    sed -i 's/^pytorch_lightning.*$/pytorch_lightning==1.6.5/' \
        stable-diffusion-webui/requirements_versions.txt && \
    echo "timm" >> stable-diffusion-webui/requirements_versions.txt

# ---- Python deps ----
# 1) keep pip < 24.1 for legacy metadata
RUN python3 -m pip install --upgrade pip==24.0 wheel==0.43.0

# 2) lightweight reqs from the repo
RUN pip install -r stable-diffusion-webui/requirements_versions.txt

# 3) heavy CUDA wheels (torch/vision/audio) for cu121
RUN pip install --no-cache-dir \
        torch==2.3.0+cu121 torchvision==0.18.0+cu121 torchaudio==2.3.0+cu121 \
        --index-url https://download.pytorch.org/whl/cu121

# 4) install xformers compatible with torch 2.3.x
RUN pip install --no-cache-dir xformers==0.0.26.post1

# ---- Model & output bind-mount locations ----
RUN mkdir -p /models/Stable-diffusion /outputs
VOLUME ["/models/Stable-diffusion", "/outputs"]

# ---- runtime ----
EXPOSE 7860
WORKDIR /workspace/stable-diffusion-webui
CMD ["python3", "launch.py", "--listen", "--port", "7860", "--api", "--ckpt-dir", "/models/Stable-diffusion", "--xformers", "--no-half-vae"]
