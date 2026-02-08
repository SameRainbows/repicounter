from dataclasses import dataclass
from typing import List

from exercises.arm_raise import ArmRaiseCounter
from exercises.hold import HoldCounter
from exercises.jumping_jack import JumpingJackCounter
from exercises.knee_raise import KneeRaiseCounter
from exercises.leg_spread import LegSpreadCounter
from exercises.lunge import LungeCounter
from exercises.pullup import PullUpCounter
from exercises.situp import SitUpCounter
from exercises.squat import SquatCounter
from exercises.torso_bend import TorsoBendCounter
from geometry import angle_degrees


@dataclass
class ExerciseEntry:
    name: str
    counter: object
    view_hint: str
    uses_bar: bool = False


def get_exercise_entries() -> List[ExerciseEntry]:
    entries: List[ExerciseEntry] = [
        ExerciseEntry("Jumping Jack", JumpingJackCounter(), "Front"),
        ExerciseEntry("Squat", SquatCounter(), "Front"),
        ExerciseEntry("Pull-Up", PullUpCounter(variant="pullup"), "Bar", uses_bar=True),
        ExerciseEntry("Chin-Up", PullUpCounter(variant="chinup"), "Bar", uses_bar=True),
        ExerciseEntry("Sit-Up", SitUpCounter(), "Side"),
    ]

    # Standing cardio / arms
    entries += [
        ExerciseEntry("Step Jack", JumpingJackCounter(arm_raise_factor=0.45, leg_spread_factor=0.5), "Front"),
        ExerciseEntry("Half Jack", JumpingJackCounter(arm_raise_factor=0.35, leg_spread_factor=0.4), "Front"),
        ExerciseEntry("Seal Jack", LegSpreadCounter(spread_delta=0.6, close_delta=0.2), "Front"),
        ExerciseEntry("Side Steps", LegSpreadCounter(spread_delta=0.35, close_delta=0.15), "Front"),
        ExerciseEntry("High Knees", KneeRaiseCounter(raise_delta=0.42, lower_delta=0.15), "Front"),
        ExerciseEntry("Marching", KneeRaiseCounter(raise_delta=0.25, lower_delta=0.12), "Front"),
        ExerciseEntry("Arm Raises", ArmRaiseCounter(raise_delta=0.35, lower_delta=0.15), "Front"),
        ExerciseEntry("Overhead Raises", ArmRaiseCounter(raise_delta=0.55, lower_delta=0.2), "Front"),
        ExerciseEntry("Lateral Raises", ArmRaiseCounter(raise_delta=0.25, lower_delta=0.12), "Front"),
        ExerciseEntry("Side Bends", TorsoBendCounter(bend_delta=0.22, return_delta=0.08), "Front"),
    ]

    # Squat variants
    entries += [
        ExerciseEntry("Wide Squat", SquatCounter(bottom_knee_angle=100.0, hip_drop_min=0.2), "Front"),
        ExerciseEntry("Narrow Squat", SquatCounter(bottom_knee_angle=95.0, hip_drop_min=0.16), "Front"),
        ExerciseEntry("Half Squat", SquatCounter(bottom_knee_angle=120.0, hip_drop_min=0.12), "Front"),
        ExerciseEntry("Pulse Squat", SquatCounter(bottom_knee_angle=110.0, hip_drop_min=0.15), "Front"),
        ExerciseEntry("Jump Squat", SquatCounter(bottom_knee_angle=100.0, hip_drop_min=0.18), "Front"),
    ]

    # Lunge variants
    entries += [
        ExerciseEntry("Forward Lunge", LungeCounter(bottom_knee_angle=95.0, hip_drop_min=0.18), "Side"),
        ExerciseEntry("Reverse Lunge", LungeCounter(bottom_knee_angle=95.0, hip_drop_min=0.18), "Side"),
        ExerciseEntry("Split Squat", LungeCounter(bottom_knee_angle=100.0, hip_drop_min=0.16), "Side"),
        ExerciseEntry("Side Lunge", LungeCounter(bottom_knee_angle=105.0, hip_drop_min=0.16), "Front"),
    ]

    # Ground / core holds
    entries += [
        ExerciseEntry("Plank Hold", _plank_hold(), "Side"),
        ExerciseEntry("Side Plank Hold", _side_plank_hold(), "Side"),
        ExerciseEntry("Wall Sit Hold", _wall_sit_hold(), "Side"),
        ExerciseEntry("Glute Bridge", _glute_bridge(), "Side"),
        ExerciseEntry("Hip Hinge", _hip_hinge(), "Side"),
        ExerciseEntry("Knee Tucks", KneeRaiseCounter(raise_delta=0.3, lower_delta=0.12), "Side"),
    ]

    # Extra variations to reach 30+ exercises
    entries += [
        ExerciseEntry("Skater Steps", LegSpreadCounter(spread_delta=0.5, close_delta=0.2), "Front"),
        ExerciseEntry("Toe Touches", TorsoBendCounter(bend_delta=0.28, return_delta=0.1), "Front"),
        ExerciseEntry("Arm Pulses", ArmRaiseCounter(raise_delta=0.2, lower_delta=0.08), "Front"),
        ExerciseEntry("Fast Jacks", JumpingJackCounter(arm_raise_factor=0.5, leg_spread_factor=0.6), "Front"),
        ExerciseEntry("Slow Jacks", JumpingJackCounter(arm_raise_factor=0.7, leg_spread_factor=0.75), "Front"),
        ExerciseEntry("Low Jacks", JumpingJackCounter(arm_raise_factor=0.35, leg_spread_factor=0.5), "Front"),
        ExerciseEntry("Power Jacks", JumpingJackCounter(arm_raise_factor=0.75, leg_spread_factor=0.85), "Front"),
        ExerciseEntry("Box Squat", SquatCounter(bottom_knee_angle=100.0, hip_drop_min=0.2), "Side"),
        ExerciseEntry("Tempo Squat", SquatCounter(bottom_knee_angle=105.0, hip_drop_min=0.18), "Front"),
        ExerciseEntry("Split Squat Hold", _split_squat_hold(), "Side"),
    ]

    return entries


def _plank_hold() -> HoldCounter:
    def condition(lm):
        shoulder = lm.get("left_shoulder") or lm.get("right_shoulder")
        hip = lm.get("left_hip") or lm.get("right_hip")
        knee = lm.get("left_knee") or lm.get("right_knee")
        if not shoulder or not hip or not knee:
            return False
        angle = angle_degrees(shoulder, hip, knee)
        return angle > 160.0

    return HoldCounter(
        name="plank_hold",
        required_joints=["left_shoulder", "left_hip", "left_knee"],
        hold_condition=condition,
        hold_seconds=2.0,
        required_any_groups=[
            ["left_shoulder", "left_hip", "left_knee"],
            ["right_shoulder", "right_hip", "right_knee"],
        ],
    )


def _side_plank_hold() -> HoldCounter:
    def condition(lm):
        shoulder = lm.get("left_shoulder") or lm.get("right_shoulder")
        hip = lm.get("left_hip") or lm.get("right_hip")
        knee = lm.get("left_knee") or lm.get("right_knee")
        if not shoulder or not hip or not knee:
            return False
        angle = angle_degrees(shoulder, hip, knee)
        return angle > 155.0

    return HoldCounter(
        name="side_plank_hold",
        required_joints=["left_shoulder", "left_hip", "left_knee"],
        hold_condition=condition,
        hold_seconds=2.0,
        required_any_groups=[
            ["left_shoulder", "left_hip", "left_knee"],
            ["right_shoulder", "right_hip", "right_knee"],
        ],
    )


def _wall_sit_hold() -> HoldCounter:
    def condition(lm):
        hip = lm.get("left_hip") or lm.get("right_hip")
        knee = lm.get("left_knee") or lm.get("right_knee")
        ankle = lm.get("left_ankle") or lm.get("right_ankle")
        if not hip or not knee or not ankle:
            return False
        angle = angle_degrees(hip, knee, ankle)
        return 80.0 <= angle <= 110.0

    return HoldCounter(
        name="wall_sit_hold",
        required_joints=["left_hip", "left_knee", "left_ankle"],
        hold_condition=condition,
        hold_seconds=2.5,
        required_any_groups=[
            ["left_hip", "left_knee", "left_ankle"],
            ["right_hip", "right_knee", "right_ankle"],
        ],
    )


def _glute_bridge() -> HoldCounter:
    def condition(lm):
        shoulder = lm.get("left_shoulder") or lm.get("right_shoulder")
        hip = lm.get("left_hip") or lm.get("right_hip")
        knee = lm.get("left_knee") or lm.get("right_knee")
        if not shoulder or not hip or not knee:
            return False
        angle = angle_degrees(shoulder, hip, knee)
        return angle > 155.0

    return HoldCounter(
        name="glute_bridge",
        required_joints=["left_shoulder", "left_hip", "left_knee"],
        hold_condition=condition,
        hold_seconds=1.5,
        required_any_groups=[
            ["left_shoulder", "left_hip", "left_knee"],
            ["right_shoulder", "right_hip", "right_knee"],
        ],
    )


def _hip_hinge() -> HoldCounter:
    def condition(lm):
        shoulder = lm.get("left_shoulder") or lm.get("right_shoulder")
        hip = lm.get("left_hip") or lm.get("right_hip")
        knee = lm.get("left_knee") or lm.get("right_knee")
        if not shoulder or not hip or not knee:
            return False
        angle = angle_degrees(shoulder, hip, knee)
        return 60.0 <= angle <= 110.0

    return HoldCounter(
        name="hip_hinge",
        required_joints=["left_shoulder", "left_hip", "left_knee"],
        hold_condition=condition,
        hold_seconds=1.0,
        required_any_groups=[
            ["left_shoulder", "left_hip", "left_knee"],
            ["right_shoulder", "right_hip", "right_knee"],
        ],
    )


def _split_squat_hold() -> HoldCounter:
    def condition(lm):
        hip = lm.get("left_hip") or lm.get("right_hip")
        knee = lm.get("left_knee") or lm.get("right_knee")
        ankle = lm.get("left_ankle") or lm.get("right_ankle")
        if not hip or not knee or not ankle:
            return False
        angle = angle_degrees(hip, knee, ankle)
        return 80.0 <= angle <= 115.0

    return HoldCounter(
        name="split_squat_hold",
        required_joints=["left_hip", "left_knee", "left_ankle"],
        hold_condition=condition,
        hold_seconds=2.0,
        required_any_groups=[
            ["left_hip", "left_knee", "left_ankle"],
            ["right_hip", "right_knee", "right_ankle"],
        ],
    )

