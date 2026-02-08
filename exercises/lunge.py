from dataclasses import dataclass
from typing import List, Optional, Tuple

from exercises.base import ExerciseBase, ExerciseState
from geometry import angle_degrees, distance_2d
from pose_types import Landmark2D, PoseFrame


@dataclass
class LungeThresholds:
    top_knee_angle: float
    bottom_knee_angle: float
    hip_drop_min: float
    start_drop: float


class LungeCounter(ExerciseBase):
    name = "lunge"
    required_joints = [
        "left_hip",
        "left_knee",
        "left_ankle",
        "right_hip",
        "right_knee",
        "right_ankle",
    ]

    def __init__(
        self,
        top_knee_angle: float = 165.0,
        bottom_knee_angle: float = 95.0,
        hip_drop_min: float = 0.16,
        start_drop: float = 0.08,
    ):
        self.rep_count = 0
        self.phase = "TOP"
        self._thresholds = LungeThresholds(
            top_knee_angle=top_knee_angle,
            bottom_knee_angle=bottom_knee_angle,
            hip_drop_min=hip_drop_min,
            start_drop=start_drop,
        )
        self._hip_y_top: Optional[float] = None
        self._leg_length: Optional[float] = None

    def reset(self) -> None:
        self.rep_count = 0
        self.phase = "TOP"
        self._hip_y_top = None
        self._leg_length = None

    def update(self, pose: PoseFrame, bar_y: Optional[float] = None) -> ExerciseState:
        warnings: List[str] = []
        if not pose.valid:
            return ExerciseState(self.rep_count, self.phase, ["No pose detected"], True)

        lm = pose.raw_landmarks
        side = _select_side(lm)
        if side is None:
            return ExerciseState(self.rep_count, self.phase, ["Legs not visible"], True)

        hip, knee, ankle = side
        knee_angle = angle_degrees(hip, knee, ankle)
        hip_y = hip.y
        if self._hip_y_top is None:
            self._hip_y_top = hip_y
        if self._leg_length is None:
            self._leg_length = max(distance_2d(hip, ankle), 1e-5)
        hip_drop = (hip_y - self._hip_y_top) / self._leg_length

        if self.phase == "TOP":
            if knee_angle < self._thresholds.top_knee_angle and hip_drop > self._thresholds.start_drop:
                self.phase = "DOWN"
        elif self.phase == "DOWN":
            if knee_angle <= self._thresholds.bottom_knee_angle and hip_drop >= self._thresholds.hip_drop_min:
                self.phase = "BOTTOM"
        elif self.phase == "BOTTOM":
            if knee_angle > self._thresholds.bottom_knee_angle + 5:
                self.phase = "UP"
        elif self.phase == "UP":
            if knee_angle >= self._thresholds.top_knee_angle - 5 and hip_drop <= 0.05:
                self.rep_count += 1
                self.phase = "TOP"

        if self.phase in ["DOWN", "BOTTOM"] and knee_angle > self._thresholds.bottom_knee_angle + 10:
            warnings.append("Go lower")

        return ExerciseState(self.rep_count, self.phase, warnings, True)


def _select_side(lm) -> Optional[Tuple[Landmark2D, Landmark2D, Landmark2D]]:
    left = (lm.get("left_hip"), lm.get("left_knee"), lm.get("left_ankle"))
    right = (lm.get("right_hip"), lm.get("right_knee"), lm.get("right_ankle"))
    left_valid = all(v is not None for v in left)
    right_valid = all(v is not None for v in right)
    if left_valid and right_valid:
        return left
    if left_valid:
        return left
    if right_valid:
        return right
    return None

