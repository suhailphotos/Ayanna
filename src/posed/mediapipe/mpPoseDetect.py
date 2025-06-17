import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
import os

POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10), (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21),
    (17, 19), (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24), (23, 25), (24, 26), (25, 27), (27, 29),
    (29, 31), (27, 31), (26, 28), (28, 30), (28, 32), (30, 32)
]

class MediaPipePoseDetector:
    def __init__(self, model_path):
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.3,
            min_pose_presence_confidence=0.3,
            min_tracking_confidence=0.3,
            output_segmentation_masks=False
        )
        self.detector = vision.PoseLandmarker.create_from_options(options)

    def detect(self, frame, timestamp_ms):
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image)
        detection_result = self.detector.detect_for_video(mp_image, timestamp_ms)
        return detection_result

    def extract_landmarks(self, detection_result):
        """Returns a list of (x, y, z, visibility) tuples for each landmark."""
        if not detection_result.pose_landmarks:
            return []
        return [
            (
                lm.x, lm.y, getattr(lm, 'z', 0.0), getattr(lm, 'visibility', 1.0)
            )
            for lm in detection_result.pose_landmarks[0]
        ]
