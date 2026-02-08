import time
from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np

from geometry import distance_2d, angle_degrees
from pose_types import Landmark2D, PoseFrame


@dataclass
class CalibrationResult:
    top_elbow_angle: float
    shoulder_y_top: float
    hip_y_top: float
    torso_length: float


class PassiveCalibrator:
    def __init__(self, duration_seconds: float = 3.0):
        self.duration_seconds = duration_seconds
        self._start_time: Optional[float] = None
        self._elbow_angles = []
        self._shoulder_ys = []
        self._hip_ys = []
        self._torso_lengths = []

    def reset(self) -> None:
        self._start_time = None
        self._elbow_angles.clear()
        self._shoulder_ys.clear()
        self._hip_ys.clear()
        self._torso_lengths.clear()

    def update(self, pose: PoseFrame) -> Optional[CalibrationResult]:
        if not pose.valid:
            return None
        if self._start_time is None:
            self._start_time = time.time()

        lm = pose.raw_landmarks
        required = [
            "left_shoulder",
            "right_shoulder",
            "left_elbow",
            "right_elbow",
            "left_wrist",
            "right_wrist",
            "left_hip",
            "right_hip",
        ]
        if any(lm.get(k) is None for k in required):
            return None

        left_elbow_angle = angle_degrees(lm["left_shoulder"], lm["left_elbow"], lm["left_wrist"])
        right_elbow_angle = angle_degrees(lm["right_shoulder"], lm["right_elbow"], lm["right_wrist"])
        elbow_angle = (left_elbow_angle + right_elbow_angle) / 2.0
        self._elbow_angles.append(elbow_angle)

        shoulder_y = (lm["left_shoulder"].y + lm["right_shoulder"].y) / 2.0
        hip_y = (lm["left_hip"].y + lm["right_hip"].y) / 2.0
        self._shoulder_ys.append(shoulder_y)
        self._hip_ys.append(hip_y)

        torso_length = distance_2d(lm["left_shoulder"], lm["left_hip"])
        self._torso_lengths.append(torso_length)

        if time.time() - self._start_time < self.duration_seconds:
            return None

        # Median values reduce jitter from noisy frames.
        top_elbow_angle = float(np.median(self._elbow_angles))
        shoulder_y_top = float(np.median(self._shoulder_ys))
        hip_y_top = float(np.median(self._hip_ys))
        torso_length = max(float(np.median(self._torso_lengths)), 1e-5)

        return CalibrationResult(
            top_elbow_angle=top_elbow_angle,
            shoulder_y_top=shoulder_y_top,
            hip_y_top=hip_y_top,
            torso_length=torso_length,
        )

