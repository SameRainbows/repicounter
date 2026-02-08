import sys
import time
from typing import Optional

import cv2
import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets

from bar_detection import BarDetector
from camera import CameraStream
from exercise_registry import ExerciseEntry, get_exercise_entries
from history import PoseHistory
from pose_detection import PoseDetector
from visualization import draw_bar, draw_joint_angles, draw_pose


class WorkoutPage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_runtime()

    def _setup_ui(self):
        self.setObjectName("WorkoutPage")
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        self.video_label = QtWidgets.QLabel("Camera feed")
        self.video_label.setAlignment(QtCore.Qt.AlignCenter)
        self.video_label.setMinimumSize(720, 480)
        self.video_label.setStyleSheet("background:#101214; border-radius:12px;")

        right_panel = QtWidgets.QVBoxLayout()
        right_panel.setSpacing(12)

        self.exercise_list = QtWidgets.QListWidget()
        self.exercise_list.setMinimumWidth(260)
        self.exercise_list.setStyleSheet(
            "QListWidget{background:#15181b;border:1px solid #2b2f33;border-radius:10px;color:#e6e6e6;}"
            "QListWidget::item{padding:8px;border-radius:6px;}"
            "QListWidget::item:selected{background:#1f6f5f;color:#ffffff;}"
        )

        self.stats_box = QtWidgets.QFrame()
        self.stats_box.setStyleSheet(
            "QFrame{background:#15181b;border:1px solid #2b2f33;border-radius:10px;color:#e6e6e6;}"
        )
        stats_layout = QtWidgets.QVBoxLayout(self.stats_box)
        stats_layout.setContentsMargins(12, 12, 12, 12)
        stats_layout.setSpacing(8)

        self.exercise_label = QtWidgets.QLabel("Exercise: -")
        self.reps_label = QtWidgets.QLabel("Reps: 0")
        self.phase_label = QtWidgets.QLabel("Phase: -")
        self.view_hint_label = QtWidgets.QLabel("View: -")
        self.motivation_label = QtWidgets.QLabel("Keep going!")
        self.warning_label = QtWidgets.QLabel("")
        self.warning_label.setStyleSheet("color:#ff9b9b;")

        for lbl in [
            self.exercise_label,
            self.reps_label,
            self.phase_label,
            self.view_hint_label,
            self.motivation_label,
            self.warning_label,
        ]:
            lbl.setStyleSheet("font-size:14px;")
            stats_layout.addWidget(lbl)

        right_panel.addWidget(QtWidgets.QLabel("Exercises"))
        right_panel.addWidget(self.exercise_list, 1)
        right_panel.addWidget(self.stats_box)

        layout.addWidget(self.video_label, 1)
        layout.addLayout(right_panel)

    def _setup_runtime(self):
        self.camera: Optional[CameraStream] = None
        self.detector = PoseDetector()
        self.history = PoseHistory(maxlen=120)
        self.bar_detector = BarDetector()
        self.entries = get_exercise_entries()
        self.selected_idx = 0
        self._last_selected_idx = 0
        self._last_motivation_change = 0.0
        self._motivation_lines = [
            "Keep going!",
            "You got this!",
            "Strong reps!",
            "Great pace!",
            "Stay consistent!",
            "Focus and breathe.",
        ]

        for entry in self.entries:
            item = QtWidgets.QListWidgetItem(entry.name)
            self.exercise_list.addItem(item)
        self.exercise_list.setCurrentRow(0)
        self.exercise_list.currentRowChanged.connect(self._on_exercise_changed)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._update_frame)
        self.timer.start(33)

    def start_camera(self):
        if self.camera is None:
            self.camera = CameraStream(camera_index=0, width=1280, height=720, target_fps=30)
            if not self.camera.open():
                self.warning_label.setText("Camera error")
                self.camera = None

    def stop_camera(self):
        if self.camera is not None:
            self.camera.release()
            self.camera = None

    def _on_exercise_changed(self, idx: int):
        if idx < 0 or idx >= len(self.entries):
            return
        self.selected_idx = idx

    def _update_frame(self):
        if self.camera is None:
            self.start_camera()
            if self.camera is None:
                return

        cam_frame = self.camera.read()
        if not cam_frame.ok:
            self.warning_label.setText("Camera error")
            return

        frame = cam_frame.frame
        pose = self.detector.process(frame, cam_frame.timestamp)
        self.history.append(pose)

        entry = self.entries[self.selected_idx]
        if self.selected_idx != self._last_selected_idx:
            entry.counter.reset()
            self.bar_detector.reset()
            self._last_selected_idx = self.selected_idx

        bar_y = self.bar_detector.update(frame) if entry.uses_bar else None
        state = entry.counter.update(pose, bar_y=bar_y)

        draw_pose(frame, pose)
        draw_joint_angles(frame, pose)
        if bar_y is not None:
            draw_bar(frame, bar_y)

        # Update stats UI
        self.exercise_label.setText(f"Exercise: {entry.name}")
        self.reps_label.setText(f"Reps: {state.rep_count}")
        self.phase_label.setText(f"Phase: {state.phase}")
        self.view_hint_label.setText(f"View: {entry.view_hint}")
        self.warning_label.setText(" | ".join(state.warnings[:2]) if state.warnings else "")

        now = time.time()
        if now - self._last_motivation_change > 4:
            idx = int(now) % len(self._motivation_lines)
            self.motivation_label.setText(self._motivation_lines[idx])
            self._last_motivation_change = now

        # Convert to QImage
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        image = QtGui.QImage(frame_rgb.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
        pixmap = QtGui.QPixmap.fromImage(image)
        self.video_label.setPixmap(pixmap.scaled(self.video_label.size(), QtCore.Qt.KeepAspectRatio))


class HomePage(QtWidgets.QWidget):
    start_clicked = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        title = QtWidgets.QLabel("AI Workout Tracker")
        title.setStyleSheet("font-size:28px;font-weight:700;color:#f2f2f2;")
        subtitle = QtWidgets.QLabel("Real-time form feedback and rep counting.")
        subtitle.setStyleSheet("font-size:14px;color:#b9c0c5;")

        button = QtWidgets.QPushButton("Start Workout")
        button.setStyleSheet(
            "QPushButton{background:#1f6f5f;color:white;padding:12px 24px;border-radius:10px;font-size:14px;}"
            "QPushButton:hover{background:#249b84;}"
        )
        button.clicked.connect(self.start_clicked.emit)

        layout.addStretch(1)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(button)
        layout.addStretch(2)


class SettingsPage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QtWidgets.QLabel("Settings")
        title.setStyleSheet("font-size:20px;font-weight:600;color:#f2f2f2;")
        layout.addWidget(title)

        info = QtWidgets.QLabel(
            "Tip: use a well-lit room and keep your full body visible for best results."
        )
        info.setStyleSheet("font-size:13px;color:#b9c0c5;")
        layout.addWidget(info)
        layout.addStretch(1)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Workout Tracker")
        self.resize(1280, 720)
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("QMainWindow{background:#0f1113;}")

        root = QtWidgets.QWidget()
        self.setCentralWidget(root)
        layout = QtWidgets.QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)

        nav = QtWidgets.QFrame()
        nav.setFixedWidth(200)
        nav.setStyleSheet("QFrame{background:#0c0e10;border-right:1px solid #22262a;}")
        nav_layout = QtWidgets.QVBoxLayout(nav)
        nav_layout.setContentsMargins(12, 20, 12, 12)
        nav_layout.setSpacing(10)

        self.home_btn = QtWidgets.QPushButton("Home")
        self.workout_btn = QtWidgets.QPushButton("Workout")
        self.settings_btn = QtWidgets.QPushButton("Settings")
        for btn in [self.home_btn, self.workout_btn, self.settings_btn]:
            btn.setStyleSheet(
                "QPushButton{background:#15181b;color:#e6e6e6;padding:10px;border-radius:8px;text-align:left;}"
                "QPushButton:hover{background:#1a1f24;}"
            )
            nav_layout.addWidget(btn)
        nav_layout.addStretch(1)

        self.stack = QtWidgets.QStackedWidget()
        self.home_page = HomePage()
        self.workout_page = WorkoutPage()
        self.settings_page = SettingsPage()
        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.workout_page)
        self.stack.addWidget(self.settings_page)

        layout.addWidget(nav)
        layout.addWidget(self.stack, 1)

        self.home_btn.clicked.connect(lambda: self._switch_page(0))
        self.workout_btn.clicked.connect(lambda: self._switch_page(1))
        self.settings_btn.clicked.connect(lambda: self._switch_page(2))
        self.home_page.start_clicked.connect(lambda: self._switch_page(1))

    def _switch_page(self, idx: int):
        self.stack.setCurrentIndex(idx)
        if idx == 1:
            self.workout_page.start_camera()

    def closeEvent(self, event):
        self.workout_page.stop_camera()
        super().closeEvent(event)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

