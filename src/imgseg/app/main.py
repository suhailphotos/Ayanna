from fastapi import FastAPI, UploadFile, File
from pathlib import Path
from tempfile import NamedTemporaryFile

from ..inference.segment import remove_bg

app = FastAPI(title="RMBG-2.0 Background-Removal API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/segment")
async def segment(file: UploadFile = File(...)):
    """Accept an image, return path to alpha-matted PNG (on disk for now)."""
    with NamedTemporaryFile(suffix=".png") as tmp:
        tmp.write(await file.read())
        tmp.flush()

        result_img = remove_bg(Path(tmp.name))
        out_path = Path("/tmp") / f"no_bg_{file.filename}"
        result_img.save(out_path)

        return {"result": str(out_path)}
