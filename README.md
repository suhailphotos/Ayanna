# imgSeg – RMBG-2.0 Background-Removal Service

This subproject provides a FastAPI wrapper around the BRIA `RMBG-2.0` background-removal model.

## Features

- **Model**: BRIA `RMBG-2.0` (BiRefNet + custom dataset)
- **API**: FastAPI endpoints (`/segment`, `/health`)
- **Containerization**: Docker + Docker Compose
- **Environments**: Conda + Poetry support

## Quick Start

### GPU Host (Docker)

```bash
git clone git@github.com:suhailece/ayanna.git
cd ayanna
git worktree add -b imgSeg ../imgSeg origin/main
cd ../imgSeg
docker compose up -d
# API will be available on http://localhost:8000
````

### Local Development (Conda + Poetry)

```bash
mamba env create -f environment.yml
conda activate imgseg
poetry install
poetry run uvicorn imgseg.app.main:app --reload
```

## API Endpoints

* `GET /health` — returns status OK
* `POST /segment` — accepts form-data with image file (`file`), returns JSON with the path to the processed PNG:

  ```json
  { "result": "/tmp/no_bg_<filename>.png" }
  ```

## CI / Publishing Cheat Sheet

| Goal                    | Command                                                                             |
| ----------------------- | ----------------------------------------------------------------------------------- |
| **Update dependencies** | `poetry add <pkg>`                                                                  |
| **Freeze requirements** | `poetry export -f requirements.txt -o requirements.txt --without-hashes`            |
| **Build & push Docker** | `docker build -t suhailece/imgseg:latest -f docker/Dockerfile . && docker push ...` |
| **Publish to PyPI**     | `poetry build && poetry publish -r pypi`                                            |

```

*Last updated: 2025-06-14*

```

