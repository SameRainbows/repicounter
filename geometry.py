import math
from typing import Optional, Tuple

from pose_types import Landmark2D


def _to_xy(lm: Landmark2D) -> Tuple[float, float]:
    return lm.x, lm.y


def distance_2d(a: Landmark2D, b: Landmark2D) -> float:
    ax, ay = _to_xy(a)
    bx, by = _to_xy(b)
    return math.hypot(ax - bx, ay - by)


def angle_degrees(a: Landmark2D, b: Landmark2D, c: Landmark2D) -> float:
    # Angle at b formed by vectors (a - b) and (c - b).
    # Using dot product: angle = acos((u·v)/(|u||v|)).
    bax = a.x - b.x
    bay = a.y - b.y
    bcx = c.x - b.x
    bcy = c.y - b.y

    dot = bax * bcx + bay * bcy
    mag_ba = math.hypot(bax, bay)
    mag_bc = math.hypot(bcx, bcy)
    if mag_ba < 1e-6 or mag_bc < 1e-6:
        return 0.0
    cos_theta = max(-1.0, min(1.0, dot / (mag_ba * mag_bc)))
    return math.degrees(math.acos(cos_theta))


def vertical_delta(a: Landmark2D, b: Landmark2D) -> float:
    # Positive when a is lower (greater y) than b in image coordinates.
    return a.y - b.y


def compute_velocity(prev_val: float, prev_time: float, curr_val: float, curr_time: float) -> Optional[float]:
    dt = curr_time - prev_time
    if dt <= 1e-6:
        return None
    return (curr_val - prev_val) / dt

