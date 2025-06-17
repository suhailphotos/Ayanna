import cv2
import os, shutil
import subprocess, pathlib, uuid, io, tempfile, json
from posed.mediapipe.mpPoseDetect import MediaPipePoseDetector, POSE_CONNECTIONS
from posed.mediapipe.draw import (
    draw_landmarks_and_connections,
    draw_transparent_landmarks,
)

def _encode_qtrle(frame_dir: pathlib.Path, fps: int, size: tuple[int,int]) -> bytes:
    """Feed a PNG sequence to ffmpeg and return MOV bytes with alpha (qtrle)."""
    tmp_mov = frame_dir / f"{uuid.uuid4()}.mov"
    cmd = [
        "ffmpeg",
        "-y",
        "-framerate", str(fps),
        "-i", str(frame_dir / "f_%06d.png"),
        "-c:v", "qtrle",
        "-pix_fmt", "argb",
        str(tmp_mov),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    data = tmp_mov.read_bytes()
    tmp_mov.unlink(missing_ok=True)
    return data

def process_video(
    model_path: str,
    input_bytes: bytes,
    mode: str = "overlay",             # overlay | transparent | both
):
    """
    Returns:
        overlay -> (bytes, None)
        transparent -> (bytes, None)               # RGBA MOV (qtrle)
        both -> (bytes, dict)                      # overlay video + landmarks json
    """
    detector = MediaPipePoseDetector(model_path)

    with tempfile.NamedTemporaryFile(suffix=".mp4") as f_in:
        f_in.write(input_bytes)
        f_in.flush()

        cap = cv2.VideoCapture(f_in.name)
        fps   = cap.get(cv2.CAP_PROP_FPS) or 30
        w,h   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        out_mem   = io.BytesIO()

        # choose output strategy
        if mode == "transparent":
            png_dir = pathlib.Path(tempfile.mkdtemp())  # hold RGBA PNGs
            writer = None
        else:
            four   = cv2.VideoWriter_fourcc(*"mp4v")
            tmp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            writer  = cv2.VideoWriter(tmp_out.name, four, fps, (w, h), isColor=True)

        landmarks_all = []

        frame_idx = 0
        while cap.isOpened():
            ok, frame = cap.read()
            if not ok: break
            ts = int(frame_idx/fps*1000)
            res = detector.detect(frame, ts)
            lms = detector.extract_landmarks(res)
            landmarks_all.append(lms)

            if mode in ("overlay","both"):
                draw_landmarks_and_connections(frame, lms, POSE_CONNECTIONS)

            if mode=="transparent":
                rgba = draw_transparent_landmarks((w, h), lms, POSE_CONNECTIONS)
                cv2.imwrite(str(png_dir / f"f_{frame_idx:06d}.png"), rgba)
            else:
                writer.write(frame)
            frame_idx += 1

        if writer is not None:
            writer.release()
        cap.release()

        if mode == "transparent":
            out_mem.write(_encode_qtrle(png_dir, fps, (w, h)))
            shutil.rmtree(png_dir, ignore_errors=True)
        else:
            with open(tmp_out.name, "rb") as f_vid:
                out_mem.write(f_vid.read())
            os.remove(tmp_out.name)

    out_mem.seek(0)
    landmarks_json = json.dumps(landmarks_all) if mode=="both" else None
    return out_mem.read(), landmarks_json
