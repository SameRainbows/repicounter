import type { Landmark2D, PoseFrame } from "./poseTypes";
import { angleDegrees, computeVelocity, distance2d } from "./geometry";

export type ExerciseState = {
  repCount: number;
  phase: string;
  warnings: string[];
  isRepValid: boolean;
};

export interface ExerciseBase {
  name: string;
  requiredJoints: string[];
  update(pose: PoseFrame, barY?: number | null): ExerciseState;
  reset(): void;
}

const median = (values: number[]): number => {
  if (!values.length) {
    return 0;
  }
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid];
};

export type CalibrationResult = {
  topElbowAngle: number;
  shoulderYTop: number;
  hipYTop: number;
  torsoLength: number;
};

export class PassiveCalibrator {
  private durationMs: number;
  private startTime: number | null = null;
  private elbowAngles: number[] = [];
  private shoulderYs: number[] = [];
  private hipYs: number[] = [];
  private torsoLengths: number[] = [];

  constructor(durationSeconds = 3) {
    this.durationMs = durationSeconds * 1000;
  }

  reset(): void {
    this.startTime = null;
    this.elbowAngles = [];
    this.shoulderYs = [];
    this.hipYs = [];
    this.torsoLengths = [];
  }

  update(pose: PoseFrame): CalibrationResult | null {
    if (!pose.valid) {
      return null;
    }
    if (this.startTime === null) {
      this.startTime = performance.now();
    }

    const lm = pose.rawLandmarks;
    const required = [
      "left_shoulder",
      "right_shoulder",
      "left_elbow",
      "right_elbow",
      "left_wrist",
      "right_wrist",
      "left_hip",
      "right_hip"
    ];
    if (required.some((k) => !lm[k])) {
      return null;
    }

    const leftElbowAngle = angleDegrees(lm.left_shoulder!, lm.left_elbow!, lm.left_wrist!);
    const rightElbowAngle = angleDegrees(lm.right_shoulder!, lm.right_elbow!, lm.right_wrist!);
    const elbowAngle = (leftElbowAngle + rightElbowAngle) / 2;
    this.elbowAngles.push(elbowAngle);

    const shoulderY = (lm.left_shoulder!.y + lm.right_shoulder!.y) / 2;
    const hipY = (lm.left_hip!.y + lm.right_hip!.y) / 2;
    this.shoulderYs.push(shoulderY);
    this.hipYs.push(hipY);
    this.torsoLengths.push(distance2d(lm.left_shoulder!, lm.left_hip!));

    if (performance.now() - this.startTime < this.durationMs) {
      return null;
    }

    const torsoLength = Math.max(median(this.torsoLengths), 1e-5);
    return {
      topElbowAngle: median(this.elbowAngles),
      shoulderYTop: median(this.shoulderYs),
      hipYTop: median(this.hipYs),
      torsoLength
    };
  }
}

export class JumpingJackCounter implements ExerciseBase {
  name = "jumping_jack";
  requiredJoints = [
    "left_shoulder",
    "right_shoulder",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_ankle",
    "right_ankle"
  ];
  repCount = 0;
  phase = "CALIBRATING";
  private thresholds: {
    hipWidth: number;
    baselineAnkleDist: number;
    armRaiseDelta: number;
    legSpreadDelta: number;
  } | null = null;
  private startTime: number | null = null;
  private hipWidths: number[] = [];
  private ankleDists: number[] = [];
  private shoulderYs: number[] = [];
  private openFrames = 0;
  private closeFrames = 0;
  private calibrationMs: number;
  private armRaiseFactor: number;
  private legSpreadFactor: number;

  constructor(calibrationSeconds = 2, armRaiseFactor = 0.6, legSpreadFactor = 0.7) {
    this.calibrationMs = calibrationSeconds * 1000;
    this.armRaiseFactor = armRaiseFactor;
    this.legSpreadFactor = legSpreadFactor;
  }

  reset(): void {
    this.repCount = 0;
    this.phase = "CALIBRATING";
    this.thresholds = null;
    this.startTime = null;
    this.hipWidths = [];
    this.ankleDists = [];
    this.shoulderYs = [];
    this.openFrames = 0;
    this.closeFrames = 0;
  }

  update(pose: PoseFrame): ExerciseState {
    const warnings: string[] = [];
    if (!pose.valid) {
      return { repCount: this.repCount, phase: this.phase, warnings: ["No pose detected"], isRepValid: true };
    }

    const lm = pose.rawLandmarks;
    if (this.requiredJoints.some((k) => !lm[k])) {
      return { repCount: this.repCount, phase: this.phase, warnings: ["Body not fully visible"], isRepValid: true };
    }

    const leftShoulder = lm.left_shoulder!;
    const rightShoulder = lm.right_shoulder!;
    const leftWrist = lm.left_wrist!;
    const rightWrist = lm.right_wrist!;
    const leftHip = lm.left_hip!;
    const rightHip = lm.right_hip!;
    const leftAnkle = lm.left_ankle!;
    const rightAnkle = lm.right_ankle!;

    const shoulderY = (leftShoulder.y + rightShoulder.y) / 2;
    const hipWidth = distance2d(leftHip, rightHip);
    const ankleDist = distance2d(leftAnkle, rightAnkle);

    if (!this.thresholds) {
      if (this.startTime === null) {
        this.startTime = performance.now();
      }
      this.hipWidths.push(hipWidth);
      this.ankleDists.push(ankleDist);
      this.shoulderYs.push(shoulderY);
      if (performance.now() - this.startTime < this.calibrationMs) {
        return { repCount: this.repCount, phase: "CALIBRATING", warnings: ["Calibrating..."], isRepValid: true };
      }
      const hip = Math.max(median(this.hipWidths), 1e-5);
      const baseline = median(this.ankleDists);
      this.thresholds = {
        hipWidth: hip,
        baselineAnkleDist: baseline,
        armRaiseDelta: this.armRaiseFactor * hip,
        legSpreadDelta: this.legSpreadFactor * hip
      };
      this.phase = "CLOSED";
    }

    const thresholds = this.thresholds!;
    const wristAvgY = (leftWrist.y + rightWrist.y) / 2;
    const armsUp = shoulderY - wristAvgY >= thresholds.armRaiseDelta;
    const armsDown = wristAvgY - shoulderY >= 0.15 * thresholds.hipWidth;
    const legsApart = ankleDist >= thresholds.baselineAnkleDist + thresholds.legSpreadDelta;
    const legsTogether = ankleDist <= thresholds.baselineAnkleDist + 0.2 * thresholds.hipWidth;

    if (this.phase === "CLOSED") {
      if (armsUp && legsApart) {
        this.openFrames += 1;
        if (this.openFrames >= 2) {
          this.phase = "OPEN";
          this.openFrames = 0;
        }
      } else {
        this.openFrames = 0;
      }
    } else if (this.phase === "OPEN") {
      if (armsDown && legsTogether) {
        this.closeFrames += 1;
        if (this.closeFrames >= 2) {
          this.repCount += 1;
          this.phase = "CLOSED";
          this.closeFrames = 0;
        }
      } else {
        this.closeFrames = 0;
      }
    }

    if (!armsUp && this.phase === "OPEN") {
      warnings.push("Raise arms higher");
    }
    if (!legsApart && this.phase === "OPEN") {
      warnings.push("Spread legs wider");
    }

    return { repCount: this.repCount, phase: this.phase, warnings, isRepValid: true };
  }
}

export class ArmRaiseCounter implements ExerciseBase {
  name = "arm_raise";
  requiredJoints = ["left_shoulder", "right_shoulder", "left_wrist", "right_wrist"];
  repCount = 0;
  phase = "DOWN";
  private raiseDelta: number;
  private lowerDelta: number;
  private shoulderWidth: number | null = null;

  constructor(raiseDelta = 0.45, lowerDelta = 0.15) {
    this.raiseDelta = raiseDelta;
    this.lowerDelta = lowerDelta;
  }

  reset(): void {
    this.repCount = 0;
    this.phase = "DOWN";
    this.shoulderWidth = null;
  }

  update(pose: PoseFrame): ExerciseState {
    const warnings: string[] = [];
    if (!pose.valid) {
      return { repCount: this.repCount, phase: this.phase, warnings: ["No pose detected"], isRepValid: true };
    }
    const lm = pose.rawLandmarks;
    if (this.requiredJoints.some((k) => !lm[k])) {
      return { repCount: this.repCount, phase: this.phase, warnings: ["Arms not visible"], isRepValid: true };
    }
    const leftShoulder = lm.left_shoulder!;
    const rightShoulder = lm.right_shoulder!;
    const leftWrist = lm.left_wrist!;
    const rightWrist = lm.right_wrist!;
    const shoulderY = (leftShoulder.y + rightShoulder.y) / 2;
    const wristY = (leftWrist.y + rightWrist.y) / 2;
    const width = distance2d(leftShoulder, rightShoulder);
    if (this.shoulderWidth === null) {
      this.shoulderWidth = Math.max(width, 1e-5);
    }

    const armRaise = (shoulderY - wristY) / this.shoulderWidth;
    const armLower = (wristY - shoulderY) / this.shoulderWidth;

    if (this.phase === "DOWN") {
      if (armRaise >= this.raiseDelta) {
        this.phase = "UP";
      }
    } else if (this.phase === "UP") {
      if (armLower >= this.lowerDelta) {
        this.repCount += 1;
        this.phase = "DOWN";
      }
    }

    if (this.phase === "UP" && armRaise < this.raiseDelta * 0.8) {
      warnings.push("Raise arms higher");
    }

    return { repCount: this.repCount, phase: this.phase, warnings, isRepValid: true };
  }
}

export class LegSpreadCounter implements ExerciseBase {
  name = "leg_spread";
  requiredJoints = ["left_hip", "right_hip", "left_ankle", "right_ankle"];
  repCount = 0;
  phase = "CLOSED";
  private spreadDelta: number;
  private closeDelta: number;
  private baselineAnkleDist: number | null = null;
  private hipWidth: number | null = null;

  constructor(spreadDelta = 0.6, closeDelta = 0.2) {
    this.spreadDelta = spreadDelta;
    this.closeDelta = closeDelta;
  }

  reset(): void {
    this.repCount = 0;
    this.phase = "CLOSED";
    this.baselineAnkleDist = null;
    this.hipWidth = null;
  }

  update(pose: PoseFrame): ExerciseState {
    const warnings: string[] = [];
    if (!pose.valid) {
      return { repCount: this.repCount, phase: this.phase, warnings: ["No pose detected"], isRepValid: true };
    }
    const lm = pose.rawLandmarks;
    if (this.requiredJoints.some((k) => !lm[k])) {
      return { repCount: this.repCount, phase: this.phase, warnings: ["Legs not visible"], isRepValid: true };
    }
    const leftHip = lm.left_hip!;
    const rightHip = lm.right_hip!;
    const leftAnkle = lm.left_ankle!;
    const rightAnkle = lm.right_ankle!;
    const hipWidth = distance2d(leftHip, rightHip);
    const ankleDist = distance2d(leftAnkle, rightAnkle);
    if (this.hipWidth === null) {
      this.hipWidth = Math.max(hipWidth, 1e-5);
    }
    if (this.baselineAnkleDist === null) {
      this.baselineAnkleDist = ankleDist;
    }
    const spread = (ankleDist - this.baselineAnkleDist) / this.hipWidth;
    if (this.phase === "CLOSED") {
      if (spread >= this.spreadDelta) {
        this.phase = "OPEN";
      }
    } else if (this.phase === "OPEN") {
      if (spread <= this.closeDelta) {
        this.repCount += 1;
        this.phase = "CLOSED";
      }
    }
    if (this.phase === "OPEN" && spread < this.spreadDelta * 0.8) {
      warnings.push("Spread legs wider");
    }
    return { repCount: this.repCount, phase: this.phase, warnings, isRepValid: true };
  }
}

export class KneeRaiseCounter implements ExerciseBase {
  name = "knee_raise";
  requiredJoints = ["left_hip", "left_knee", "left_ankle", "right_hip", "right_knee", "right_ankle"];
  repCount = 0;
  phase = "DOWN";
  private raiseDelta: number;
  private lowerDelta: number;
  private legLength: number | null = null;

  constructor(raiseDelta = 0.35, lowerDelta = 0.12) {
    this.raiseDelta = raiseDelta;
    this.lowerDelta = lowerDelta;
  }

  reset(): void {
    this.repCount = 0;
    this.phase = "DOWN";
    this.legLength = null;
  }

  update(pose: PoseFrame): ExerciseState {
    const warnings: string[] = [];
    if (!pose.valid) {
      return { repCount: this.repCount, phase: this.phase, warnings: ["No pose detected"], isRepValid: true };
    }
    const side = selectLegSide(pose.rawLandmarks);
    if (!side) {
      return { repCount: this.repCount, phase: this.phase, warnings: ["Legs not visible"], isRepValid: true };
    }
    const [hip, knee, ankle] = side;
    if (this.legLength === null) {
      this.legLength = Math.max(distance2d(hip, ankle), 1e-5);
    }
    const kneeRaise = (hip.y - knee.y) / this.legLength;
    if (this.phase === "DOWN") {
      if (kneeRaise >= this.raiseDelta) {
        this.phase = "UP";
      }
    } else if (this.phase === "UP") {
      if (kneeRaise <= this.lowerDelta) {
        this.repCount += 1;
        this.phase = "DOWN";
      }
    }
    if (this.phase === "UP" && kneeRaise < this.raiseDelta * 0.85) {
      warnings.push("Lift knee higher");
    }
    return { repCount: this.repCount, phase: this.phase, warnings, isRepValid: true };
  }
}

export class TorsoBendCounter implements ExerciseBase {
  name = "torso_bend";
  requiredJoints = ["left_shoulder", "right_shoulder", "left_hip", "right_hip"];
  repCount = 0;
  phase = "CENTER";
  private bendDelta: number;
  private returnDelta: number;
  private shoulderWidth: number | null = null;

  constructor(bendDelta = 0.25, returnDelta = 0.08) {
    this.bendDelta = bendDelta;
    this.returnDelta = returnDelta;
  }

  reset(): void {
    this.repCount = 0;
    this.phase = "CENTER";
    this.shoulderWidth = null;
  }

  update(pose: PoseFrame): ExerciseState {
    const warnings: string[] = [];
    if (!pose.valid) {
      return { repCount: this.repCount, phase: this.phase, warnings: ["No pose detected"], isRepValid: true };
    }
    const lm = pose.rawLandmarks;
    if (this.requiredJoints.some((k) => !lm[k])) {
      return { repCount: this.repCount, phase: this.phase, warnings: ["Torso not visible"], isRepValid: true };
    }
    const leftShoulder = lm.left_shoulder!;
    const rightShoulder = lm.right_shoulder!;
    const leftHip = lm.left_hip!;
    const rightHip = lm.right_hip!;
    const shoulderCenterX = (leftShoulder.x + rightShoulder.x) / 2;
    const hipCenterX = (leftHip.x + rightHip.x) / 2;
    const shoulderWidth = distance2d(leftShoulder, rightShoulder);
    if (this.shoulderWidth === null) {
      this.shoulderWidth = Math.max(shoulderWidth, 1e-5);
    }
    const bend = Math.abs(shoulderCenterX - hipCenterX) / this.shoulderWidth;
    if (this.phase === "CENTER") {
      if (bend >= this.bendDelta) {
        this.phase = "BEND";
      }
    } else if (this.phase === "BEND") {
      if (bend <= this.returnDelta) {
        this.repCount += 1;
        this.phase = "CENTER";
      }
    }
    if (this.phase === "BEND" && bend < this.bendDelta * 0.85) {
      warnings.push("Bend further");
    }
    return { repCount: this.repCount, phase: this.phase, warnings, isRepValid: true };
  }
}

export class SquatCounter implements ExerciseBase {
  name = "squat";
  requiredJoints = ["left_hip", "left_knee", "left_ankle", "right_hip", "right_knee", "right_ankle"];
  repCount = 0;
  phase = "TOP";
  private topKneeAngle: number;
  private bottomKneeAngle: number;
  private hipDropMin: number;
  private startDrop: number;
  private hipYTop: number | null = null;
  private legLength: number | null = null;

  constructor(topKneeAngle = 165, bottomKneeAngle = 95, hipDropMin = 0.18, startDrop = 0.08) {
    this.topKneeAngle = topKneeAngle;
    this.bottomKneeAngle = bottomKneeAngle;
    this.hipDropMin = hipDropMin;
    this.startDrop = startDrop;
  }

  reset(): void {
    this.repCount = 0;
    this.phase = "TOP";
    this.hipYTop = null;
    this.legLength = null;
  }

  update(pose: PoseFrame): ExerciseState {
    const warnings: string[] = [];
    if (!pose.valid) {
      return { repCount: this.repCount, phase: this.phase, warnings: ["No pose detected"], isRepValid: true };
    }
    const side = selectLegSide(pose.rawLandmarks);
    if (!side) {
      return { repCount: this.repCount, phase: this.phase, warnings: ["Legs not visible"], isRepValid: true };
    }
    const [hip, knee, ankle] = side;
    const kneeAngle = angleDegrees(hip, knee, ankle);
    const hipY = hip.y;
    if (this.hipYTop === null) {
      this.hipYTop = hipY;
    }
    if (this.legLength === null) {
      this.legLength = Math.max(distance2d(hip, ankle), 1e-5);
    }
    const hipDrop = (hipY - this.hipYTop) / this.legLength;
    if (this.phase === "TOP") {
      if (kneeAngle < this.topKneeAngle && hipDrop > this.startDrop) {
        this.phase = "DOWN";
      }
    } else if (this.phase === "DOWN") {
      if (kneeAngle <= this.bottomKneeAngle && hipDrop >= this.hipDropMin) {
        this.phase = "BOTTOM";
      }
    } else if (this.phase === "BOTTOM") {
      if (kneeAngle > this.bottomKneeAngle + 5) {
        this.phase = "UP";
      }
    } else if (this.phase === "UP") {
      if (kneeAngle >= this.topKneeAngle - 5 && hipDrop <= 0.04) {
        this.repCount += 1;
        this.phase = "TOP";
      }
    }

    if (["DOWN", "BOTTOM"].includes(this.phase) && kneeAngle > this.bottomKneeAngle + 10) {
      warnings.push("Go lower");
    }
    return { repCount: this.repCount, phase: this.phase, warnings, isRepValid: true };
  }
}

export class LungeCounter implements ExerciseBase {
  name = "lunge";
  requiredJoints = ["left_hip", "left_knee", "left_ankle", "right_hip", "right_knee", "right_ankle"];
  repCount = 0;
  phase = "TOP";
  private topKneeAngle: number;
  private bottomKneeAngle: number;
  private hipDropMin: number;
  private startDrop: number;
  private hipYTop: number | null = null;
  private legLength: number | null = null;

  constructor(topKneeAngle = 165, bottomKneeAngle = 95, hipDropMin = 0.16, startDrop = 0.08) {
    this.topKneeAngle = topKneeAngle;
    this.bottomKneeAngle = bottomKneeAngle;
    this.hipDropMin = hipDropMin;
    this.startDrop = startDrop;
  }

  reset(): void {
    this.repCount = 0;
    this.phase = "TOP";
    this.hipYTop = null;
    this.legLength = null;
  }

  update(pose: PoseFrame): ExerciseState {
    const warnings: string[] = [];
    if (!pose.valid) {
      return { repCount: this.repCount, phase: this.phase, warnings: ["No pose detected"], isRepValid: true };
    }
    const side = selectLegSide(pose.rawLandmarks);
    if (!side) {
      return { repCount: this.repCount, phase: this.phase, warnings: ["Legs not visible"], isRepValid: true };
    }
    const [hip, knee, ankle] = side;
    const kneeAngle = angleDegrees(hip, knee, ankle);
    const hipY = hip.y;
    if (this.hipYTop === null) {
      this.hipYTop = hipY;
    }
    if (this.legLength === null) {
      this.legLength = Math.max(distance2d(hip, ankle), 1e-5);
    }
    const hipDrop = (hipY - this.hipYTop) / this.legLength;
    if (this.phase === "TOP") {
      if (kneeAngle < this.topKneeAngle && hipDrop > this.startDrop) {
        this.phase = "DOWN";
      }
    } else if (this.phase === "DOWN") {
      if (kneeAngle <= this.bottomKneeAngle && hipDrop >= this.hipDropMin) {
        this.phase = "BOTTOM";
      }
    } else if (this.phase === "BOTTOM") {
      if (kneeAngle > this.bottomKneeAngle + 5) {
        this.phase = "UP";
      }
    } else if (this.phase === "UP") {
      if (kneeAngle >= this.topKneeAngle - 5 && hipDrop <= 0.05) {
        this.repCount += 1;
        this.phase = "TOP";
      }
    }

    if (["DOWN", "BOTTOM"].includes(this.phase) && kneeAngle > this.bottomKneeAngle + 10) {
      warnings.push("Go lower");
    }
    return { repCount: this.repCount, phase: this.phase, warnings, isRepValid: true };
  }
}

export class SitUpCounter implements ExerciseBase {
  name = "situp";
  requiredJoints = [
    "left_shoulder",
    "left_hip",
    "left_knee",
    "right_shoulder",
    "right_hip",
    "right_knee"
  ];
  repCount = 0;
  phase = "DOWN";
  private downTorsoAngle = 35;
  private upTorsoAngle = 70;
  private minTorsoRaise = 0.18;
  private hipYBase: number | null = null;
  private torsoLength: number | null = null;

  reset(): void {
    this.repCount = 0;
    this.phase = "DOWN";
    this.hipYBase = null;
    this.torsoLength = null;
  }

  update(pose: PoseFrame): ExerciseState {
    const warnings: string[] = [];
    if (!pose.valid) {
      return { repCount: this.repCount, phase: this.phase, warnings: ["No pose detected"], isRepValid: true };
    }
    const side = selectTorsoSide(pose.rawLandmarks);
    if (!side) {
      return { repCount: this.repCount, phase: this.phase, warnings: ["Torso not visible"], isRepValid: true };
    }
    const [shoulder, hip, knee] = side;
    if (this.hipYBase === null) {
      this.hipYBase = hip.y;
    }
    if (this.torsoLength === null) {
      this.torsoLength = Math.max(distance2d(shoulder, hip), 1e-5);
    }
    const torsoRaise = (this.hipYBase - hip.y) / this.torsoLength;
    const torsoAngle = angleDegrees(knee, hip, shoulder);

    if (this.phase === "DOWN") {
      if (torsoAngle >= this.upTorsoAngle && torsoRaise >= this.minTorsoRaise) {
        this.phase = "UP";
      }
    } else if (this.phase === "UP") {
      if (torsoAngle <= this.downTorsoAngle && torsoRaise <= 0.05) {
        this.repCount += 1;
        this.phase = "DOWN";
      }
    }
    if (this.phase === "DOWN" && torsoAngle > this.downTorsoAngle + 10) {
      warnings.push("Lie back further");
    }
    if (this.phase === "UP" && torsoAngle < this.upTorsoAngle - 5) {
      warnings.push("Come up higher");
    }
    return { repCount: this.repCount, phase: this.phase, warnings, isRepValid: true };
  }
}

export class PullUpCounter implements ExerciseBase {
  name = "pullup";
  requiredJoints = ["nose", "left_wrist", "right_wrist", "left_shoulder", "right_shoulder"];
  repCount = 0;
  phase = "WAITING_BAR";
  private barY: number | null = null;
  private variant: "pullup" | "chinup";
  private thresholds = {
    chinAboveBar: 0.015,
    bottomResetDelta: 0.08,
    gripWidthMin: 0.15,
    maxFaceDepthDelta: 0.15,
    wristBarYDelta: 0.08
  };

  constructor(variant: "pullup" | "chinup" = "pullup") {
    this.variant = variant;
  }

  reset(): void {
    this.repCount = 0;
    this.phase = "WAITING_BAR";
    this.barY = null;
  }

  update(pose: PoseFrame, barY?: number | null): ExerciseState {
    const warnings: string[] = [];
    if (!pose.valid) {
      return { repCount: this.repCount, phase: this.phase, warnings: ["No pose detected"], isRepValid: true };
    }
    if (barY == null) {
      return { repCount: this.repCount, phase: "WAITING_BAR", warnings: ["Bar not found"], isRepValid: true };
    }
    this.barY = barY;

    const lm = pose.rawLandmarks;
    if (this.requiredJoints.some((k) => !lm[k])) {
      return { repCount: this.repCount, phase: this.phase, warnings: ["Upper body not visible"], isRepValid: true };
    }

    const noseY = lm.nose!.y;
    const noseZ = lm.nose!.z;
    const wristDist = distance2d(lm.left_wrist!, lm.right_wrist!);
    const shoulderWidth = distance2d(lm.left_shoulder!, lm.right_shoulder!);
    const shoulderZ = (lm.left_shoulder!.z + lm.right_shoulder!.z) / 2;
    const wristAvgY = (lm.left_wrist!.y + lm.right_wrist!.y) / 2;

    if (wristDist < this.thresholds.gripWidthMin * Math.max(shoulderWidth, 1e-5)) {
      warnings.push("Wider grip for pull-ups");
    }

    const depthOk = shoulderZ - noseZ <= this.thresholds.maxFaceDepthDelta;
    const wristsOnBar = Math.abs(wristAvgY - barY) <= this.thresholds.wristBarYDelta;
    const chinAbove = barY - noseY > this.thresholds.chinAboveBar && depthOk && wristsOnBar;
    const chinBelow = noseY - barY > this.thresholds.bottomResetDelta;

    if (this.phase === "WAITING_BAR" || this.phase === "DOWN") {
      if (chinAbove) {
        this.phase = "UP";
      }
    } else if (this.phase === "UP") {
      if (chinBelow) {
        this.repCount += 1;
        this.phase = "DOWN";
      }
    }

    if (!depthOk) {
      warnings.push("Move back from camera");
    }
    if (!wristsOnBar) {
      warnings.push("Keep wrists on the bar");
    }
    if (this.variant === "chinup" && wristDist > shoulderWidth * 1.4) {
      warnings.push("Narrower grip for chin-ups");
    }

    return { repCount: this.repCount, phase: this.phase, warnings, isRepValid: true };
  }
}

export class HoldCounter implements ExerciseBase {
  name: string;
  requiredJoints: string[];
  repCount = 0;
  phase = "READY";
  private holdSeconds: number;
  private holdCondition: (lm: Record<string, Landmark2D | null>) => boolean;
  private holdStart: number | null = null;
  private requiredAnyGroups?: string[][];

  constructor(
    name: string,
    requiredJoints: string[],
    holdCondition: (lm: Record<string, Landmark2D | null>) => boolean,
    holdSeconds = 2,
    requiredAnyGroups?: string[][]
  ) {
    this.name = name;
    this.requiredJoints = requiredJoints;
    this.holdCondition = holdCondition;
    this.holdSeconds = holdSeconds;
    this.requiredAnyGroups = requiredAnyGroups;
  }

  reset(): void {
    this.repCount = 0;
    this.phase = "READY";
    this.holdStart = null;
  }

  update(pose: PoseFrame): ExerciseState {
    const warnings: string[] = [];
    if (!pose.valid) {
      return { repCount: this.repCount, phase: this.phase, warnings: ["No pose detected"], isRepValid: true };
    }

    const lm = pose.rawLandmarks;
    if (this.requiredAnyGroups) {
      const ok = this.requiredAnyGroups.some((group) => group.every((k) => lm[k]));
      if (!ok) {
        return { repCount: this.repCount, phase: this.phase, warnings: ["Body not visible"], isRepValid: true };
      }
    } else if (this.requiredJoints.some((k) => !lm[k])) {
      return { repCount: this.repCount, phase: this.phase, warnings: ["Body not visible"], isRepValid: true };
    }

    const holding = this.holdCondition(lm);
    const now = performance.now();

    if (this.phase === "READY") {
      if (holding) {
        this.phase = "HOLDING";
        this.holdStart = now;
      }
    } else if (this.phase === "HOLDING") {
      if (!holding) {
        this.phase = "READY";
        this.holdStart = null;
      } else if (this.holdStart && now - this.holdStart >= this.holdSeconds * 1000) {
        this.repCount += 1;
        this.phase = "COUNTED";
      }
    } else if (this.phase === "COUNTED") {
      if (!holding) {
        this.phase = "READY";
        this.holdStart = null;
      }
    }

    if (this.phase === "HOLDING") {
      const remaining = Math.max(0, this.holdSeconds - (now - (this.holdStart ?? now)) / 1000);
      warnings.push(`Hold ${remaining.toFixed(1)}s`);
    }

    return { repCount: this.repCount, phase: this.phase, warnings, isRepValid: true };
  }
}

export class PushUpCounter implements ExerciseBase {
  name = "pushup";
  requiredJoints = [
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist"
  ];
  repCount = 0;
  phase = "CALIBRATING";
  private repValid = true;
  private thresholds: {
    topElbowAngle: number;
    bottomElbowAngle: number;
    minShoulderDrop: number;
    hipDeviationTolerance: number;
    topDropTolerance: number;
  } | null = null;
  private calibration: CalibrationResult | null = null;
  private lastShoulderY: number | null = null;
  private lastTime: number | null = null;
  private badHipFrames = 0;

  setCalibration(calibration: CalibrationResult): void {
    this.calibration = calibration;
    const bottomElbowAngle = Math.max(40, calibration.topElbowAngle - 80);
    this.thresholds = {
      topElbowAngle: calibration.topElbowAngle,
      bottomElbowAngle,
      minShoulderDrop: 0.25,
      hipDeviationTolerance: 0.25,
      topDropTolerance: 0.1
    };
    this.phase = "TOP";
    this.repValid = true;
  }

  reset(): void {
    this.repCount = 0;
    this.phase = "CALIBRATING";
    this.repValid = true;
    this.thresholds = null;
    this.calibration = null;
    this.lastShoulderY = null;
    this.lastTime = null;
    this.badHipFrames = 0;
  }

  update(pose: PoseFrame): ExerciseState {
    const warnings: string[] = [];
    if (!pose.valid) {
      return { repCount: this.repCount, phase: this.phase, warnings: ["No pose detected"], isRepValid: this.repValid };
    }
    if (!this.thresholds || !this.calibration) {
      return { repCount: this.repCount, phase: "CALIBRATING", warnings: ["Calibrating..."], isRepValid: this.repValid };
    }

    const lm = pose.rawLandmarks;
    if (this.requiredJoints.some((k) => !lm[k])) {
      return {
        repCount: this.repCount,
        phase: this.phase,
        warnings: ["Arms/shoulders not visible"],
        isRepValid: this.repValid
      };
    }

    const leftElbowAngle = angleDegrees(lm.left_shoulder!, lm.left_elbow!, lm.left_wrist!);
    const rightElbowAngle = angleDegrees(lm.right_shoulder!, lm.right_elbow!, lm.right_wrist!);
    const elbowAngle = (leftElbowAngle + rightElbowAngle) / 2;

    const shoulderY = (lm.left_shoulder!.y + lm.right_shoulder!.y) / 2;
    const hipY =
      lm.left_hip && lm.right_hip ? (lm.left_hip.y + lm.right_hip.y) / 2 : null;
    const torsoLength = this.calibration.torsoLength;

    const shoulderDrop = (shoulderY - this.calibration.shoulderYTop) / torsoLength;
    const hipDeviation = hipY !== null ? Math.abs(hipY - this.calibration.hipYTop) / torsoLength : null;

    const velocity =
      this.lastShoulderY !== null && this.lastTime !== null
        ? computeVelocity(this.lastShoulderY, this.lastTime, shoulderY, pose.timestamp)
        : null;
    this.lastShoulderY = shoulderY;
    this.lastTime = pose.timestamp;

    if (hipDeviation !== null) {
      if (hipDeviation > this.thresholds.hipDeviationTolerance) {
        this.badHipFrames += 1;
      } else {
        this.badHipFrames = 0;
      }
      if (this.badHipFrames >= 5) {
        warnings.push("Keep hips stable");
        this.repValid = false;
      }
    } else {
      warnings.push("Hips not visible (stability not checked)");
    }

    if (this.phase === "TOP") {
      if (elbowAngle < this.thresholds.topElbowAngle - 10 && shoulderDrop > 0.05) {
        this.phase = "DOWN";
        this.repValid = true;
        this.badHipFrames = 0;
      }
    } else if (this.phase === "DOWN") {
      if (elbowAngle <= this.thresholds.bottomElbowAngle && shoulderDrop >= this.thresholds.minShoulderDrop) {
        this.phase = "BOTTOM";
      }
    } else if (this.phase === "BOTTOM") {
      if (velocity !== null && velocity < -0.02 && elbowAngle > this.thresholds.bottomElbowAngle + 5) {
        this.phase = "UP";
      }
    } else if (this.phase === "UP") {
      if (
        elbowAngle >= this.thresholds.topElbowAngle - 5 &&
        shoulderDrop <= this.thresholds.topDropTolerance
      ) {
        if (this.repValid) {
          this.repCount += 1;
        } else {
          warnings.push("Rep not counted");
        }
        this.phase = "TOP";
      }
    }

    if (["DOWN", "BOTTOM"].includes(this.phase) && elbowAngle > this.thresholds.bottomElbowAngle + 10) {
      warnings.push("Go lower");
    }

    return { repCount: this.repCount, phase: this.phase, warnings, isRepValid: this.repValid };
  }
}

const selectLegSide = (
  lm: Record<string, Landmark2D | null>
): [Landmark2D, Landmark2D, Landmark2D] | null => {
  const left = [lm.left_hip, lm.left_knee, lm.left_ankle] as const;
  const right = [lm.right_hip, lm.right_knee, lm.right_ankle] as const;
  const leftValid = left.every(Boolean);
  const rightValid = right.every(Boolean);
  if (leftValid && rightValid) {
    return [left[0]!, left[1]!, left[2]!];
  }
  if (leftValid) {
    return [left[0]!, left[1]!, left[2]!];
  }
  if (rightValid) {
    return [right[0]!, right[1]!, right[2]!];
  }
  return null;
};

const selectTorsoSide = (
  lm: Record<string, Landmark2D | null>
): [Landmark2D, Landmark2D, Landmark2D] | null => {
  const left = [lm.left_shoulder, lm.left_hip, lm.left_knee] as const;
  const right = [lm.right_shoulder, lm.right_hip, lm.right_knee] as const;
  const leftValid = left.every(Boolean);
  const rightValid = right.every(Boolean);
  if (leftValid && rightValid) {
    return [left[0]!, left[1]!, left[2]!];
  }
  if (leftValid) {
    return [left[0]!, left[1]!, left[2]!];
  }
  if (rightValid) {
    return [right[0]!, right[1]!, right[2]!];
  }
  return null;
};

