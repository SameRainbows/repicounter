from dataclasses import dataclass
from typing import List, Optional, Tuple

from exercises.base import ExerciseBase, ExerciseState
from geometry import angle_degrees, distance_2d
from pose_types import Landmark2D, PoseFrame


@dataclass
class SitUpThresholds:
    down_torso_angle: float
    up_torso_angle: float
    min_torso_raise: float


class SitUpCounter(ExerciseBase):
    name = "situp"
    required_joints = [
        "left_shoulder",
        "left_hip",
        "left_knee",
        "right_shoulder",
        "right_hip",
        "right_knee",
    ]

    def __init__(self):
        self.rep_count = 0
        self.phase = "DOWN"
        self._thresholds = SitUpThresholds(
            down_torso_angle=35.0,
            up_torso_angle=70.0,
            min_torso_raise=0.18,
        )
        self._hip_y_base: Optional[float] = None
        self._torso_length: Optional[float] = None

    def reset(self) -> None:
        self.rep_count = 0
        self.phase = "DOWN"
        self._hip_y_base = None
        self._torso_length = None

    def update(self, pose: PoseFrame, bar_y: Optional[float] = None) -> ExerciseState:
        warnings: List[str] = []
        if not pose.valid:
            return ExerciseState(self.rep_count, self.phase, ["No pose detected"], True)

        lm = pose.raw_landmarks
        side = _select_side(lm)
        if side is None:
            return ExerciseState(self.rep_count, self.phase, ["Torso not visible"], True)

        shoulder, hip, knee = side

        if self._hip_y_base is None:
            self._hip_y_base = hip.y
        if self._torso_length is None:
            self._torso_length = max(distance_2d(shoulder, hip), 1e-5)

        torso_raise = (self._hip_y_base - hip.y) / self._torso_length
        torso_angle = angle_degrees(knee, hip, shoulder)

        if self.phase == "DOWN":
            if torso_angle >= self._thresholds.up_torso_angle and torso_raise >= self._thresholds.min_torso_raise:
                self.phase = "UP"
        elif self.phase == "UP":
            if torso_angle <= self._thresholds.down_torso_angle and torso_raise <= 0.05:
                self.rep_count += 1
                self.phase = "DOWN"

        if self.phase == "DOWN" and torso_angle > self._thresholds.down_torso_angle + 10:
            warnings.append("Lie back further")
        if self.phase == "UP" and torso_angle < self._thresholds.up_torso_angle - 5:
            warnings.append("Come up higher")

        return ExerciseState(self.rep_count, self.phase, warnings, True)


def _select_side(lm) -> Optional[Tuple[Landmark2D, Landmark2D, Landmark2D]]:
    left = (lm.get("left_shoulder"), lm.get("left_hip"), lm.get("left_knee"))
    right = (lm.get("right_shoulder"), lm.get("right_hip"), lm.get("right_knee"))
    left_valid = all(v is not None for v in left)
    right_valid = all(v is not None for v in right)
    if left_valid and right_valid:
        return left
    if left_valid:
        return left
    if right_valid:
        return right
    return None

