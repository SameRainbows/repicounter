from dataclasses import dataclass
from typing import List, Optional

from exercises.base import ExerciseBase, ExerciseState
from geometry import distance_2d
from pose_types import PoseFrame


@dataclass
class PullUpThresholds:
    chin_above_bar: float
    bottom_reset_delta: float
    grip_width_min: float
    max_face_depth_delta: float
    wrist_bar_y_delta: float


class PullUpCounter(ExerciseBase):
    name = "pullup"
    required_joints = [
        "nose",
        "left_wrist",
        "right_wrist",
        "left_shoulder",
        "right_shoulder",
    ]

    def __init__(self, variant: str = "pullup"):
        self.rep_count = 0
        self.phase = "WAITING_BAR"
        self._thresholds = PullUpThresholds(
            chin_above_bar=0.015,
            bottom_reset_delta=0.08,
            grip_width_min=0.15,
            max_face_depth_delta=0.15,
            wrist_bar_y_delta=0.08,
        )
        self._bar_y: Optional[float] = None
        self._variant = variant

    def reset(self) -> None:
        self.rep_count = 0
        self.phase = "WAITING_BAR"
        self._bar_y = None

    def update(self, pose: PoseFrame, bar_y: Optional[float] = None) -> ExerciseState:
        warnings: List[str] = []
        if not pose.valid:
            return ExerciseState(self.rep_count, self.phase, ["No pose detected"], True)

        if bar_y is None:
            return ExerciseState(self.rep_count, "WAITING_BAR", ["Bar not found"], True)

        self._bar_y = bar_y

        lm = pose.raw_landmarks
        if any(lm.get(k) is None for k in self.required_joints):
            return ExerciseState(self.rep_count, self.phase, ["Upper body not visible"], True)

        nose_y = lm["nose"].y
        nose_z = lm["nose"].z
        wrist_dist = distance_2d(lm["left_wrist"], lm["right_wrist"])
        shoulder_width = distance_2d(lm["left_shoulder"], lm["right_shoulder"])
        shoulder_z = (lm["left_shoulder"].z + lm["right_shoulder"].z) / 2.0
        wrist_avg_y = (lm["left_wrist"].y + lm["right_wrist"].y) / 2.0

        if wrist_dist < self._thresholds.grip_width_min * max(shoulder_width, 1e-5):
            warnings.append("Wider grip for pull-ups")

        # Depth guard: prevent false positives when user moves close to camera.
        depth_ok = (shoulder_z - nose_z) <= self._thresholds.max_face_depth_delta

        # Ensure wrists are near the bar line (simple contact proxy).
        wrists_on_bar = abs(wrist_avg_y - bar_y) <= self._thresholds.wrist_bar_y_delta

        chin_above = (bar_y - nose_y) > self._thresholds.chin_above_bar and depth_ok and wrists_on_bar
        chin_below = (nose_y - bar_y) > self._thresholds.bottom_reset_delta

        if self.phase in ["WAITING_BAR", "DOWN"]:
            if chin_above:
                self.phase = "UP"
        elif self.phase == "UP":
            if chin_below:
                self.rep_count += 1
                self.phase = "DOWN"

        if not depth_ok:
            warnings.append("Move back from camera")
        if not wrists_on_bar:
            warnings.append("Keep wrists on the bar")
        if self._variant == "chinup" and wrist_dist > shoulder_width * 1.4:
            warnings.append("Narrower grip for chin-ups")

        return ExerciseState(self.rep_count, self.phase, warnings, True)

