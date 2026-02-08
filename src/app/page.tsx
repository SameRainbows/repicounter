"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { BarDetector } from "../lib/barDetection";
import { drawBar, drawJointAngles, drawPose } from "../lib/draw";
import type { ExerciseBase } from "../lib/exercises";
import { PassiveCalibrator, PushUpCounter } from "../lib/exercises";
import { loadPoseLandmarker, toPoseFrame } from "../lib/pose";
import { getExerciseEntries, type ExerciseEntry } from "../lib/registry";
import { playBeep } from "../lib/audio";
import { clearSessions, exportSessionsCsv, loadSessions, saveSession, type SessionLog } from "../lib/storage";

const MOTIVATION_LINES = [
  "Keep going!",
  "You got this!",
  "Strong reps!",
  "Great pace!",
  "Stay consistent!",
  "Focus and breathe."
];

type SettingsState = {
  mirror: boolean;
  showAngles: boolean;
  showSkeleton: boolean;
  soundOnRep: boolean;
  targetReps: number;
  targetMinutes: number;
};

export default function Home() {
  const entries = useMemo(() => getExerciseEntries(), []);
  const [activePage, setActivePage] = useState<"home" | "workout" | "settings">("home");
  const [selectedId, setSelectedId] = useState(entries[0]?.id ?? "");
  const [counter, setCounter] = useState<ExerciseBase>(() =>
    entries[0] ? (entries[0].createCounter() as ExerciseBase) : ({} as ExerciseBase)
  );
  const [stats, setStats] = useState({
    reps: 0,
    phase: "-",
    warnings: [] as string[],
    isRepValid: true
  });
  const [viewHint, setViewHint] = useState(entries[0]?.viewHint ?? "");
  const [status, setStatus] = useState("Idle");
  const [isRunning, setIsRunning] = useState(false);
  const [sessionStart, setSessionStart] = useState<number | null>(null);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [motivation, setMotivation] = useState(MOTIVATION_LINES[0]);
  const [sessions, setSessions] = useState<SessionLog[]>([]);
  const [exerciseTotals, setExerciseTotals] = useState<Record<string, number>>({});
  const [settings, setSettings] = useState<SettingsState>({
    mirror: true,
    showAngles: true,
    showSkeleton: true,
    soundOnRep: true,
    targetReps: 20,
    targetMinutes: 10
  });

  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const analysisCanvasRef = useRef<HTMLCanvasElement>(null);
  const barDetectorRef = useRef(new BarDetector());
  const calibratorRef = useRef(new PassiveCalibrator());
  const lastRepCountRef = useRef(0);
  const frameRef = useRef<number | null>(null);
  const landmarkerReadyRef = useRef(false);

  useEffect(() => {
    setSessions(loadSessions());
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    const entry = entries.find((item) => item.id === selectedId);
    if (!entry) return;
    setViewHint(entry.viewHint);
    const nextCounter = entry.createCounter() as ExerciseBase;
    setCounter(nextCounter);
    setStats({ reps: 0, phase: "-", warnings: [], isRepValid: true });
    lastRepCountRef.current = 0;
    calibratorRef.current.reset();
    barDetectorRef.current.reset();
  }, [selectedId, entries]);

  useEffect(() => {
    if (!isRunning) {
      return;
    }
    const interval = window.setInterval(() => {
      if (sessionStart !== null) {
        setElapsedSec((Date.now() - sessionStart) / 1000);
      }
    }, 250);
    return () => window.clearInterval(interval);
  }, [isRunning, sessionStart]);

  useEffect(() => {
    if (!isRunning) return;
    const idx = Math.floor(Date.now() / 1000) % MOTIVATION_LINES.length;
    setMotivation(MOTIVATION_LINES[idx]);
  }, [elapsedSec, isRunning]);

  const startCamera = async () => {
    if (landmarkerReadyRef.current) {
      return;
    }
    try {
      setStatus("Requesting camera...");
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 1280, height: 720 } });
      const video = videoRef.current;
      if (!video) {
        return;
      }
      video.srcObject = stream;
      await video.play();
      await loadPoseLandmarker();
      landmarkerReadyRef.current = true;
      setStatus("Camera ready");
      if (!isRunning) {
        setIsRunning(true);
        setSessionStart(Date.now());
        setElapsedSec(0);
      }
      startLoop();
    } catch (err) {
      setStatus("Camera access denied");
    }
  };

  const stopCamera = () => {
    const video = videoRef.current;
    if (video?.srcObject) {
      const tracks = (video.srcObject as MediaStream).getTracks();
      tracks.forEach((track) => track.stop());
      video.srcObject = null;
    }
    landmarkerReadyRef.current = false;
    setIsRunning(false);
    setStatus("Stopped");
    if (frameRef.current) {
      cancelAnimationFrame(frameRef.current);
    }
  };

  const startLoop = () => {
    const loop = async () => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      const analysisCanvas = analysisCanvasRef.current;
      if (!video || !canvas || !analysisCanvas || !landmarkerReadyRef.current) {
        frameRef.current = requestAnimationFrame(loop);
        return;
      }
      if (video.readyState < 2) {
        frameRef.current = requestAnimationFrame(loop);
        return;
      }

      const width = video.videoWidth;
      const height = video.videoHeight;
      canvas.width = width;
      canvas.height = height;
      analysisCanvas.width = width;
      analysisCanvas.height = height;

      const ctx = canvas.getContext("2d");
      const analysisCtx = analysisCanvas.getContext("2d");
      if (!ctx || !analysisCtx) {
        frameRef.current = requestAnimationFrame(loop);
        return;
      }
      ctx.clearRect(0, 0, width, height);
      analysisCtx.drawImage(video, 0, 0, width, height);

      const landmarker = await loadPoseLandmarker();
      const result = landmarker.detectForVideo(video, performance.now());
      const landmarks = result.landmarks?.[0];
      const pose = toPoseFrame(landmarks, performance.now(), [width, height]);

      const entry = entries.find((item) => item.id === selectedId);
      let barY: number | null = null;
      if (entry?.usesBar) {
        const imageData = analysisCtx.getImageData(0, 0, width, height);
        barY = barDetectorRef.current.update(imageData);
      }

      let exerciseState = {
        repCount: stats.reps,
        phase: stats.phase,
        warnings: stats.warnings,
        isRepValid: stats.isRepValid
      };
      if (counter && typeof counter.update === "function") {
        if (counter instanceof PushUpCounter) {
          const calibration = calibratorRef.current.update(pose);
          if (calibration) {
            counter.setCalibration(calibration);
          }
        }
        exerciseState = counter.update(pose, barY);
      }
      setStats({
        reps: exerciseState.repCount,
        phase: exerciseState.phase,
        warnings: exerciseState.warnings,
        isRepValid: exerciseState.isRepValid
      });

      if (exerciseState.repCount > lastRepCountRef.current) {
        if (settings.soundOnRep) {
          playBeep();
        }
        const entryId = entry?.id ?? "unknown";
        setExerciseTotals((prev) => ({
          ...prev,
          [entryId]: (prev[entryId] ?? 0) + 1
        }));
      }
      lastRepCountRef.current = exerciseState.repCount;

      if (settings.showSkeleton) {
        drawPose(ctx, pose);
      }
      if (settings.showAngles) {
        drawJointAngles(ctx, pose);
      }
      if (barY !== null) {
        drawBar(ctx, barY, [width, height]);
      }

      frameRef.current = requestAnimationFrame(loop);
    };
    frameRef.current = requestAnimationFrame(loop);
  };

  const resetSession = () => {
    setExerciseTotals({});
    setElapsedSec(0);
    setSessionStart(Date.now());
    setStats({ reps: 0, phase: "-", warnings: [], isRepValid: true });
    lastRepCountRef.current = 0;
    counter.reset();
  };

  const finishSession = () => {
    if (sessionStart === null) {
      return;
    }
    const ended = Date.now();
    const session: SessionLog = {
      id: `session-${ended}`,
      startedAt: sessionStart,
      endedAt: ended,
      durationSec: (ended - sessionStart) / 1000,
      exerciseTotals
    };
    saveSession(session);
    setSessions(loadSessions());
    setStatus("Session saved");
  };

  const exportCsv = () => {
    const csv = exportSessionsCsv(sessions);
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "workout-sessions.csv";
    link.click();
    URL.revokeObjectURL(url);
  };

  const targetReached =
    (settings.targetReps > 0 && stats.reps >= settings.targetReps) ||
    (settings.targetMinutes > 0 && elapsedSec >= settings.targetMinutes * 60);

  const entry = entries.find((item) => item.id === selectedId);

  return (
    <div className="app-shell">
      <nav className="nav">
        <button className={activePage === "home" ? "active" : ""} onClick={() => setActivePage("home")}>
          Home
        </button>
        <button className={activePage === "workout" ? "active" : ""} onClick={() => setActivePage("workout")}>
          Workout
        </button>
        <button className={activePage === "settings" ? "active" : ""} onClick={() => setActivePage("settings")}>
          Settings
        </button>
        <div className="panel">
          <div className="muted">Status</div>
          <div>{status}</div>
          <div className="badge">{isRunning ? "Live" : "Idle"}</div>
        </div>
      </nav>

      <main className="main">
        {activePage === "home" && (
          <div className="panel">
            <h1>AI Workout Tracker</h1>
            <p className="muted">Real-time form feedback and rep counting with your camera.</p>
            <div className="row" style={{ marginTop: 12 }}>
              <button
                className="primary"
                onClick={() => {
                  setActivePage("workout");
                  startCamera();
                }}
              >
                Start Workout
              </button>
              <button className="secondary" onClick={() => setActivePage("settings")}>
                Configure
              </button>
            </div>
          </div>
        )}

        {activePage === "workout" && (
          <>
            <div className="video-shell panel">
              <video
                ref={videoRef}
                muted
                playsInline
                style={{ transform: settings.mirror ? "scaleX(-1)" : "none" }}
              />
              <canvas
                ref={canvasRef}
                style={{ transform: settings.mirror ? "scaleX(-1)" : "none" }}
              />
              <canvas ref={analysisCanvasRef} style={{ display: "none" }} />
            </div>

            <div className="panel controls">
              <button className="primary" onClick={startCamera}>
                Start Camera
              </button>
              <button className="secondary" onClick={stopCamera}>
                Stop Camera
              </button>
              <button className="secondary" onClick={resetSession}>
                Reset Session
              </button>
              <button className="secondary" onClick={finishSession}>
                Save Session
              </button>
            </div>

            <div className="panel stat-grid">
              <div className="stat-card">
                <div className="muted">Exercise</div>
                <div>{entry?.name ?? "-"}</div>
              </div>
              <div className="stat-card">
                <div className="muted">Reps</div>
                <div>{stats.reps}</div>
              </div>
              <div className="stat-card">
                <div className="muted">Phase</div>
                <div>{stats.phase}</div>
              </div>
              <div className="stat-card">
                <div className="muted">View</div>
                <div>{viewHint}</div>
              </div>
              <div className="stat-card">
                <div className="muted">Timer</div>
                <div>{elapsedSec.toFixed(1)}s</div>
              </div>
              <div className="stat-card">
                <div className="muted">Motivation</div>
                <div>{motivation}</div>
              </div>
            </div>

            <div className="panel">
              <div className="row">
                <span className="badge">Warnings</span>
                {stats.isRepValid ? (
                  <span className="success">Rep valid</span>
                ) : (
                  <span className="warning">Rep not counted</span>
                )}
              </div>
              {stats.warnings.length === 0 ? (
                <div className="muted">No warnings</div>
              ) : (
                stats.warnings.map((warning, idx) => (
                  <div className="warning" key={`${warning}-${idx}`}>
                    {warning}
                  </div>
                ))
              )}
              {targetReached && (
                <div className="success" style={{ marginTop: 8 }}>
                  Target reached! Great work.
                </div>
              )}
            </div>
          </>
        )}

        {activePage === "settings" && (
          <div className="panel">
            <h2>Settings</h2>
            <div className="row">
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={settings.mirror}
                  onChange={(e) => setSettings((prev) => ({ ...prev, mirror: e.target.checked }))}
                />
                Mirror camera
              </label>
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={settings.showAngles}
                  onChange={(e) => setSettings((prev) => ({ ...prev, showAngles: e.target.checked }))}
                />
                Show joint angles
              </label>
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={settings.showSkeleton}
                  onChange={(e) => setSettings((prev) => ({ ...prev, showSkeleton: e.target.checked }))}
                />
                Show skeleton
              </label>
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={settings.soundOnRep}
                  onChange={(e) => setSettings((prev) => ({ ...prev, soundOnRep: e.target.checked }))}
                />
                Sound on rep
              </label>
            </div>
            <div className="row" style={{ marginTop: 12 }}>
              <label className="toggle">
                Target reps
                <input
                  type="number"
                  min={0}
                  value={settings.targetReps}
                  onChange={(e) => setSettings((prev) => ({ ...prev, targetReps: Number(e.target.value) }))}
                />
              </label>
              <label className="toggle">
                Target minutes
                <input
                  type="number"
                  min={0}
                  value={settings.targetMinutes}
                  onChange={(e) => setSettings((prev) => ({ ...prev, targetMinutes: Number(e.target.value) }))}
                />
              </label>
            </div>
            <div className="panel" style={{ marginTop: 12 }}>
              <div className="row">
                <button className="secondary" onClick={exportCsv}>
                  Export CSV
                </button>
                <button
                  className="secondary"
                  onClick={() => {
                    clearSessions();
                    setSessions([]);
                  }}
                >
                  Clear local view
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      <aside className="right-panel">
        <div className="panel">
          <div className="row">
            <span className="badge">Exercises</span>
            <span className="muted">Click to switch</span>
          </div>
          <div className="exercise-list">
            {entries.map((item) => (
              <div
                key={item.id}
                className={`exercise-item ${item.id === selectedId ? "active" : ""}`}
                onClick={() => setSelectedId(item.id)}
              >
                {item.name}
              </div>
            ))}
          </div>
        </div>
        <div className="panel">
          <div className="row">
            <span className="badge">Session totals</span>
            <span className="muted">{Object.keys(exerciseTotals).length} exercises</span>
          </div>
          {Object.keys(exerciseTotals).length === 0 ? (
            <div className="muted">No reps recorded yet.</div>
          ) : (
            Object.entries(exerciseTotals).map(([id, reps]) => {
              const label = entries.find((e) => e.id === id)?.name ?? id;
              return (
                <div key={id} className="row" style={{ justifyContent: "space-between" }}>
                  <span>{label}</span>
                  <span>{reps}</span>
                </div>
              );
            })
          )}
        </div>
        <div className="panel">
          <div className="row">
            <span className="badge">Recent sessions</span>
            <span className="muted">{sessions.length}</span>
          </div>
          <div className="log-list">
            {sessions.length === 0 && <div className="muted">No saved sessions yet.</div>}
            {sessions.slice(0, 6).map((session) => (
              <div key={session.id} className="log-item">
                <div>{new Date(session.startedAt).toLocaleString()}</div>
                <div className="muted">{session.durationSec.toFixed(1)}s</div>
              </div>
            ))}
          </div>
        </div>
      </aside>
    </div>
  );
}

