import type { Landmark2D, PoseFrame } from "./poseTypes";
import { angleDegrees } from "./geometry";

const POSE_CONNECTIONS: Array<[number, number]> = [
  [0, 1],
  [1, 2],
  [2, 3],
  [3, 7],
  [0, 4],
  [4, 5],
  [5, 6],
  [6, 8],
  [9, 10],
  [11, 12],
  [11, 13],
  [13, 15],
  [15, 17],
  [15, 19],
  [15, 21],
  [17, 19],
  [12, 14],
  [14, 16],
  [16, 18],
  [16, 20],
  [16, 22],
  [18, 20],
  [11, 23],
  [12, 24],
  [23, 24],
  [23, 25],
  [24, 26],
  [25, 27],
  [26, 28],
  [27, 29],
  [28, 30],
  [29, 31],
  [30, 32],
  [27, 31],
  [28, 32]
];

export function drawPose(
  ctx: CanvasRenderingContext2D,
  pose: PoseFrame,
  highlight?: Record<string, string>
): void {
  if (!pose.valid) {
    return;
  }

  const { imageSize, rawLandmarks } = pose;
  const [width, height] = imageSize;
  const toPixel = (lm: Landmark2D) => [lm.x * width, lm.y * height] as const;

  ctx.lineWidth = 2;
  ctx.strokeStyle = "#43d675";
  ctx.fillStyle = "#43d675";

  const landmarks = Object.values(rawLandmarks);
  POSE_CONNECTIONS.forEach(([a, b]) => {
    const lmA = landmarks[a];
    const lmB = landmarks[b];
    if (!lmA || !lmB) {
      return;
    }
    const [ax, ay] = toPixel(lmA);
    const [bx, by] = toPixel(lmB);
    ctx.beginPath();
    ctx.moveTo(ax, ay);
    ctx.lineTo(bx, by);
    ctx.stroke();
  });

  Object.entries(rawLandmarks).forEach(([name, lm]) => {
    if (!lm) {
      return;
    }
    const [x, y] = toPixel(lm);
    ctx.fillStyle = highlight?.[name] ?? "#f5d442";
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fill();
  });
}

export function drawJointAngles(ctx: CanvasRenderingContext2D, pose: PoseFrame): void {
  if (!pose.valid) {
    return;
  }
  const { imageSize, rawLandmarks } = pose;
  const [width, height] = imageSize;
  const toPixel = (lm: Landmark2D) => [lm.x * width, lm.y * height] as const;
  const triples: Array<[string, string, string]> = [
    ["left_hip", "left_knee", "left_ankle"],
    ["right_hip", "right_knee", "right_ankle"],
    ["left_shoulder", "left_elbow", "left_wrist"],
    ["right_shoulder", "right_elbow", "right_wrist"]
  ];

  ctx.fillStyle = "#f5d442";
  ctx.font = "12px sans-serif";

  triples.forEach(([a, b, c]) => {
    const la = rawLandmarks[a];
    const lb = rawLandmarks[b];
    const lc = rawLandmarks[c];
    if (!la || !lb || !lc) {
      return;
    }
    const angle = angleDegrees(la, lb, lc);
    const [x, y] = toPixel(lb);
    ctx.fillText(`${Math.round(angle)}`, x + 6, y - 6);
  });
}

export function drawBar(ctx: CanvasRenderingContext2D, barY: number, imageSize: [number, number]): void {
  const [width, height] = imageSize;
  const y = barY * height;
  ctx.strokeStyle = "#d86cff";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(0, y);
  ctx.lineTo(width, y);
  ctx.stroke();
}

