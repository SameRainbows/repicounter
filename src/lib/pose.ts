import { FilesetResolver, PoseLandmarker, type NormalizedLandmark } from "@mediapipe/tasks-vision";
import type { Landmark2D, PoseFrame } from "./poseTypes";
import { POSE_LANDMARK_NAMES } from "./poseTypes";

let cachedLandmarker: PoseLandmarker | null = null;

export async function loadPoseLandmarker(): Promise<PoseLandmarker> {
  if (cachedLandmarker) {
    return cachedLandmarker;
  }

  const vision = await FilesetResolver.forVisionTasks(
    "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22/wasm"
  );
  cachedLandmarker = await PoseLandmarker.createFromOptions(vision, {
    baseOptions: {
      modelAssetPath:
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
    },
    runningMode: "VIDEO",
    numPoses: 1,
    minPoseDetectionConfidence: 0.5,
    minPosePresenceConfidence: 0.5,
    minTrackingConfidence: 0.5
  });

  return cachedLandmarker;
}

export function toPoseFrame(
  landmarks: NormalizedLandmark[] | undefined,
  timestampMs: number,
  imageSize: [number, number],
  visibilityThreshold = 0.5
): PoseFrame {
  const [width, height] = imageSize;
  const rawLandmarks: Record<string, Landmark2D | null> = {};
  const normalizedLandmarks: Record<string, Landmark2D | null> = {};
  POSE_LANDMARK_NAMES.forEach((name) => {
    rawLandmarks[name] = null;
    normalizedLandmarks[name] = null;
  });

  if (!landmarks || landmarks.length !== POSE_LANDMARK_NAMES.length) {
    return {
      timestamp: timestampMs / 1000,
      imageSize: [width, height],
      rawLandmarks,
      normalizedLandmarks,
      valid: false
    };
  }

  landmarks.forEach((lm, idx) => {
    const name = POSE_LANDMARK_NAMES[idx];
    if (!name) {
      return;
    }
    if ((lm.visibility ?? 0) < visibilityThreshold) {
      rawLandmarks[name] = null;
      return;
    }
    rawLandmarks[name] = {
      x: lm.x,
      y: lm.y,
      z: lm.z ?? 0,
      visibility: lm.visibility ?? 0
    };
  });

  const normalized = normalizeLandmarks(rawLandmarks);
  Object.assign(normalizedLandmarks, normalized);

  return {
    timestamp: timestampMs / 1000,
    imageSize: [width, height],
    rawLandmarks,
    normalizedLandmarks,
    valid: true
  };
}

function normalizeLandmarks(rawLandmarks: Record<string, Landmark2D | null>): Record<string, Landmark2D | null> {
  const leftHip = rawLandmarks.left_hip;
  const rightHip = rawLandmarks.right_hip;
  const leftShoulder = rawLandmarks.left_shoulder;
  const rightShoulder = rawLandmarks.right_shoulder;

  if (!leftHip || !rightHip) {
    return { ...rawLandmarks };
  }

  const centerX = (leftHip.x + rightHip.x) / 2;
  const centerY = (leftHip.y + rightHip.y) / 2;
  const scale =
    leftShoulder && rightShoulder
      ? Math.abs(leftShoulder.x - rightShoulder.x)
      : Math.abs(leftHip.x - rightHip.x);
  const safeScale = scale < 1e-5 ? 1 : scale;

  const normalized: Record<string, Landmark2D | null> = {};
  Object.entries(rawLandmarks).forEach(([name, lm]) => {
    if (!lm) {
      normalized[name] = null;
      return;
    }
    normalized[name] = {
      x: (lm.x - centerX) / safeScale,
      y: (lm.y - centerY) / safeScale,
      z: lm.z / safeScale,
      visibility: lm.visibility
    };
  });
  return normalized;
}

