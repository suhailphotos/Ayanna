FROM nvidia/cuda:12.6.2-devel-ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    POETRY_VERSION=2.1.3 \
    POETRY_VIRTUALENVS_CREATE=false \
    CMAKE_ARGS="-DGGML_CUDA=on" \
    GGML_CUDA=1 \
    FORCE_CMAKE=1

ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH}

# ── system deps ────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.12 python3.12-dev python3.12-venv python3-pip \
        build-essential git cmake ninja-build curl             \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3.12 /usr/local/bin/python
RUN ln -sf /usr/local/cuda/targets/x86_64-linux/lib/stubs/libcuda.so \
           /usr/local/cuda/lib64/libcuda.so       && \
    ln -sf /usr/local/cuda/targets/x86_64-linux/lib/stubs/libcuda.so \
           /usr/local/cuda/lib64/libcuda.so.1

# ② build & install deps (unchanged)
RUN python -m pip install --break-system-packages "numpy<2" "poetry==$POETRY_VERSION"
WORKDIR /app
COPY pyproject.toml poetry.lock* ./
COPY src ./src
RUN poetry install --only main --no-interaction

# ③ —–– **now** delete the stub so the real driver wins at runtime
RUN rm /usr/local/cuda/lib64/libcuda.so /usr/local/cuda/lib64/libcuda.so.1

# ④ keep the rest (entrypoint, expose, etc.)
ENV NEBULA_AI_MODELS=/mnt/ai/models 

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
