import time
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np


@dataclass
class CameraFrame:
    frame: Optional[np.ndarray]
    timestamp: float
    ok: bool


class CameraStream:
    def __init__(self, camera_index: int = 0, width: int = 1280, height: int = 720, target_fps: int = 30):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.target_fps = target_fps
        self._capture: Optional[cv2.VideoCapture] = None
        self._last_time = time.time()

    def open(self) -> bool:
        self._capture = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not self._capture.isOpened():
            return False
        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self._capture.set(cv2.CAP_PROP_FPS, self.target_fps)
        return True

    def read(self) -> CameraFrame:
        if self._capture is None:
            return CameraFrame(None, time.time(), False)

        ok, frame = self._capture.read()
        now = time.time()
        if not ok:
            return CameraFrame(None, now, False)

        # FPS stabilization: sleep to keep processing close to target_fps.
        if self.target_fps > 0:
            min_frame_time = 1.0 / float(self.target_fps)
            elapsed = now - self._last_time
            if elapsed < min_frame_time:
                time.sleep(min_frame_time - elapsed)
                now = time.time()
        self._last_time = now
        return CameraFrame(frame, now, True)

    def release(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

