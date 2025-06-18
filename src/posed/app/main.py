import shutil
import os, uuid, io
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from posed.inference.poseDetect import process_video
from email.message import EmailMessage
from email.generator import BytesGenerator

app = FastAPI()

def build_multipart(video: bytes, json_txt: str, boundary: str | None = None) -> tuple[bytes, str]:
    root = EmailMessage()
    root["MIME-Version"] = "1.0"
    root.set_type("multipart/mixed")
    if boundary:
        root.set_boundary(boundary)
    boundary = root.get_boundary()

    # --- Part 1  (video) ---
    part_mov = EmailMessage()
    part_mov.set_type("video/quicktime")
    part_mov["Content-Disposition"] = 'attachment; filename="pose_overlay.mov"'
    # DO NOT override content-transfer-encoding → stays as 'base64'
    part_mov.set_payload(video)      # bytes → auto-base64
    root.attach(part_mov)

    # --- Part 2  (JSON) ---
    part_json = EmailMessage()
    part_json.set_type("application/json; charset=utf-8")
    part_json["Content-Disposition"] = 'attachment; filename="landmarks.json"'
    part_json.set_payload(json_txt, "utf-8")  # 8-bit text
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



