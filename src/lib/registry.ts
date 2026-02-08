import type { Landmark2D } from "./poseTypes";
import { angleDegrees } from "./geometry";
import type { ExerciseBase } from "./exercises";
import {
  ArmRaiseCounter,
  HoldCounter,
  JumpingJackCounter,
  KneeRaiseCounter,
  LegSpreadCounter,
  LungeCounter,
  PullUpCounter,
  SitUpCounter,
  SquatCounter,
  TorsoBendCounter,
  PushUpCounter
} from "./exercises";

export type ExerciseEntry = {
  id: string;
  name: string;
  viewHint: string;
  usesBar?: boolean;
  createCounter: () => ExerciseBase;
};

const holdCondition = (fn: (lm: Record<string, Landmark2D | null>) => boolean, name: string, required: string[], holdSeconds: number, anyGroups?: string[][]) =>
  new HoldCounter(name, required, fn, holdSeconds, anyGroups);

const plankHold = () =>
  holdCondition(
    (lm) => {
      const shoulder = lm.left_shoulder ?? lm.right_shoulder;
      const hip = lm.left_hip ?? lm.right_hip;
      const knee = lm.left_knee ?? lm.right_knee;
      if (!shoulder || !hip || !knee) return false;
      return angleDegrees(shoulder, hip, knee) > 160;
    },
    "plank_hold",
    ["left_shoulder", "left_hip", "left_knee"],
    2,
    [
      ["left_shoulder", "left_hip", "left_knee"],
      ["right_shoulder", "right_hip", "right_knee"]
    ]
  );

const sidePlankHold = () =>
  holdCondition(
    (lm) => {
      const shoulder = lm.left_shoulder ?? lm.right_shoulder;
      const hip = lm.left_hip ?? lm.right_hip;
      const knee = lm.left_knee ?? lm.right_knee;
      if (!shoulder || !hip || !knee) return false;
      return angleDegrees(shoulder, hip, knee) > 155;
    },
    "side_plank_hold",
    ["left_shoulder", "left_hip", "left_knee"],
    2,
    [
      ["left_shoulder", "left_hip", "left_knee"],
      ["right_shoulder", "right_hip", "right_knee"]
    ]
  );

const wallSitHold = () =>
  holdCondition(
    (lm) => {
      const hip = lm.left_hip ?? lm.right_hip;
      const knee = lm.left_knee ?? lm.right_knee;
      const ankle = lm.left_ankle ?? lm.right_ankle;
      if (!hip || !knee || !ankle) return false;
      const angle = angleDegrees(hip, knee, ankle);
      return angle >= 80 && angle <= 110;
    },
    "wall_sit_hold",
    ["left_hip", "left_knee", "left_ankle"],
    2.5,
    [
      ["left_hip", "left_knee", "left_ankle"],
      ["right_hip", "right_knee", "right_ankle"]
    ]
  );

const gluteBridgeHold = () =>
  holdCondition(
    (lm) => {
      const shoulder = lm.left_shoulder ?? lm.right_shoulder;
      const hip = lm.left_hip ?? lm.right_hip;
      const knee = lm.left_knee ?? lm.right_knee;
      if (!shoulder || !hip || !knee) return false;
      return angleDegrees(shoulder, hip, knee) > 155;
    },
    "glute_bridge",
    ["left_shoulder", "left_hip", "left_knee"],
    1.5,
    [
      ["left_shoulder", "left_hip", "left_knee"],
      ["right_shoulder", "right_hip", "right_knee"]
    ]
  );

const hipHingeHold = () =>
  holdCondition(
    (lm) => {
      const shoulder = lm.left_shoulder ?? lm.right_shoulder;
      const hip = lm.left_hip ?? lm.right_hip;
      const knee = lm.left_knee ?? lm.right_knee;
      if (!shoulder || !hip || !knee) return false;
      const angle = angleDegrees(shoulder, hip, knee);
      return angle >= 60 && angle <= 110;
    },
    "hip_hinge",
    ["left_shoulder", "left_hip", "left_knee"],
    1,
    [
      ["left_shoulder", "left_hip", "left_knee"],
      ["right_shoulder", "right_hip", "right_knee"]
    ]
  );

const splitSquatHold = () =>
  holdCondition(
    (lm) => {
      const hip = lm.left_hip ?? lm.right_hip;
      const knee = lm.left_knee ?? lm.right_knee;
      const ankle = lm.left_ankle ?? lm.right_ankle;
      if (!hip || !knee || !ankle) return false;
      const angle = angleDegrees(hip, knee, ankle);
      return angle >= 80 && angle <= 115;
    },
    "split_squat_hold",
    ["left_hip", "left_knee", "left_ankle"],
    2,
    [
      ["left_hip", "left_knee", "left_ankle"],
      ["right_hip", "right_knee", "right_ankle"]
    ]
  );

export const getExerciseEntries = (): ExerciseEntry[] => {
  const entries: ExerciseEntry[] = [
    { id: "jumping_jack", name: "Jumping Jack", viewHint: "Front", createCounter: () => new JumpingJackCounter() },
    { id: "squat", name: "Squat", viewHint: "Front", createCounter: () => new SquatCounter() },
    { id: "pullup", name: "Pull-Up", viewHint: "Bar", usesBar: true, createCounter: () => new PullUpCounter("pullup") },
    { id: "chinup", name: "Chin-Up", viewHint: "Bar", usesBar: true, createCounter: () => new PullUpCounter("chinup") },
    { id: "situp", name: "Sit-Up", viewHint: "Side", createCounter: () => new SitUpCounter() },
    { id: "pushup", name: "Push-Up", viewHint: "Side", createCounter: () => new PushUpCounter() }
  ];

  entries.push(
    { id: "step_jack", name: "Step Jack", viewHint: "Front", createCounter: () => new JumpingJackCounter(2, 0.45, 0.5) },
    { id: "half_jack", name: "Half Jack", viewHint: "Front", createCounter: () => new JumpingJackCounter(2, 0.35, 0.4) },
    { id: "seal_jack", name: "Seal Jack", viewHint: "Front", createCounter: () => new LegSpreadCounter(0.6, 0.2) },
    { id: "side_steps", name: "Side Steps", viewHint: "Front", createCounter: () => new LegSpreadCounter(0.35, 0.15) },
    { id: "high_knees", name: "High Knees", viewHint: "Front", createCounter: () => new KneeRaiseCounter(0.42, 0.15) },
    { id: "marching", name: "Marching", viewHint: "Front", createCounter: () => new KneeRaiseCounter(0.25, 0.12) },
    { id: "arm_raises", name: "Arm Raises", viewHint: "Front", createCounter: () => new ArmRaiseCounter(0.35, 0.15) },
    { id: "overhead_raises", name: "Overhead Raises", viewHint: "Front", createCounter: () => new ArmRaiseCounter(0.55, 0.2) },
    { id: "lateral_raises", name: "Lateral Raises", viewHint: "Front", createCounter: () => new ArmRaiseCounter(0.25, 0.12) },
    { id: "side_bends", name: "Side Bends", viewHint: "Front", createCounter: () => new TorsoBendCounter(0.22, 0.08) }
  );

  entries.push(
    { id: "wide_squat", name: "Wide Squat", viewHint: "Front", createCounter: () => new SquatCounter(100, 100, 0.2) },
    { id: "narrow_squat", name: "Narrow Squat", viewHint: "Front", createCounter: () => new SquatCounter(95, 95, 0.16) },
    { id: "half_squat", name: "Half Squat", viewHint: "Front", createCounter: () => new SquatCounter(120, 120, 0.12) },
    { id: "pulse_squat", name: "Pulse Squat", viewHint: "Front", createCounter: () => new SquatCounter(110, 110, 0.15) },
    { id: "jump_squat", name: "Jump Squat", viewHint: "Front", createCounter: () => new SquatCounter(100, 100, 0.18) }
  );

  entries.push(
    { id: "forward_lunge", name: "Forward Lunge", viewHint: "Side", createCounter: () => new LungeCounter(165, 95, 0.18) },
    { id: "reverse_lunge", name: "Reverse Lunge", viewHint: "Side", createCounter: () => new LungeCounter(165, 95, 0.18) },
    { id: "split_squat", name: "Split Squat", viewHint: "Side", createCounter: () => new LungeCounter(165, 100, 0.16) },
    { id: "side_lunge", name: "Side Lunge", viewHint: "Front", createCounter: () => new LungeCounter(165, 105, 0.16) }
  );

  entries.push(
    { id: "plank_hold", name: "Plank Hold", viewHint: "Side", createCounter: plankHold },
    { id: "side_plank_hold", name: "Side Plank Hold", viewHint: "Side", createCounter: sidePlankHold },
    { id: "wall_sit_hold", name: "Wall Sit Hold", viewHint: "Side", createCounter: wallSitHold },
    { id: "glute_bridge", name: "Glute Bridge", viewHint: "Side", createCounter: gluteBridgeHold },
    { id: "hip_hinge", name: "Hip Hinge", viewHint: "Side", createCounter: hipHingeHold },
    { id: "knee_tucks", name: "Knee Tucks", viewHint: "Side", createCounter: () => new KneeRaiseCounter(0.3, 0.12) }
  );

  entries.push(
    { id: "skater_steps", name: "Skater Steps", viewHint: "Front", createCounter: () => new LegSpreadCounter(0.5, 0.2) },
    { id: "toe_touches", name: "Toe Touches", viewHint: "Front", createCounter: () => new TorsoBendCounter(0.28, 0.1) },
    { id: "arm_pulses", name: "Arm Pulses", viewHint: "Front", createCounter: () => new ArmRaiseCounter(0.2, 0.08) },
    { id: "fast_jacks", name: "Fast Jacks", viewHint: "Front", createCounter: () => new JumpingJackCounter(1.5, 0.5, 0.6) },
    { id: "slow_jacks", name: "Slow Jacks", viewHint: "Front", createCounter: () => new JumpingJackCounter(3, 0.7, 0.75) },
    { id: "low_jacks", name: "Low Jacks", viewHint: "Front", createCounter: () => new JumpingJackCounter(2, 0.35, 0.5) },
    { id: "power_jacks", name: "Power Jacks", viewHint: "Front", createCounter: () => new JumpingJackCounter(2, 0.75, 0.85) },
    { id: "box_squat", name: "Box Squat", viewHint: "Side", createCounter: () => new SquatCounter(100, 100, 0.2) },
    { id: "tempo_squat", name: "Tempo Squat", viewHint: "Front", createCounter: () => new SquatCounter(105, 105, 0.18) },
    { id: "split_squat_hold", name: "Split Squat Hold", viewHint: "Side", createCounter: splitSquatHold }
  );

  return entries;
};

