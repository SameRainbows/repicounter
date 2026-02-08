from dataclasses import dataclass
from typing import List, Optional

from exercises.base import ExerciseBase, ExerciseState
from geometry import distance_2d
from pose_types import PoseFrame


@dataclass
class ArmRaiseThresholds:
    raise_delta: float
    lower_delta: float
    min_spread: float


class ArmRaiseCounter(ExerciseBase):
    name = "arm_raise"
    required_joints = [
        "left_shoulder",
        "right_shoulder",
        "left_wrist",
        "right_wrist",
    ]

    def __init__(self, raise_delta: float = 0.45, lower_delta: float = 0.15, min_spread: float = 0.2):
        self.rep_count = 0
        self.phase = "DOWN"
        self._thresholds = ArmRaiseThresholds(
            raise_delta=raise_delta,
            lower_delta=lower_delta,
            min_spread=min_spread,
        )
        self._shoulder_width: Optional[float] = None

    def reset(self) -> None:
        self.rep_count = 0
        self.phase = "DOWN"
        self._shoulder_width = None

    def update(self, pose: PoseFrame, bar_y: Optional[float] = None) -> ExerciseState:
        warnings: List[str] = []
        if not pose.valid:
            return ExerciseState(self.rep_count, self.phase, ["No pose detected"], True)

        lm = pose.raw_landmarks
        if any(lm.get(k) is None for k in self.required_joints):
            return ExerciseState(self.rep_count, self.phase, ["Arms not visible"], True)

        left_shoulder = lm["left_shoulder"]
        right_shoulder = lm["right_shoulder"]
        left_wrist = lm["left_wrist"]
        right_wrist = lm["right_wrist"]

        shoulder_y = (left_shoulder.y + right_shoulder.y) / 2.0
        wrist_y = (left_wrist.y + right_wrist.y) / 2.0
        shoulder_width = distance_2d(left_shoulder, right_shoulder)
        if self._shoulder_width is None:
            self._shoulder_width = max(shoulder_width, 1e-5)

        arm_raise = (shoulder_y - wrist_y) / self._shoulder_width
        arm_lower = (wrist_y - shoulder_y) / self._shoulder_width

        if self.phase == "DOWN":
            if arm_raise >= self._thresholds.raise_delta:
                self.phase = "UP"
        elif self.phase == "UP":
            if arm_lower >= self._thresholds.lower_delta:
                self.rep_count += 1
                self.phase = "DOWN"

        if self.phase == "UP" and arm_raise < self._thresholds.raise_delta * 0.8:
            warnings.append("Raise arms higher")

        return ExerciseState(self.rep_count, self.phase, warnings, True)

