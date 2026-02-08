# AI Workout Tracker (Web + Desktop)

This project now ships as a **Vercel-ready web app** and a **desktop prototype**. Both versions run fully on-device using your camera and MediaPipe Pose for real-time rep counting and form feedback.

## Web App (Vercel-ready)

The web app runs in the browser, uses your camera via WebRTC, and performs pose detection client-side.

### Install & Run

```
npm install
npm run dev
```

### Deploy on Vercel

- Import the repo in Vercel.
- Framework preset: **Next.js**
- Build command: `npm run build`
- Output: default
- **No environment variables required** for the default setup.

### Web Features

- Live camera feed + pose overlay
- Rep counting + phase tracking
- Exercise library (30+ exercises)
- Bar detection for pull-ups/chin-ups
- Session timer + goals
- Rep warnings + valid/invalid rep feedback
- Session history stored locally + CSV export

---

## How It Works

- **Camera Layer** (`camera.py`): OpenCV webcam capture with FPS stabilization and graceful failure handling.
- **Pose Detection Layer** (`pose_detection.py`): MediaPipe Pose integration. Extracts 2D landmarks, filters low-visibility points, and normalizes coordinates to a body-centered frame.
- **Pose History Buffer** (`history.py`): Rolling buffer for recent poses to support motion trend analysis.
- **Geometry Utilities** (`geometry.py`): Joint angles, distances, and simple velocity calculation with clear math comments.
- **Calibration**: Passive calibration inside each exercise (jumping jacks use a short calibration window).
- **Exercise System** (`exercises/`):
  - `base.py`: Base exercise definition.
  - `jumping_jack.py`: Jumping jack state machine using arm height and leg spread.
  - `squat.py`: Squat counter using knee angle and hip drop.
  - `pullup.py`: Pull-up / chin-up counter using bar detection + chin height.
  - `situp.py`: Sit-up counter using torso angle and hip raise.
  - `arm_raise.py`, `leg_spread.py`, `knee_raise.py`, `lunge.py`, `torso_bend.py`: Modular counters for additional exercise types.
  - `hold.py`: Generic isometric hold counter.
- **Exercise Registry** (`exercise_registry.py`): Central list of 35 exercises with view hints.
- **UI** (`ui.py`): Side panel menu + status overlay.
- **Bar Detection** (`bar_detection.py`): Heuristic horizontal bar detection using edges + Hough lines.
- **Visualization** (`visualization.py`): Skeleton drawing, joint highlighting, and on-screen overlays.
- **Main App** (`app.py`): Wires everything together and runs the live UI.

### Jumping Jack Definition

Jumping jacks are detected using:

- **Arm raise**: Wrists move above shoulders by a calibrated delta.
- **Leg spread**: Ankles move apart relative to a baseline standing width.

Movement phases are tracked with a state machine:

- `CLOSED` → `OPEN` → `CLOSED`

A repetition is counted only if:

- Arms are raised while legs spread,
- Arms return down while legs close.

## Desktop Install Dependencies

From the project root:

```
pip install -r requirements.txt
```

## Run the Desktop Prototype

```
python app.py
```

Press **Q** to quit.

## Run the Desktop App (GUI)

```
python gui_app.py
```

This launches a multi-page desktop app with a navigation sidebar, exercise list, and live video view.

### Exercise Switching

- **Up/Down** = change exercise
- **Q** = quit

## Add a New Exercise (Desktop)

1. Create a new file in `exercises/`, e.g. `squat.py`.
2. Subclass `ExerciseBase` and implement an `update()` method.
3. Define:
   - required joints
   - calibration needs (if any)
   - state machine phases
   - thresholds for valid reps
4. Wire the new exercise in `app.py`.

## Exercises Included (40)

Jumping Jack, Step Jack, Half Jack, Seal Jack, Fast Jacks, Slow Jacks, Low Jacks, Power Jacks,  
Squat, Wide Squat, Narrow Squat, Half Squat, Pulse Squat, Jump Squat, Box Squat, Tempo Squat,  
Forward Lunge, Reverse Lunge, Split Squat, Side Lunge, Split Squat Hold,  
High Knees, Marching, Knee Tucks, Side Steps, Skater Steps,  
Arm Raises, Overhead Raises, Lateral Raises, Arm Pulses, Side Bends, Toe Touches,  
Sit-Up, Plank Hold, Side Plank Hold, Wall Sit Hold, Glute Bridge, Hip Hinge,  
Pull-Up, Chin-Up

## Notes

- Jumping jacks and squats work best with the full body visible in a front view.
- Sit-ups, planks, and lunges work best with a side view (phone on the floor next to you).
- Bar exercises require a visible horizontal bar in frame; the system detects the bar automatically.
- Pull-ups/chin-ups require a visible horizontal bar in frame; the system detects the bar automatically.
- Calibration happens automatically at startup for jumping jacks; stand relaxed for ~2 seconds.
- No data is saved or uploaded.

