from typing import Dict, Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np

from pose_types import Landmark2D, PoseFrame


def _to_pixel(lm: Landmark2D, image_size: Tuple[int, int]) -> Tuple[int, int]:
    width, height = image_size
    return int(lm.x * width), int(lm.y * height)


def draw_pose(frame, pose: PoseFrame, highlight: Optional[Dict[str, Tuple[int, int, int]]] = None) -> None:
    if not pose.valid:
        return
    highlight = highlight or {}
    connections = mp.solutions.pose.POSE_CONNECTIONS
    lms = pose.raw_landmarks
    width, height = pose.image_size

    for a, b in connections:
        # Mediapipe connections are enum indices; we map by order in PoseLandmark.
        name_a = mp.solutions.pose.PoseLandmark(a).name.lower()
        name_b = mp.solutions.pose.PoseLandmark(b).name.lower()
        if name_a not in lms or name_b not in lms:
            continue
        lm_a = lms[name_a]
        lm_b = lms[name_b]
        if lm_a is None or lm_b is None:
            continue
        ax, ay = _to_pixel(lm_a, (width, height))
        bx, by = _to_pixel(lm_b, (width, height))
        cv2.line(frame, (ax, ay), (bx, by), (0, 255, 0), 2)

    for name, lm in lms.items():
        if lm is None:
            continue
        x, y = _to_pixel(lm, (width, height))
        color = highlight.get(name, (0, 255, 255))
        cv2.circle(frame, (x, y), 5, color, -1)


def draw_overlay(frame, text_lines, origin=(10, 30)) -> None:
    x, y = origin
    for line in text_lines:
        cv2.putText(frame, line, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        y += 28


def draw_bar(frame, bar_y: float, color=(255, 0, 255)) -> None:
    height, width = frame.shape[:2]
    y = int(bar_y * height)
    cv2.line(frame, (0, y), (width, y), color, 2)


def draw_joint_angles(frame, pose: PoseFrame) -> None:
    if not pose.valid:
        return
    lm = pose.raw_landmarks
    angle_triples = [
        ("left_hip", "left_knee", "left_ankle"),
        ("right_hip", "right_knee", "right_ankle"),
        ("left_shoulder", "left_elbow", "left_wrist"),
        ("right_shoulder", "right_elbow", "right_wrist"),
    ]
    for a, b, c in angle_triples:
        la = lm.get(a)
        lb = lm.get(b)
        lc = lm.get(c)
        if la is None or lb is None or lc is None:
            continue
        angle = _angle_degrees(la, lb, lc)
        x, y = _to_pixel(lb, pose.image_size)
        cv2.putText(frame, f"{int(angle)}", (x + 6, y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)


def _angle_degrees(a: Landmark2D, b: Landmark2D, c: Landmark2D) -> float:
    bax = a.x - b.x
    bay = a.y - b.y
    bcx = c.x - b.x
    bcy = c.y - b.y
    dot = bax * bcx + bay * bcy
    mag_ba = (bax * bax + bay * bay) ** 0.5
    mag_bc = (bcx * bcx + bcy * bcy) ** 0.5
    if mag_ba < 1e-6 or mag_bc < 1e-6:
        return 0.0
    cos_theta = max(-1.0, min(1.0, dot / (mag_ba * mag_bc)))
    return float(np.degrees(np.arccos(cos_theta)))

