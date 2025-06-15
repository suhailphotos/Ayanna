# ────────────────────────────────────────────────────────────────
# CUDA 12.4  •  Ubuntu 22.04  •  Poetry 1.8.2  •  Python 3.10
# ────────────────────────────────────────────────────────────────
FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04

ARG UID=1000
ENV POETRY_VERSION=1.8.2 \
    HF_HOME=/workspace/.cache/huggingface \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC \
    HOME=/workspace

# System deps, Poetry, non-root user
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3-pip git curl tzdata && \
    pip install --no-cache-dir "poetry==$POETRY_VERSION" && \
    useradd -m -u $UID -s /bin/bash imgseg && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --no-interaction --no-ansi

COPY src ./src
RUN mkdir -p /workspace/.cache/huggingface && chown -R imgseg:imgseg /workspace
ENV PYTHONPATH=/workspace/src

USER imgseg
CMD ["uvicorn", "imgseg.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

