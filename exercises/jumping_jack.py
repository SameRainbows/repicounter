import time
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from exercises.base import ExerciseBase, ExerciseState
from geometry import distance_2d
from pose_types import PoseFrame


@dataclass
class JumpingJackThresholds:
    hip_width: float
    baseline_ankle_dist: float
    arm_raise_delta: float
    leg_spread_delta: float


class JumpingJackCounter(ExerciseBase):
    name = "jumping_jack"
    required_joints = [
        "left_shoulder",
        "right_shoulder",
        "left_wrist",
        "right_wrist",
        "left_hip",
        "right_hip",
        "left_ankle",
        "right_ankle",
    ]

    def __init__(
        self,
        calibration_seconds: float = 2.0,
        arm_raise_factor: float = 0.6,
        leg_spread_factor: float = 0.7,
    ):
        self.rep_count = 0
        self.phase = "CALIBRATING"
        self._thresholds: Optional[JumpingJackThresholds] = None
        self._start_time: Optional[float] = None
        self._hip_widths: List[float] = []
        self._ankle_dists: List[float] = []
        self._shoulder_ys: List[float] = []
        self._open_frames = 0
        self._close_frames = 0
        self._calibration_seconds = calibration_seconds
        self._arm_raise_factor = arm_raise_factor
        self._leg_spread_factor = leg_spread_factor

    def reset(self) -> None:
        self.rep_count = 0
        self.phase = "CALIBRATING"
        self._thresholds = None
        self._start_time = None
        self._hip_widths.clear()
        self._ankle_dists.clear()
        self._shoulder_ys.clear()
        self._open_frames = 0
        self._close_frames = 0

    def _maybe_calibrate(self) -> Optional[JumpingJackThresholds]:
        if self._start_time is None:
            self._start_time = time.time()
        if time.time() - self._start_time < self._calibration_seconds:
            return None

        hip_width = float(np.median(self._hip_widths)) if self._hip_widths else 0.0
        ankle_dist = float(np.median(self._ankle_dists)) if self._ankle_dists else 0.0
        shoulder_y = float(np.median(self._shoulder_ys)) if self._shoulder_ys else 0.0

        if hip_width < 1e-5:
            hip_width = 0.2

        # Thresholds are normalized by hip width to make them person-agnostic.
        return JumpingJackThresholds(
            hip_width=hip_width,
            baseline_ankle_dist=ankle_dist,
            arm_raise_delta=self._arm_raise_factor * hip_width,
            leg_spread_delta=self._leg_spread_factor * hip_width,
        )

    def update(self, pose: PoseFrame, bar_y: Optional[float] = None) -> ExerciseState:
        warnings: List[str] = []
        if not pose.valid:
            return ExerciseState(self.rep_count, self.phase, ["No pose detected"], True)

        lm = pose.raw_landmarks
        if any(lm.get(k) is None for k in self.required_joints):
            return ExerciseState(self.rep_count, self.phase, ["Body not fully visible"], True)

        left_shoulder = lm["left_shoulder"]
        right_shoulder = lm["right_shoulder"]
        left_wrist = lm["left_wrist"]
        right_wrist = lm["right_wrist"]
        left_hip = lm["left_hip"]
        right_hip = lm["right_hip"]
        left_ankle = lm["left_ankle"]
        right_ankle = lm["right_ankle"]

        shoulder_y = (left_shoulder.y + right_shoulder.y) / 2.0
        hip_width = distance_2d(left_hip, right_hip)
        ankle_dist = distance_2d(left_ankle, right_ankle)

        if self._thresholds is None:
            self._hip_widths.append(hip_width)
            self._ankle_dists.append(ankle_dist)
            self._shoulder_ys.append(shoulder_y)
            thresholds = self._maybe_calibrate()
            if thresholds is None:
                return ExerciseState(self.rep_count, "CALIBRATING", ["Calibrating..."], True)
            self._thresholds = thresholds
            self.phase = "CLOSED"

        thresholds = self._thresholds
        wrist_avg_y = (left_wrist.y + right_wrist.y) / 2.0

        arms_up = (shoulder_y - wrist_avg_y) >= thresholds.arm_raise_delta
        arms_down = (wrist_avg_y - shoulder_y) >= 0.15 * thresholds.hip_width

        legs_apart = ankle_dist >= thresholds.baseline_ankle_dist + thresholds.leg_spread_delta
        legs_together = ankle_dist <= thresholds.baseline_ankle_dist + 0.2 * thresholds.hip_width

        if self.phase == "CLOSED":
            if arms_up and legs_apart:
                self._open_frames += 1
                if self._open_frames >= 2:
                    self.phase = "OPEN"
                    self._open_frames = 0
            else:
                self._open_frames = 0
        elif self.phase == "OPEN":
            if arms_down and legs_together:
                self._close_frames += 1
                if self._close_frames >= 2:
                    self.rep_count += 1
                    self.phase = "CLOSED"
                    self._close_frames = 0
            else:
                self._close_frames = 0

        if not arms_up and self.phase == "OPEN":
            warnings.append("Raise arms higher")
        if not legs_apart and self.phase == "OPEN":
            warnings.append("Spread legs wider")

        return ExerciseState(self.rep_count, self.phase, warnings, True)

