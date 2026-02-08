from dataclasses import dataclass
from typing import List, Optional

from calibration import CalibrationResult
from exercises.base import ExerciseBase, ExerciseState
from geometry import angle_degrees, compute_velocity
from pose_types import PoseFrame


@dataclass
class PushUpThresholds:
    top_elbow_angle: float
    bottom_elbow_angle: float
    min_shoulder_drop: float
    hip_deviation_tolerance: float
    top_drop_tolerance: float = 0.1


class PushUpCounter(ExerciseBase):
    name = "pushup"
    required_joints = [
        "left_shoulder",
        "right_shoulder",
        "left_elbow",
        "right_elbow",
        "left_wrist",
        "right_wrist",
    ]
    hip_joints = ["left_hip", "right_hip"]

    def __init__(self):
        self.rep_count = 0
        self.phase = "CALIBRATING"
        self._rep_valid = True
        self._thresholds: Optional[PushUpThresholds] = None
        self._calibration: Optional[CalibrationResult] = None
        self._last_shoulder_y = None
        self._last_time = None
        self._bad_hip_frames = 0

    def set_calibration(self, calibration: CalibrationResult) -> None:
        self._calibration = calibration
        top_elbow_angle = calibration.top_elbow_angle
        bottom_elbow_angle = max(40.0, top_elbow_angle - 80.0)
        min_shoulder_drop = 0.25
        self._thresholds = PushUpThresholds(
            top_elbow_angle=top_elbow_angle,
            bottom_elbow_angle=bottom_elbow_angle,
            min_shoulder_drop=min_shoulder_drop,
            hip_deviation_tolerance=0.25,
        )
        self.phase = "TOP"
        self._rep_valid = True

    def update(self, pose: PoseFrame) -> ExerciseState:
        warnings: List[str] = []
        if not pose.valid:
            return ExerciseState(self.rep_count, self.phase, ["No pose detected"], self._rep_valid)

        if self._thresholds is None or self._calibration is None:
            return ExerciseState(self.rep_count, "CALIBRATING", ["Calibrating..."], self._rep_valid)

        lm = pose.raw_landmarks
        if any(lm.get(k) is None for k in self.required_joints):
            return ExerciseState(self.rep_count, self.phase, ["Arms/shoulders not visible"], self._rep_valid)

        left_elbow_angle = angle_degrees(lm["left_shoulder"], lm["left_elbow"], lm["left_wrist"])
        right_elbow_angle = angle_degrees(lm["right_shoulder"], lm["right_elbow"], lm["right_wrist"])
        elbow_angle = (left_elbow_angle + right_elbow_angle) / 2.0

        shoulder_y = (lm["left_shoulder"].y + lm["right_shoulder"].y) / 2.0
        hip_y = None
        if lm.get("left_hip") is not None and lm.get("right_hip") is not None:
            hip_y = (lm["left_hip"].y + lm["right_hip"].y) / 2.0
        torso_length = self._calibration.torso_length

        shoulder_drop = (shoulder_y - self._calibration.shoulder_y_top) / torso_length
        hip_deviation = None
        if hip_y is not None:
            hip_deviation = abs(hip_y - self._calibration.hip_y_top) / torso_length

        velocity = None
        if self._last_shoulder_y is not None and self._last_time is not None:
            velocity = compute_velocity(self._last_shoulder_y, self._last_time, shoulder_y, pose.timestamp)
        self._last_shoulder_y = shoulder_y
        self._last_time = pose.timestamp

        if hip_deviation is not None:
            if hip_deviation > self._thresholds.hip_deviation_tolerance:
                self._bad_hip_frames += 1
            else:
                self._bad_hip_frames = 0
            if self._bad_hip_frames >= 5:
                warnings.append("Keep hips stable")
                self._rep_valid = False
        else:
            warnings.append("Hips not visible (stability not checked)")

        # State machine for push-up phases.
        if self.phase == "TOP":
            if elbow_angle < self._thresholds.top_elbow_angle - 10 and shoulder_drop > 0.05:
                self.phase = "DOWN"
                self._rep_valid = True
                self._bad_hip_frames = 0
        elif self.phase == "DOWN":
            if elbow_angle <= self._thresholds.bottom_elbow_angle and shoulder_drop >= self._thresholds.min_shoulder_drop:
                self.phase = "BOTTOM"
        elif self.phase == "BOTTOM":
            if velocity is not None and velocity < -0.02 and elbow_angle > self._thresholds.bottom_elbow_angle + 5:
                self.phase = "UP"
        elif self.phase == "UP":
            if (
                elbow_angle >= self._thresholds.top_elbow_angle - 5
                and shoulder_drop <= self._thresholds.top_drop_tolerance
            ):
                if self._rep_valid:
                    self.rep_count += 1
                else:
                    warnings.append("Rep not counted")
                self.phase = "TOP"

        # Depth warning if the user never reached bottom angle.
        if self.phase in ["DOWN", "BOTTOM"] and elbow_angle > self._thresholds.bottom_elbow_angle + 10:
            warnings.append("Go lower")

        return ExerciseState(self.rep_count, self.phase, warnings, self._rep_valid)

