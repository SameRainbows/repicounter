export class BarDetector {
  private maxAgeMs: number;
  private smoothing: number;
  private lastY: number | null = null;
  private lastTime: number | null = null;

  constructor(maxAgeSeconds = 0.6, smoothing = 0.7) {
    this.maxAgeMs = maxAgeSeconds * 1000;
    this.smoothing = smoothing;
  }

  update(imageData: ImageData): number | null {
    const candidate = detectBarCandidate(imageData);
    const now = performance.now();
    if (candidate !== null) {
      this.lastY = this.smooth(this.lastY, candidate, this.smoothing);
      this.lastTime = now;
      return this.lastY;
    }

    if (this.lastY !== null && this.lastTime !== null) {
      if (now - this.lastTime <= this.maxAgeMs) {
        return this.lastY;
      }
    }
    return null;
  }

  reset(): void {
    this.lastY = null;
    this.lastTime = null;
  }

  private smooth(prev: number | null, curr: number, alpha: number): number {
    if (prev === null) {
      return curr;
    }
    return prev * alpha + curr * (1 - alpha);
  }
}

export function detectBarCandidate(imageData: ImageData): number | null {
  const { width, height, data } = imageData;
  const roiHeight = Math.floor(height * 0.65);
  if (roiHeight <= 2 || width <= 2) {
    return null;
  }

  const rowScores = new Float32Array(roiHeight);
  for (let y = 1; y < roiHeight; y += 1) {
    let sum = 0;
    const row = y * width * 4;
    const prev = (y - 1) * width * 4;
    for (let x = 0; x < width; x += 1) {
      const idx = row + x * 4;
      const prevIdx = prev + x * 4;
      const gray = 0.299 * data[idx] + 0.587 * data[idx + 1] + 0.114 * data[idx + 2];
      const grayPrev =
        0.299 * data[prevIdx] + 0.587 * data[prevIdx + 1] + 0.114 * data[prevIdx + 2];
      sum += Math.abs(gray - grayPrev);
    }
    rowScores[y] = sum;
  }

  let maxVal = 0;
  let maxIdx = -1;
  let total = 0;
  for (let i = 0; i < rowScores.length; i += 1) {
    total += rowScores[i];
    if (rowScores[i] > maxVal) {
      maxVal = rowScores[i];
      maxIdx = i;
    }
  }

  const mean = total / Math.max(rowScores.length, 1);
  if (maxIdx < 0 || maxVal < mean * 1.6) {
    return null;
  }

  return maxIdx / height;
}

