import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import os

POSE_MODEL_PATH = "../models/mediapipe/pose_landmarker_heavy.task"
VIDEO_PATH = "../data/raw/videos/ana_sdr.mp4"

OUTPUT_PATH = "../data/processed/ana_sdr_pose_overlay.mp4"

POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),
    (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19), (12, 14),
    (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24), (23, 25), (24, 26),
    (25, 27), (27, 29), (29, 31), (27, 31), (26, 28), (28, 30), (28, 32), (30, 32)
]

# Set up the base options and the PoseLandmarker
base_options = python.BaseOptions(model_asset_path=POSE_MODEL_PATH)

options = vision.PoseLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    num_poses=1,
    min_pose_detection_confidence=0.3,
    min_pose_presence_confidence=0.3,
    min_tracking_confidence=0.3,
    output_segmentation_masks=False
)
detector = vision.PoseLandmarker.create_from_options(options)

# Video capture
cap = cv2.VideoCapture(VIDEO_PATH)

# Get video properties for output
fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fourcc = cv2.VideoWriter_fourcc(*'mp4v')

# Ensure output directory exists
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

# Create VideoWriter object
out = cv2.VideoWriter(OUTPUT_PATH, fourcc, fps, (width, height))

frame_count = 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Convert to RGB as MediaPipe expects
    image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image)
    timestamp_ms = int((frame_count / fps) * 1000)

    detection_result = detector.detect_for_video(mp_image, timestamp_ms)

    # Draw connections/lines between landmarks
    if detection_result.pose_landmarks:
        landmarks = detection_result.pose_landmarks[0]
        for connection in POSE_CONNECTIONS:
            start_idx, end_idx = connection
            if start_idx < len(landmarks) and end_idx < len(landmarks):
                x1 = int(landmarks[start_idx].x * frame.shape[1])
                y1 = int(landmarks[start_idx].y * frame.shape[0])
                x2 = int(landmarks[end_idx].x * frame.shape[1])
                y2 = int(landmarks[end_idx].y * frame.shape[0])
                cv2.line(frame, (x1, y1), (x2, y2), (255,255,255), 2)
        # Draw the dots on top
        for landmark in landmarks:
            x = int(landmark.x * frame.shape[1])
            y = int(landmark.y * frame.shape[0])
            cv2.circle(frame, (x, y), 3, (0,255,0), -1)

    out.write(frame)
    frame_count += 1
    if frame_count % 100 == 0:
        print(f"Processed {frame_count} frames...")

cap.release()
out.release()
print(f"Done! Output saved to {OUTPUT_PATH}")
