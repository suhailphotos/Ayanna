import shutil
import os, uuid, io
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from posed.inference.poseDetect import process_video

app = FastAPI()


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}

@app.post("/pose",
          responses={
              200: {"content": {"video/mp4": {}, "video/webm": {}, "application/json": {}}}
          })
async def pose_video(
    file: UploadFile = File(..., description="Any H.264 / MP4 clip"),
    mode: str = Query("overlay", enum=["overlay","transparent","both"],
                      description="overlay = original+lines, transparent = RGBA overlay only, both = overlay+landmark JSON")
):
    if not file.filename.lower().endswith((".mp4", ".mov", ".mkv")):
        raise HTTPException(400, "Please upload an MP4/MOV/MKV video.")

    vid_bytes = await file.read()

    video_out, landmarks_json = process_video(
        model_path=os.getenv("POSE_MODEL","./models/mediapipe/pose_landmarker_heavy.task"),
        input_bytes=vid_bytes,
        mode=mode,
    )

    if mode == "both":
        boundary = uuid.uuid4().hex
        return StreamingResponse(
            content=_multipart_stream(video_out, landmarks_json, boundary),
            media_type=f"multipart/mixed; boundary={boundary}"
        )

    media_type = "video/quicktime" if mode=="transparent" else "video/mp4"
    return StreamingResponse(io.BytesIO(video_out), media_type=media_type)


def _multipart_stream(video_bytes: bytes, json_str: str, boundary: str):
    """Yield multipart/mixed chunks so the client receives both assets in one response
    with filenames so any MIME-aware tool can split them out automatically."""

    yield (
        f"--{boundary}\r\n"
        f"Content-Type: video/quicktime\r\n"
        f"Content-Disposition: attachment; filename=\"pose_overlay.mov\"\r\n\r\n"
    ).encode()
    yield video_bytes
    yield (
        f"\r\n--{boundary}\r\n"
        f"Content-Type: application/json\r\n"
        f"Content-Disposition: attachment; filename=\"landmarks.json\"\r\n\r\n"
        f"{json_str}\r\n"
        f"--{boundary}--"
    ).encode()
