from dataclasses import dataclass
from typing import List

from pose_types import PoseFrame


@dataclass
class ExerciseState:
    rep_count: int
    phase: str
    warnings: List[str]
    is_rep_valid: bool


class ExerciseBase:
    name = "base"
    required_joints: List[str] = []

    def update(self, pose: PoseFrame, **kwargs):
        raise NotImplementedError

    def reset(self) -> None:
        raise NotImplementedError

