import time
from dataclasses import dataclass
from typing import Callable, List, Optional

from exercises.base import ExerciseBase, ExerciseState
from pose_types import PoseFrame


@dataclass
class HoldThresholds:
    hold_seconds: float


class HoldCounter(ExerciseBase):
    name = "hold"
    required_joints = []

    def __init__(
        self,
        name: str,
        required_joints: List[str],
        hold_condition: Callable,
        hold_seconds: float = 2.0,
        required_any_groups: Optional[List[List[str]]] = None,
    ):
        self.name = name
        self.required_joints = required_joints
        self.rep_count = 0
        self.phase = "READY"
        self._thresholds = HoldThresholds(hold_seconds=hold_seconds)
        self._hold_condition = hold_condition
        self._hold_start: Optional[float] = None
        self._required_any_groups = required_any_groups

    def reset(self) -> None:
        self.rep_count = 0
        self.phase = "READY"
        self._hold_start = None

    def update(self, pose: PoseFrame, bar_y: Optional[float] = None) -> ExerciseState:
        warnings: List[str] = []
        if not pose.valid:
            return ExerciseState(self.rep_count, self.phase, ["No pose detected"], True)

        lm = pose.raw_landmarks
        if self._required_any_groups:
            if not any(all(lm.get(k) is not None for k in group) for group in self._required_any_groups):
                return ExerciseState(self.rep_count, self.phase, ["Body not visible"], True)
        else:
            if any(lm.get(k) is None for k in self.required_joints):
                return ExerciseState(self.rep_count, self.phase, ["Body not visible"], True)

        holding = self._hold_condition(lm)
        now = time.time()

        if self.phase == "READY":
            if holding:
                self.phase = "HOLDING"
                self._hold_start = now
        elif self.phase == "HOLDING":
            if not holding:
                self.phase = "READY"
                self._hold_start = None
            elif self._hold_start and now - self._hold_start >= self._thresholds.hold_seconds:
                self.rep_count += 1
                self.phase = "COUNTED"
        elif self.phase == "COUNTED":
            if not holding:
                self.phase = "READY"
                self._hold_start = None

        if self.phase == "HOLDING":
            remaining = max(0.0, self._thresholds.hold_seconds - (now - (self._hold_start or now)))
            warnings.append(f"Hold {remaining:.1f}s")

        return ExerciseState(self.rep_count, self.phase, warnings, True)

