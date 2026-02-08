from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass
class Landmark2D:
    x: float
    y: float
    z: float
    visibility: float


@dataclass
class PoseFrame:
    timestamp: float
    image_size: Tuple[int, int]
    raw_landmarks: Dict[str, Optional[Landmark2D]]
    normalized_landmarks: Dict[str, Optional[Landmark2D]]
    valid: bool

