from typing import Dict, Optional, Tuple

import cv2
import mediapipe as mp

from pose_types import Landmark2D, PoseFrame


class PoseDetector:
    def __init__(
        self,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        visibility_threshold: float = 0.5,
    ):
        self.visibility_threshold = visibility_threshold
        self._mp_pose = mp.solutions.pose
        self._pose = self._mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            smooth_landmarks=True,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self._landmark_names = {
            lm.name.lower(): lm for lm in self._mp_pose.PoseLandmark
        }

    def process(self, frame_bgr, timestamp: float) -> PoseFrame:
        height, width = frame_bgr.shape[:2]
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self._pose.process(frame_rgb)

        raw_landmarks: Dict[str, Optional[Landmark2D]] = {k: None for k in self._landmark_names}
        normalized_landmarks: Dict[str, Optional[Landmark2D]] = {k: None for k in self._landmark_names}
        valid = results.pose_landmarks is not None
        if not valid:
            return PoseFrame(
                timestamp=timestamp,
                image_size=(width, height),
                raw_landmarks=raw_landmarks,
                normalized_landmarks=normalized_landmarks,
                valid=False,
            )

        for name, idx in self._landmark_names.items():
            lm = results.pose_landmarks.landmark[idx]
            if lm.visibility < self.visibility_threshold:
                raw_landmarks[name] = None
                continue
            raw_landmarks[name] = Landmark2D(lm.x, lm.y, lm.z, lm.visibility)

        normalized_landmarks = self._normalize(raw_landmarks)
        return PoseFrame(
            timestamp=timestamp,
            image_size=(width, height),
            raw_landmarks=raw_landmarks,
            normalized_landmarks=normalized_landmarks,
            valid=True,
        )

    def _normalize(self, raw_landmarks: Dict[str, Optional[Landmark2D]]) -> Dict[str, Optional[Landmark2D]]:
        # Normalize coordinates to a body-centered frame:
        # - origin at hip center
        # - scale by shoulder or hip width to reduce distance variance
        left_hip = raw_landmarks.get("left_hip")
        right_hip = raw_landmarks.get("right_hip")
        left_shoulder = raw_landmarks.get("left_shoulder")
        right_shoulder = raw_landmarks.get("right_shoulder")

        if left_hip is None or right_hip is None:
            return {k: None if v is None else v for k, v in raw_landmarks.items()}

        center_x = (left_hip.x + right_hip.x) / 2.0
        center_y = (left_hip.y + right_hip.y) / 2.0

        if left_shoulder is not None and right_shoulder is not None:
            scale = abs(left_shoulder.x - right_shoulder.x)
        else:
            scale = abs(left_hip.x - right_hip.x)

        if scale < 1e-5:
            scale = 1.0

        normalized: Dict[str, Optional[Landmark2D]] = {}
        for name, lm in raw_landmarks.items():
            if lm is None:
                normalized[name] = None
                continue
            normalized[name] = Landmark2D(
                (lm.x - center_x) / scale,
                (lm.y - center_y) / scale,
                lm.z / scale,
                lm.visibility,
            )
        return normalized

