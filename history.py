from collections import deque
from typing import Deque, Iterable, List, Optional

from pose_types import PoseFrame


class PoseHistory:
    def __init__(self, maxlen: int = 90):
        self._buffer: Deque[PoseFrame] = deque(maxlen=maxlen)

    def append(self, pose: PoseFrame) -> None:
        self._buffer.append(pose)

    def latest(self) -> Optional[PoseFrame]:
        return self._buffer[-1] if self._buffer else None

    def latest_valid(self) -> Optional[PoseFrame]:
        for pose in reversed(self._buffer):
            if pose.valid:
                return pose
        return None

    def recent(self, count: int) -> List[PoseFrame]:
        if count <= 0:
            return []
        return list(self._buffer)[-count:]

    def time_window(self, seconds: float) -> List[PoseFrame]:
        if not self._buffer:
            return []
        end_time = self._buffer[-1].timestamp
        return [p for p in self._buffer if end_time - p.timestamp <= seconds]

