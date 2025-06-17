import shutil
import os, uuid, io
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from posed.inference.poseDetect import process_video
from email.message import EmailMessage
from email.generator import BytesGenerator

app = FastAPI()

def build_multipart(video: bytes, json_txt: str, boundary: str | None = None) -> bytes:
    """Return a fully-formed multipart/mixed document (as bytes) plus its boundary."""
    root = EmailMessage()
    root["MIME-Version"] = "1.0"
    root.set_type("multipart/mixed")
    if boundary:
        root.set_boundary(boundary)            # FastAPI already chose one
    boundary = root.get_boundary()             # keep for Content-Type header

    # Part 1 – ProRes MOV
    part_mov = EmailMessage()
    part_mov.set_type("video/quicktime")
    part_mov["Content-Disposition"] = 'attachment; filename="pose_overlay.mov"'
    part_mov.add_header("Content-Transfer-Encoding", "binary")
    part_mov.set_payload(video)                # bytes payload, untouched
    root.attach(part_mov)

    # Part 2 – JSON
    part_json = EmailMessage()
    part_json.set_type("application/json; charset=utf-8")
    part_json["Content-Disposition"] = 'attachment; filename="landmarks.json"'
    part_json.set_payload(json_txt, "utf-8")
    root.attach(part_json)

    buf = io.BytesIO()
    BytesGenerator(buf, mangle_from_=False, maxheaderlen=0).flatten(root)
    buf.seek(0)
    return buf.read(), boundary

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
        body, boundary = build_multipart(video_out, landmarks_json)
        return StreamingResponse(
            io.BytesIO(body),
            media_type=f'multipart/mixed; boundary="{boundary}"'
        )

    media_type = "video/quicktime" if mode=="transparent" else "video/mp4"
    return StreamingResponse(io.BytesIO(video_out), media_type=media_type)


def _multipart_stream(video_bytes: bytes, json_str: str, boundary: str):
    """Yield multipart/mixed chunks so the client receives both assets in one response
    with filenames so any MIME-aware tool can split them out automatically."""

    yield (
        f"--{boundary}\r\n"
        f"Content-Type: video/quicktime\r\n"
        f"Content-Transfer-Encoding: binary\r\n"
        f"Content-Disposition: attachment; filename=\"pose_overlay.mov\"\r\n\r\n"
    ).encode()
    yield video_bytes
    # <-- ensure a clean break between parts
    yield b"\r\n"
    yield (
        f"\r\n--{boundary}\r\n"
        f"Content-Type: application/json\r\n"
        f"Content-Transfer-Encoding: 8bit\r\n"
        f"Content-Disposition: attachment; filename=\"landmarks.json\"\r\n\r\n"
        f"{json_str}\r\n"
        f"--{boundary}--\r\n"
    ).encode()
