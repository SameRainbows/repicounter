import cv2
import numpy as np

from bar_detection import BarDetector
from camera import CameraStream
from exercise_registry import get_exercise_entries
from history import PoseHistory
from pose_detection import PoseDetector
from ui import draw_side_panel, draw_status_panel, get_motivation_line
from visualization import draw_bar, draw_joint_angles, draw_pose


def main():
    window_name = "AI Workout Tracker"
    camera = CameraStream(camera_index=0, width=1280, height=720, target_fps=30)
    if not camera.open():
        print("Error: Could not open webcam.")
        return

    detector = PoseDetector()
    history = PoseHistory(maxlen=120)
    bar_detector = BarDetector()
    entries = get_exercise_entries()
    selected_idx = 0
    last_selected_idx = selected_idx

    highlight = {
        "left_shoulder": (255, 0, 0),
        "right_shoulder": (255, 0, 0),
        "left_wrist": (0, 255, 255),
        "right_wrist": (0, 255, 255),
        "left_hip": (255, 255, 0),
        "right_hip": (255, 255, 0),
        "left_ankle": (255, 0, 255),
        "right_ankle": (255, 0, 255),
        "left_knee": (0, 165, 255),
        "right_knee": (0, 165, 255),
    }

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    click_state = {"x": None, "y": None}

    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            click_state["x"] = x
            click_state["y"] = y

    cv2.setMouseCallback(window_name, on_mouse)
    while True:
        if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
            break
        cam_frame = camera.read()
        if not cam_frame.ok:
            blank = np.zeros((480, 640, 3), dtype=np.uint8)
            draw_status_panel(blank, ["Camera error"], origin=(10, 30))
            cv2.imshow(window_name, blank)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
            continue

        frame = cam_frame.frame
        pose = detector.process(frame, cam_frame.timestamp)
        history.append(pose)

        entry = entries[selected_idx]
        if selected_idx != last_selected_idx:
            entry.counter.reset()
            bar_detector.reset()
            last_selected_idx = selected_idx

        bar_y = bar_detector.update(frame) if entry.uses_bar else None
        state = entry.counter.update(pose, bar_y=bar_y)

        draw_pose(frame, pose, highlight=highlight)
        if bar_y is not None:
            draw_bar(frame, bar_y)
        lines = [
            f"Exercise: {entry.name}",
            f"Reps: {state.rep_count}",
            f"Phase: {state.phase}",
            get_motivation_line(),
            "Keys: Up/Down change, Q quit",
        ]
        for warning in state.warnings[:3]:
            lines.append(f"Warning: {warning}")
        draw_status_panel(frame, lines, origin=(10, 30))
        clickable = draw_side_panel(frame, entries, selected_idx)
        draw_joint_angles(frame, pose)

        cv2.imshow(window_name, frame)
        if click_state["x"] is not None and click_state["y"] is not None:
            cx, cy = click_state["x"], click_state["y"]
            click_state["x"] = None
            click_state["y"] = None
            for (left, top, right, bottom), idx in clickable:
                if left <= cx <= right and top <= cy <= bottom:
                    selected_idx = idx
                    break

        key = cv2.waitKey(1)
        if key & 0xFF == ord("q"):
            break
        if key in [2490368, ord("w")]:
            selected_idx = max(0, selected_idx - 1)
        elif key in [2621440, ord("s")]:
            selected_idx = min(len(entries) - 1, selected_idx + 1)

    camera.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

