import cv2

def draw_landmarks_and_connections(frame, landmarks, connections, landmark_color=(0,255,0), connection_color=(255,255,255)):
    h, w = frame.shape[:2]
    # Draw connections
    for start_idx, end_idx in connections:
        if start_idx < len(landmarks) and end_idx < len(landmarks):
            x1, y1 = int(landmarks[start_idx][0]*w), int(landmarks[start_idx][1]*h)
            x2, y2 = int(landmarks[end_idx][0]*w), int(landmarks[end_idx][1]*h)
            cv2.line(frame, (x1, y1), (x2, y2), connection_color, 2)
    # Draw landmarks
    for x, y, z, vis in landmarks:
        if vis > 0.2:
            cv2.circle(frame, (int(x*w), int(y*h)), 3, landmark_color, -1)
    return frame

def draw_transparent_landmarks(shape, landmarks, connections, landmark_color=(0,255,0,255), connection_color=(255,255,255,255)):
    """Draws landmarks and connections on a transparent (RGBA) image."""
    import numpy as np
    overlay = np.zeros((shape[1], shape[0], 4), dtype=np.uint8)
    h, w = shape[1], shape[0]
    # Draw connections
    for start_idx, end_idx in connections:
        if start_idx < len(landmarks) and end_idx < len(landmarks):
            x1, y1 = int(landmarks[start_idx][0]*w), int(landmarks[start_idx][1]*h)
            x2, y2 = int(landmarks[end_idx][0]*w), int(landmarks[end_idx][1]*h)
            cv2.line(overlay, (x1, y1), (x2, y2), connection_color, 2)
    # Draw landmarks
    for x, y, z, vis in landmarks:
        if vis > 0.2:
            cv2.circle(overlay, (int(x*w), int(y*h)), 3, landmark_color, -1)
    return overlay
