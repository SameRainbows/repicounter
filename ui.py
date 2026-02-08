import time
from typing import List, Tuple

import cv2

from exercise_registry import ExerciseEntry


MOTIVATION_LINES = [
    "Keep going!",
    "You got this!",
    "Strong reps!",
    "Great pace!",
    "Stay consistent!",
    "Focus and breathe.",
]


def draw_side_panel(
    frame, entries: List[ExerciseEntry], selected_idx: int, panel_width: int = 320
) -> List[Tuple[Tuple[int, int, int, int], int]]:
    height, width = frame.shape[:2]
    x0 = width - panel_width
    cv2.rectangle(frame, (x0, 0), (width, height), (30, 30, 30), -1)
    cv2.rectangle(frame, (x0, 0), (width, height), (80, 80, 80), 2)

    y = 30
    cv2.putText(frame, "Exercises", (x0 + 12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    y += 25

    clickable: List[Tuple[Tuple[int, int, int, int], int]] = []

    # Show a scrolling window of entries around the selected index.
    window_size = 10
    start = max(0, selected_idx - window_size // 2)
    end = min(len(entries), start + window_size)
    if end - start < window_size:
        start = max(0, end - window_size)

    for idx in range(start, end):
        entry = entries[idx]
        color = (0, 255, 180) if idx == selected_idx else (220, 220, 220)
        prefix = ">" if idx == selected_idx else " "
        line = f"{prefix} {entry.name}"
        card_top = y - 16
        card_bottom = y + 10
        card_left = x0 + 8
        card_right = width - 8
        if idx == selected_idx:
            cv2.rectangle(frame, (card_left, card_top), (card_right, card_bottom), (60, 60, 60), -1)
        cv2.putText(frame, line, (x0 + 12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1)
        clickable.append(((card_left, card_top, card_right, card_bottom), idx))
        y += 24

    y += 10
    hint = entries[selected_idx].view_hint if entries else ""
    cv2.putText(frame, f"View: {hint}", (x0 + 12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 180, 180), 1)
    return clickable


def draw_status_panel(frame, lines, origin=(10, 30)) -> None:
    x, y = origin
    for line in lines:
        cv2.putText(frame, line, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        y += 28


def get_motivation_line() -> str:
    idx = int(time.time()) % len(MOTIVATION_LINES)
    return MOTIVATION_LINES[idx]

