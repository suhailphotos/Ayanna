# Use official Python image (slim to keep it light)
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app

# Copy only poetry config and install poetry first (better cache usage)
COPY pyproject.toml poetry.lock ./

# Install Poetry
RUN pip install --upgrade pip && pip install poetry

# Copy your project code into the image
COPY src ./src

# Install project dependencies (no dev deps for prod image)
RUN poetry install --no-interaction --no-ansi --only main

# Set env variables (these can be overridden by docker-compose or at runtime)
ENV PYTHONUNBUFFERED=1 \
    DATASET=/app/data \
    MODELS_PATH=/app/models

# Make sure dataset/models folders exist
RUN mkdir -p /app/data/raw /app/models

# Expose container port
EXPOSE 8000

# Start server (host 0.0.0.0 for Docker, app is in src/rndforest/app/main.py)
CMD ["poetry", "run", "uvicorn", "src.rndforest.app.main:app", "--host", "::", "--port", "8000"]
