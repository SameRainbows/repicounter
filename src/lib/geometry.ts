import type { Landmark2D } from "./poseTypes";

export function distance2d(a: Landmark2D, b: Landmark2D): number {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  return Math.hypot(dx, dy);
}

export function angleDegrees(a: Landmark2D, b: Landmark2D, c: Landmark2D): number {
  const bax = a.x - b.x;
  const bay = a.y - b.y;
  const bcx = c.x - b.x;
  const bcy = c.y - b.y;
  const dot = bax * bcx + bay * bcy;
  const magBa = Math.hypot(bax, bay);
  const magBc = Math.hypot(bcx, bcy);
  if (magBa < 1e-6 || magBc < 1e-6) {
    return 0;
  }
  const cosTheta = Math.max(-1, Math.min(1, dot / (magBa * magBc)));
  return (Math.acos(cosTheta) * 180) / Math.PI;
}

export function verticalDelta(a: Landmark2D, b: Landmark2D): number {
  return a.y - b.y;
}

export function computeVelocity(prevVal: number, prevTime: number, currVal: number, currTime: number): number | null {
  const dt = currTime - prevTime;
  if (dt <= 1e-6) {
    return null;
  }
  return (currVal - prevVal) / dt;
}

