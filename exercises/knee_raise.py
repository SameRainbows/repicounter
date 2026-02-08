from dataclasses import dataclass
from typing import List, Optional, Tuple

from exercises.base import ExerciseBase, ExerciseState
from geometry import distance_2d
from pose_types import Landmark2D, PoseFrame


@dataclass
class KneeRaiseThresholds:
    raise_delta: float
    lower_delta: float


class KneeRaiseCounter(ExerciseBase):
    name = "knee_raise"
    required_joints = [
        "left_hip",
        "left_knee",
        "left_ankle",
        "right_hip",
        "right_knee",
        "right_ankle",
    ]

    def __init__(self, raise_delta: float = 0.35, lower_delta: float = 0.12):
        self.rep_count = 0
        self.phase = "DOWN"
        self._thresholds = KneeRaiseThresholds(raise_delta=raise_delta, lower_delta=lower_delta)
        self._leg_length: Optional[float] = None

    def reset(self) -> None:
        self.rep_count = 0
        self.phase = "DOWN"
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
        if self._leg_length is None:
            self._leg_length = max(distance_2d(hip, ankle), 1e-5)

        knee_raise = (hip.y - knee.y) / self._leg_length

        if self.phase == "DOWN":
            if knee_raise >= self._thresholds.raise_delta:
                self.phase = "UP"
        elif self.phase == "UP":
            if knee_raise <= self._thresholds.lower_delta:
                self.rep_count += 1
                self.phase = "DOWN"

        if self.phase == "UP" and knee_raise < self._thresholds.raise_delta * 0.85:
            warnings.append("Lift knee higher")

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

