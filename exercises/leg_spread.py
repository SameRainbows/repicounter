from dataclasses import dataclass
from typing import List, Optional

from exercises.base import ExerciseBase, ExerciseState
from geometry import distance_2d
from pose_types import PoseFrame


@dataclass
class LegSpreadThresholds:
    spread_delta: float
    close_delta: float


class LegSpreadCounter(ExerciseBase):
    name = "leg_spread"
    required_joints = [
        "left_hip",
        "right_hip",
        "left_ankle",
        "right_ankle",
    ]

    def __init__(self, spread_delta: float = 0.6, close_delta: float = 0.2):
        self.rep_count = 0
        self.phase = "CLOSED"
        self._thresholds = LegSpreadThresholds(
            spread_delta=spread_delta,
            close_delta=close_delta,
        )
        self._baseline_ankle_dist: Optional[float] = None
        self._hip_width: Optional[float] = None

    def reset(self) -> None:
        self.rep_count = 0
        self.phase = "CLOSED"
        self._baseline_ankle_dist = None
        self._hip_width = None

    def update(self, pose: PoseFrame, bar_y: Optional[float] = None) -> ExerciseState:
        warnings: List[str] = []
        if not pose.valid:
            return ExerciseState(self.rep_count, self.phase, ["No pose detected"], True)

        lm = pose.raw_landmarks
        if any(lm.get(k) is None for k in self.required_joints):
            return ExerciseState(self.rep_count, self.phase, ["Legs not visible"], True)

        left_hip = lm["left_hip"]
        right_hip = lm["right_hip"]
        left_ankle = lm["left_ankle"]
        right_ankle = lm["right_ankle"]

        hip_width = distance_2d(left_hip, right_hip)
        ankle_dist = distance_2d(left_ankle, right_ankle)
        if self._hip_width is None:
            self._hip_width = max(hip_width, 1e-5)
        if self._baseline_ankle_dist is None:
            self._baseline_ankle_dist = ankle_dist

        spread = (ankle_dist - self._baseline_ankle_dist) / self._hip_width

        if self.phase == "CLOSED":
            if spread >= self._thresholds.spread_delta:
                self.phase = "OPEN"
        elif self.phase == "OPEN":
            if spread <= self._thresholds.close_delta:
                self.rep_count += 1
                self.phase = "CLOSED"

        if self.phase == "OPEN" and spread < self._thresholds.spread_delta * 0.8:
            warnings.append("Spread legs wider")

        return ExerciseState(self.rep_count, self.phase, warnings, True)

