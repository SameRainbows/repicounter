import time
from typing import List, Optional, Tuple

import cv2
import numpy as np


class BarDetector:
    def __init__(self, max_age_seconds: float = 0.6, smoothing: float = 0.7):
        self.max_age_seconds = max_age_seconds
        self.smoothing = smoothing
        self._last_y: Optional[float] = None
        self._last_time: Optional[float] = None

    def update(self, frame_bgr) -> Optional[float]:
        candidates = _detect_bar_candidates(frame_bgr)
        if candidates:
            best_y = _select_best_candidate(candidates)
            self._last_y = self._smooth(self._last_y, best_y, self.smoothing)
            self._last_time = time.time()
            return self._last_y

        if self._last_y is not None and self._last_time is not None:
            if time.time() - self._last_time <= self.max_age_seconds:
                return self._last_y
        return None

    def reset(self) -> None:
        self._last_y = None
        self._last_time = None

    @staticmethod
    def _smooth(prev: Optional[float], curr: float, alpha: float) -> float:
        if prev is None:
            return curr
        return prev * alpha + curr * (1.0 - alpha)


def detect_pullup_bar(frame_bgr) -> Optional[float]:
    # Backward-compatible stateless function.
    detector = BarDetector()
    return detector.update(frame_bgr)


def _detect_bar_candidates(frame_bgr) -> List[Tuple[float, float]]:
    height, width = frame_bgr.shape[:2]
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

    # Improve contrast for bars with subtle edges.
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    # Auto Canny thresholds using the median.
    median = float(np.median(gray))
    lower = int(max(10, 0.66 * median))
    upper = int(min(255, 1.33 * median))
    edges = cv2.Canny(gray, lower, upper)

    # Focus on top 65% where bars typically appear.
    roi_height = int(height * 0.65)
    edges_roi = edges[:roi_height, :]

    lines = cv2.HoughLinesP(
        edges_roi,
        rho=1,
        theta=np.pi / 180,
        threshold=80,
        minLineLength=int(width * 0.35),
        maxLineGap=25,
    )

    candidates: List[Tuple[float, float]] = []
    if lines is not None:
        for x1, y1, x2, y2 in lines[:, 0]:
            dx = x2 - x1
            dy = y2 - y1
            if abs(dy) > 8:
                continue
            length = abs(dx)
            if length < width * 0.35:
                continue
            y_avg = (y1 + y2) / 2.0
            y_norm = y_avg / max(roi_height, 1)
            position_score = max(0.2, 1.0 - (y_norm / 1.2))
            score = length * position_score
            candidates.append((y_avg / height, score))

    # Fallback: horizontal edge projection peak.
    if not candidates:
        proj = np.sum(edges_roi > 0, axis=1).astype(np.float32)
        if proj.size > 5:
            proj = cv2.GaussianBlur(proj.reshape(-1, 1), (1, 9), 0).flatten()
            y_idx = int(np.argmax(proj))
            if proj[y_idx] > 0.1 * np.max(proj):
                candidates.append((float(y_idx / height), float(proj[y_idx])))

    return candidates


def _select_best_candidate(candidates: List[Tuple[float, float]]) -> float:
    # Cluster candidates by row to reduce noise.
    if len(candidates) == 1:
        return candidates[0][0]

    bin_size = 0.01  # normalized ~1% of height
    bins = {}
    for y_norm, score in candidates:
        key = int(y_norm / bin_size)
        bins.setdefault(key, []).append((y_norm, score))

    best_key = None
    best_score = -1.0
    best_y = candidates[0][0]
    for key, values in bins.items():
        total = sum(score for _, score in values)
        if total > best_score:
            best_score = total
            weighted_y = sum(y * score for y, score in values) / max(total, 1e-6)
            best_y = weighted_y
            best_key = key

    _ = best_key
    return best_y

