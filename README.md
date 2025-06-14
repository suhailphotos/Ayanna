# imgSeg — Modular Image Segmentation API (RMBG-2.0)

**imgSeg** is a modular, container-ready API for background removal and image segmentation. The project wraps BRIA RMBG-2.0 as a FastAPI service and is designed for plug-and-play support of additional models.

> **This project is a submodule of the [Ayanna](https://github.com/suhailece/ayanna) workspace. All stable packages are published via the Ayanna main branch. Each subproject (like imgSeg) lives on its own worktree branch for isolated development and experimentation.**

---

## Project Objective

* Provide a production-ready, API-first template for deploying and experimenting with image segmentation/matting models
* Structure the codebase for easy extension to new models (future: "plug and run")
* Serve as an example for organizing research/deployment code in an ML platform context (Ayanna)
* Fully reproducible and portable (Docker, Poetry, Conda)

---

## Folder Structure

```
imgSeg/
├── README.md                # this file
├── data/                    # datasets (raw, processed)
│   ├── processed/
│   └── raw/
├── docker/
│   ├── .dockerignore
│   └── Dockerfile
├── docker-compose.yml       # (future: multi-service setups)
├── environment.yml          # Conda environment for GPU dev
├── models/                  # pre-trained/fine-tuned model weights
│   └── rmbg2.0/
├── notebooks/               # research, model analysis, quick tests
├── poetry.lock
├── pyproject.toml           # Poetry project configuration
├── requirements.txt         # pip requirements (for Docker/CI)
├── scripts/                 # utility scripts (future: data, eval, etc.)
└── src/
    └── imgseg/              # project code (import as ayanna.imgseg or imgseg)
        ├── __init__.py
        ├── app/             # FastAPI app
        │   └── main.py
        ├── inference/       # model inference wrappers
        │   └── segment.py
        └── train/           # training/fine-tuning logic
            └── train.py
```

---

## Quick Start

### GPU Host (Docker)

```bash
git clone git@github.com:suhailece/ayanna.git
cd ayanna
git worktree add -b imgSeg ../imgSeg origin/main
cd ../imgSeg
docker compose up -d  # API runs on :8000
```

### Local Dev (Conda + Poetry)

```bash
# create or re-create the env
conda env create -f environment.yml    # or `conda env update -f …` to update

# activate
conda activate imgseg

# install project deps into that env via Poetry
poetry config virtualenvs.create false
poetry install --no-interaction
```

---

## API Usage

* **GET /health** — status check
* **POST /segment** — accepts an image file (PNG/JPEG) via `form-data` field `file`, returns a JSON path to the alpha-matted PNG result.

Example request:

```bash
curl -F "file=@image.jpg" http://localhost:8000/segment
```

Example response:

```json
{ "result": "/tmp/no_bg_image.jpg" }
```

---

## CI & Publishing Cheat Sheet

| Goal                    | Command                                                                          |
| ----------------------- | -------------------------------------------------------------------------------- |
| **Update dependencies** | `poetry add opencv-python` *(writes lock)*                                       |
| **Freeze requirements** | `poetry export -f requirements.txt -o requirements.txt --without-hashes`         |
| **Build & push Docker** | `docker build -t suhailece/imgseg:0.2 -f docker/Dockerfile . && docker push ...` |
| **Publish to PyPI**     | `poetry build && poetry publish`                                                 |

Minimal GitHub Actions snippet:

```yaml
- uses: actions/checkout@v4
- uses: conda-incubator/setup-miniconda@v3
  with:
    environment-file: environment.yml
    activate-environment: imgseg
- run: pip install poetry
- run: poetry install --no-root
- run: poetry run pytest         # (add tests when ready)
- run: docker build -t suhailece/imgseg:${{ github.sha }} -f docker/Dockerfile .
- run: echo ${{ secrets.DOCKER_PWD }} | docker login -u suhailece --password-stdin
- run: docker push suhailece/imgseg:${{ github.sha }}
```

---

## Development Status

* **Current phase:** In development / research.
* **Goal:** Make segmentation model plug-and-play, standardize serving workflow, and provide example fine-tuning pipelines.
* **Namespace:** To be published as `ayanna.imgseg` once stable.

---

*For more context, see the Ayanna root README or open an issue to discuss ML deployment standards.*

