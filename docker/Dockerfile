# ───────── base image ─────────
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VIRTUALENVS_CREATE=false

# — system libs Mediapipe / OpenCV need —
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ───────── dependencies ─────────
# • Poetry preferred (lockfile →  reproducible)  
# • fall back to requirements.txt if user didn’t commit poetry.lock
COPY pyproject.toml poetry.lock* requirements.txt* /app/

RUN set -eux; \
    if [ -f poetry.lock ]; then \
        pip install --upgrade pip poetry && \
        poetry install --no-interaction --no-root; \
    else \
        pip install --upgrade pip && \
        pip install -r requirements.txt; \
    fi

# ───────── project code ─────────
COPY src ./src
ENV PYTHONPATH=/app/src

EXPOSE 8000
CMD ["uvicorn", "posed.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
