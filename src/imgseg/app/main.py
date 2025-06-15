from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from ..inference.segment import remove_bg

app = FastAPI(title="RMBG-2.0 Background-Removal API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/segment")
async def segment(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
):
    try:
        # Save upload to temp file
        with NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(await file.read())
            tmp.flush()
            temp_path = tmp.name

        # Process and save result as PNG to another temp file
        out_path = f"/tmp/no_bg_{uuid4().hex}.png"
        result_img = remove_bg(Path(temp_path))
        result_img.save(out_path, format="PNG")

        import os
        os.remove(temp_path)  # Remove uploaded temp file immediately

        # Schedule output PNG for deletion after response is sent
        if background_tasks is not None:
            background_tasks.add_task(os.remove, out_path)

        return FileResponse(out_path, media_type="image/png", filename="no_bg.png")
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
