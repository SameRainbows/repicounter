from dataclasses import dataclass
from typing import List, Optional

from exercises.base import ExerciseBase, ExerciseState
from geometry import distance_2d
from pose_types import PoseFrame


@dataclass
class TorsoBendThresholds:
    bend_delta: float
    return_delta: float


class TorsoBendCounter(ExerciseBase):
    name = "torso_bend"
    required_joints = [
        "left_shoulder",
        "right_shoulder",
        "left_hip",
        "right_hip",
    ]

    def __init__(self, bend_delta: float = 0.25, return_delta: float = 0.08):
        self.rep_count = 0
        self.phase = "CENTER"
        self._thresholds = TorsoBendThresholds(bend_delta=bend_delta, return_delta=return_delta)
        self._shoulder_width: Optional[float] = None

    def reset(self) -> None:
        self.rep_count = 0
        self.phase = "CENTER"
        self._shoulder_width = None

    def update(self, pose: PoseFrame, bar_y: Optional[float] = None) -> ExerciseState:
        warnings: List[str] = []
        if not pose.valid:
            return ExerciseState(self.rep_count, self.phase, ["No pose detected"], True)

        lm = pose.raw_landmarks
        if any(lm.get(k) is None for k in self.required_joints):
            return ExerciseState(self.rep_count, self.phase, ["Torso not visible"], True)

        left_shoulder = lm["left_shoulder"]
        right_shoulder = lm["right_shoulder"]
        left_hip = lm["left_hip"]
        right_hip = lm["right_hip"]

        shoulder_center_x = (left_shoulder.x + right_shoulder.x) / 2.0
        hip_center_x = (left_hip.x + right_hip.x) / 2.0
        shoulder_width = distance_2d(left_shoulder, right_shoulder)
        if self._shoulder_width is None:
            self._shoulder_width = max(shoulder_width, 1e-5)

        bend = abs(shoulder_center_x - hip_center_x) / self._shoulder_width

        if self.phase == "CENTER":
            if bend >= self._thresholds.bend_delta:
                self.phase = "BEND"
        elif self.phase == "BEND":
            if bend <= self._thresholds.return_delta:
                self.rep_count += 1
                self.phase = "CENTER"

        if self.phase == "BEND" and bend < self._thresholds.bend_delta * 0.85:
            warnings.append("Bend further")

        return ExerciseState(self.rep_count, self.phase, warnings, True)

